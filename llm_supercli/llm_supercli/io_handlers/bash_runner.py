"""
Shell command runner for llm_supercli.
Handles execution of shell commands via !command syntax.
"""
import asyncio
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

from ..utils import is_windows


@dataclass
class CommandResult:
    """Result of a shell command execution."""
    stdout: str
    stderr: str
    return_code: int
    command: str
    timed_out: bool = False
    
    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.return_code == 0
    
    @property
    def output(self) -> str:
        """Get combined output."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        return "\n".join(parts) if parts else "(no output)"


class BashRunner:
    """
    Executes shell commands safely.
    
    Supports command execution with timeout, output capture,
    and cross-platform shell selection.
    """
    
    DANGEROUS_COMMANDS = {
        "rm -rf /",
        "rm -rf ~",
        "rm -rf *",
        ":(){:|:&};:",
        "dd if=/dev/random",
        "mkfs",
        "chmod -R 777 /",
        "> /dev/sda",
    }
    
    def __init__(
        self,
        shell: Optional[str] = None,
        timeout: int = 60,
        env: Optional[dict] = None
    ) -> None:
        """
        Initialize bash runner.
        
        Args:
            shell: Shell to use (auto-detected if not provided)
            timeout: Default timeout in seconds
            env: Additional environment variables
        """
        self._shell = shell or self._detect_shell()
        self._timeout = timeout
        self._env = {**os.environ, **(env or {})}
    
    def _detect_shell(self) -> str:
        """Detect the appropriate shell for the platform."""
        if is_windows():
            return "powershell.exe"
        
        for shell in ["/bin/bash", "/bin/zsh", "/bin/sh"]:
            if os.path.exists(shell):
                return shell
        
        return os.environ.get("SHELL", "/bin/sh")
    
    def _is_dangerous(self, command: str) -> bool:
        """Check if a command is potentially dangerous."""
        command_lower = command.lower().strip()
        
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command_lower:
                return True
        
        if command_lower.startswith("sudo rm") and "-rf" in command_lower:
            if "/" in command_lower.split()[-1] or "~" in command_lower:
                return True
        
        return False
    
    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        capture_output: bool = True
    ) -> CommandResult:
        """
        Run a shell command synchronously.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CommandResult with execution results
        """
        if self._is_dangerous(command):
            return CommandResult(
                stdout="",
                stderr="Command blocked: potentially dangerous operation",
                return_code=-1,
                command=command
            )
        
        timeout = timeout or self._timeout
        
        try:
            if is_windows():
                args = ["powershell.exe", "-Command", command]
            else:
                args = [self._shell, "-c", command]
            
            result = subprocess.run(
                args,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=self._env
            )
            
            return CommandResult(
                stdout=result.stdout.strip() if result.stdout else "",
                stderr=result.stderr.strip() if result.stderr else "",
                return_code=result.returncode,
                command=command
            )
            
        except subprocess.TimeoutExpired:
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1,
                command=command,
                timed_out=True
            )
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=command
            )
    
    async def run_async(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None
    ) -> CommandResult:
        """
        Run a shell command asynchronously.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            
        Returns:
            CommandResult with execution results
        """
        if self._is_dangerous(command):
            return CommandResult(
                stdout="",
                stderr="Command blocked: potentially dangerous operation",
                return_code=-1,
                command=command
            )
        
        timeout = timeout or self._timeout
        
        try:
            if is_windows():
                shell_cmd = f'powershell.exe -Command "{command}"'
            else:
                shell_cmd = command
            
            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=self._env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # Handle Windows encoding (cp866/cp1251)
                encoding = 'cp866' if is_windows() else 'utf-8'
                
                return CommandResult(
                    stdout=stdout.decode(encoding, errors='replace').strip() if stdout else "",
                    stderr=stderr.decode(encoding, errors='replace').strip() if stderr else "",
                    return_code=process.returncode or 0,
                    command=command
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    return_code=-1,
                    command=command,
                    timed_out=True
                )
                
        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=-1,
                command=command
            )
    
    def run_interactive(self, command: str, cwd: Optional[str] = None) -> int:
        """
        Run a command interactively (with direct terminal I/O).
        
        Args:
            command: Command to execute
            cwd: Working directory
            
        Returns:
            Return code
        """
        if self._is_dangerous(command):
            print("Command blocked: potentially dangerous operation")
            return -1
        
        try:
            if is_windows():
                args = ["powershell.exe", "-Command", command]
            else:
                args = [self._shell, "-c", command]
            
            return subprocess.call(args, cwd=cwd, env=self._env)
        except Exception as e:
            print(f"Error: {e}")
            return -1


_runner: Optional[BashRunner] = None


def get_runner() -> BashRunner:
    """Get the global bash runner instance."""
    global _runner
    if _runner is None:
        _runner = BashRunner()
    return _runner


def run_command(command: str, **kwargs) -> CommandResult:
    """Convenience function to run a shell command."""
    return get_runner().run(command, **kwargs)
