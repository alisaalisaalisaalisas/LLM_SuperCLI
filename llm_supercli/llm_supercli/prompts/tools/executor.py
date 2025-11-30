"""Tool executor for handling LLM tool calls."""
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class ToolExecutor:
    """Executes tool calls from LLM responses."""
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return the result as a string."""
        try:
            if tool_name == "get_current_directory":
                return self._get_current_directory()
            elif tool_name == "list_directory":
                return self._list_directory(arguments.get("path", "."))
            elif tool_name == "read_file":
                return self._read_file(arguments.get("path", ""))
            elif tool_name == "write_file":
                return self._write_file(
                    arguments.get("path", ""),
                    arguments.get("content", "")
                )
            elif tool_name == "create_directory":
                return self._create_directory(arguments.get("path", ""))
            elif tool_name == "run_command":
                return self._run_command(arguments.get("command", ""))
            else:
                return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory."""
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.working_dir) / p
        return p.resolve()
    
    def _get_current_directory(self) -> str:
        """Get current working directory."""
        return self.working_dir

    def _list_directory(self, path: str) -> str:
        """List contents of a directory."""
        dir_path = self._resolve_path(path)
        
        if not dir_path.exists():
            return f"Error: Directory '{path}' does not exist"
        if not dir_path.is_dir():
            return f"Error: '{path}' is not a directory"
        
        items = []
        try:
            for item in sorted(dir_path.iterdir()):
                if item.is_dir():
                    items.append(f"[DIR]  {item.name}/")
                else:
                    size = item.stat().st_size
                    size_str = self._format_size(size)
                    items.append(f"[FILE] {item.name} ({size_str})")
        except PermissionError:
            return f"Error: Permission denied accessing '{path}'"
        
        if not items:
            return f"Directory '{path}' is empty"
        
        return f"Contents of {dir_path}:\n" + "\n".join(items)
    
    def _format_size(self, size: int) -> str:
        """Format file size in human readable form."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}" if unit != 'B' else f"{size}B"
            size /= 1024
        return f"{size:.1f}TB"
    
    def _read_file(self, path: str) -> str:
        """Read contents of a file."""
        if not path:
            return "Error: No file path provided"
        
        file_path = self._resolve_path(path)
        
        if not file_path.exists():
            return f"Error: File '{path}' does not exist"
        if not file_path.is_file():
            return f"Error: '{path}' is not a file"
        
        try:
            content = file_path.read_text(encoding='utf-8')
            if len(content) > 50000:
                content = content[:50000] + f"\n\n... [truncated, file has {len(content)} characters total]"
            return content
        except UnicodeDecodeError:
            return f"Error: File '{path}' is not a text file or has encoding issues"
        except PermissionError:
            return f"Error: Permission denied reading '{path}'"
    
    def _write_file(self, path: str, content: str) -> str:
        """Write content to a file."""
        if not path:
            return "Error: No file path provided"
        
        file_path = self._resolve_path(path)
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            return f"Successfully wrote {len(content)} characters to '{path}'"
        except PermissionError:
            return f"Error: Permission denied writing to '{path}'"
    
    def _create_directory(self, path: str) -> str:
        """Create a directory."""
        if not path:
            return "Error: No directory path provided"
        
        dir_path = self._resolve_path(path)
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory '{path}'"
        except PermissionError:
            return f"Error: Permission denied creating '{path}'"
    
    def _run_command(self, command: str) -> str:
        """Run a shell command."""
        if not command:
            return "Error: No command provided"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + f"[stderr]: {result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            
            return output if output else "(command produced no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds"
        except Exception as e:
            return f"Error running command: {str(e)}"
