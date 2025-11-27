"""
Input handling for llm_supercli Rich UI.
Provides interactive prompts with history, completion, and multiline support.
"""
import sys
from typing import Callable, List, Optional

try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text

from .theme import get_theme_manager
from ..constants import SLASH_PREFIX, SHELL_PREFIX, FILE_PREFIX


class InputHandler:
    """
    Handles user input with Rich-styled prompts.
    Supports command history, tab completion, and multiline input.
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize input handler.
        
        Args:
            console: Optional Rich Console instance
        """
        self._theme = get_theme_manager()
        self._console = console or Console(theme=self._theme.get_rich_theme())
        self._history: List[str] = []
        self._completions: List[str] = []
        self._multiline_mode = False
        self._setup_readline()
    
    def _setup_readline(self) -> None:
        """Configure readline for history and completion."""
        if not HAS_READLINE:
            return
        try:
            readline.set_history_length(1000)
            readline.set_completer(self._completer)
            readline.parse_and_bind("tab: complete")
            readline.set_completer_delims(' \t\n')
        except Exception:
            pass
    
    def _completer(self, text: str, state: int) -> Optional[str]:
        """
        Tab completion function.
        
        Args:
            text: Current input text
            state: Completion state
            
        Returns:
            Completion suggestion or None
        """
        if state == 0:
            if text.startswith(SLASH_PREFIX):
                self._completions = [
                    c for c in self._get_command_completions()
                    if c.startswith(text)
                ]
            elif text.startswith(FILE_PREFIX):
                self._completions = self._get_file_completions(text[1:])
            else:
                self._completions = []
        
        try:
            return self._completions[state]
        except IndexError:
            return None
    
    def _get_command_completions(self) -> List[str]:
        """Get list of slash command completions."""
        commands = [
            "/help", "/account", "/login", "/logout", "/sessions",
            "/new", "/clear", "/model", "/mcp", "/settings",
            "/status", "/cost", "/favorite", "/compress", "/rewind",
            "/quit", "/billing", "/bug", "/droids", "/skills",
            "/ide", "/review", "/terminal_setup"
        ]
        return commands
    
    def _get_file_completions(self, partial: str) -> List[str]:
        """
        Get file path completions.
        
        Args:
            partial: Partial file path
            
        Returns:
            List of matching file paths
        """
        import os
        from pathlib import Path
        
        try:
            if not partial:
                directory = Path.cwd()
                prefix = ""
            else:
                path = Path(partial).expanduser()
                if path.is_dir():
                    directory = path
                    prefix = partial
                else:
                    directory = path.parent
                    prefix = str(path.parent) + os.sep if str(path.parent) != "." else ""
            
            completions = []
            for item in directory.iterdir():
                name = prefix + item.name
                if item.is_dir():
                    name += os.sep
                completions.append(FILE_PREFIX + name)
            
            return sorted(completions)
        except Exception:
            return []
    
    def set_command_completions(self, commands: List[str]) -> None:
        """
        Set available commands for completion.
        
        Args:
            commands: List of command names
        """
        self._command_completions = [f"{SLASH_PREFIX}{c}" for c in commands]
    
    def get_input(
        self,
        prompt_text: str = ">>> ",
        default: str = "",
        password: bool = False
    ) -> str:
        """
        Get single-line input from user.
        
        Args:
            prompt_text: Prompt to display
            default: Default value
            password: Whether to hide input
            
        Returns:
            User input string
        """
        style = self._theme.get_style("prompt")
        styled_prompt = Text(prompt_text, style=style)
        
        try:
            if password:
                result = Prompt.ask(
                    styled_prompt,
                    console=self._console,
                    password=True,
                    default=default
                )
            else:
                self._console.print(styled_prompt, end="")
                result = input()
                
                if result.strip():
                    self._history.append(result)
                    if HAS_READLINE:
                        try:
                            readline.add_history(result)
                        except Exception:
                            pass
            
            return result
        except EOFError:
            return "/quit"
        except KeyboardInterrupt:
            self._console.print("\n[dim]Input cancelled[/dim]")
            return ""
    
    def get_multiline_input(
        self,
        prompt_text: str = ">>> ",
        end_marker: str = "EOF",
        show_instructions: bool = True
    ) -> str:
        """
        Get multiline input from user.
        
        Args:
            prompt_text: Initial prompt
            end_marker: String that ends input (e.g., 'EOF' or empty line twice)
            show_instructions: Whether to show usage instructions
            
        Returns:
            Combined multiline input
        """
        if show_instructions:
            self._console.print(
                f"[dim]Enter multiline input. Type '{end_marker}' on a new line or press Ctrl+D to finish.[/dim]"
            )
        
        lines = []
        continuation_prompt = "... "
        empty_count = 0
        
        try:
            while True:
                prompt = prompt_text if not lines else continuation_prompt
                style = self._theme.get_style("prompt")
                self._console.print(Text(prompt, style=style), end="")
                
                line = input()
                
                if line.strip() == end_marker:
                    break
                
                if not line.strip():
                    empty_count += 1
                    if empty_count >= 2 and lines:
                        break
                else:
                    empty_count = 0
                
                lines.append(line)
        except EOFError:
            pass
        except KeyboardInterrupt:
            self._console.print("\n[dim]Input cancelled[/dim]")
            return ""
        
        result = "\n".join(lines)
        if result.strip():
            self._history.append(result)
        
        return result
    
    def confirm(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """
        Get yes/no confirmation from user.
        
        Args:
            message: Confirmation message
            default: Default value
            
        Returns:
            User's choice
        """
        return Confirm.ask(message, default=default, console=self._console)
    
    def select(
        self,
        message: str,
        choices: List[str],
        default: Optional[str] = None
    ) -> str:
        """
        Let user select from a list of choices.
        
        Args:
            message: Selection prompt
            choices: List of choices
            default: Default selection
            
        Returns:
            Selected choice
        """
        self._console.print(f"[{self._theme.get_style('prompt')}]{message}[/]")
        
        for i, choice in enumerate(choices, 1):
            marker = ">" if choice == default else " "
            self._console.print(f"  {marker} [{i}] {choice}")
        
        while True:
            try:
                self._console.print(
                    Text("Enter number or name: ", style=self._theme.get_style("prompt")),
                    end=""
                )
                selection = input().strip()
                
                if not selection and default:
                    return default
                
                if selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]
                
                if selection in choices:
                    return selection
                
                self._console.print("[warning]Invalid selection. Try again.[/warning]")
            except (EOFError, KeyboardInterrupt):
                return default or choices[0]
    
    def get_secret(self, prompt_text: str = "Enter secret: ") -> str:
        """
        Get secret input (hidden).
        
        Args:
            prompt_text: Prompt to display
            
        Returns:
            Secret string
        """
        return self.get_input(prompt_text, password=True)
    
    def parse_input(self, text: str) -> dict:
        """
        Parse user input to determine type and content.
        
        Args:
            text: Raw user input
            
        Returns:
            Dict with 'type' and 'content' keys
        """
        text = text.strip()
        
        if not text:
            return {"type": "empty", "content": ""}
        
        if text.startswith(SLASH_PREFIX):
            parts = text[1:].split(maxsplit=1)
            command = parts[0] if parts else ""
            args = parts[1] if len(parts) > 1 else ""
            return {
                "type": "command",
                "content": command,
                "args": args
            }
        
        if text.startswith(SHELL_PREFIX):
            return {
                "type": "shell",
                "content": text[1:].strip()
            }
        
        if FILE_PREFIX in text:
            return {
                "type": "message_with_files",
                "content": text,
                "files": self._extract_file_references(text)
            }
        
        return {
            "type": "message",
            "content": text
        }
    
    def _extract_file_references(self, text: str) -> List[str]:
        """
        Extract file references from text.
        
        Args:
            text: Text containing @file references
            
        Returns:
            List of file paths
        """
        import re
        pattern = rf'{FILE_PREFIX}([^\s]+)'
        matches = re.findall(pattern, text)
        return matches
    
    @property
    def history(self) -> List[str]:
        """Get input history."""
        return self._history.copy()
    
    def clear_history(self) -> None:
        """Clear input history."""
        self._history.clear()
        if HAS_READLINE:
            try:
                readline.clear_history()
            except Exception:
                pass
    
    def save_history(self, filepath: str) -> None:
        """
        Save history to file.
        
        Args:
            filepath: Path to save history
        """
        if HAS_READLINE:
            try:
                readline.write_history_file(filepath)
                return
            except Exception:
                pass
        with open(filepath, 'w', encoding='utf-8') as f:
            for line in self._history:
                f.write(line + '\n')
    
    def load_history(self, filepath: str) -> None:
        """
        Load history from file.
        
        Args:
            filepath: Path to load history from
        """
        if HAS_READLINE:
            try:
                readline.read_history_file(filepath)
                return
            except Exception:
                pass
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self._history = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            pass


_input_handler: Optional[InputHandler] = None


def get_input_handler() -> InputHandler:
    """Get the global input handler instance."""
    global _input_handler
    if _input_handler is None:
        _input_handler = InputHandler()
    return _input_handler
