"""
Autocomplete and dropdown menus for llm_supercli.
Provides interactive completion for commands, files, and shell commands.
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console

from .theme import get_theme_manager


class AutocompleteMenu:
    """
    Interactive autocomplete dropdown menu.
    
    Displays a list of suggestions that can be navigated with arrow keys.
    """
    
    def __init__(self, console: Console, max_items: int = 10) -> None:
        """
        Initialize autocomplete menu.
        
        Args:
            console: Rich console instance
            max_items: Maximum items to display
        """
        self._console = console
        self._max_items = max_items
        self._theme = get_theme_manager()
        self._items: List[Tuple[str, str]] = []  # (value, description)
        self._selected_index = 0
        self._visible = False
        self._filter_text = ""
    
    def set_items(self, items: List[Tuple[str, str]]) -> None:
        """
        Set menu items.
        
        Args:
            items: List of (value, description) tuples
        """
        self._items = items
        self._selected_index = 0
    
    def filter(self, text: str) -> List[Tuple[str, str]]:
        """
        Filter items based on text.
        
        Args:
            text: Filter text
            
        Returns:
            Filtered items
        """
        self._filter_text = text.lower()
        if not self._filter_text:
            return self._items[:self._max_items]
        
        filtered = [
            item for item in self._items
            if self._filter_text in item[0].lower()
        ]
        return filtered[:self._max_items]
    
    def render(self, filtered_items: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        Render the menu as a string.
        
        Args:
            filtered_items: Items to display (uses all if not provided)
            
        Returns:
            Rendered menu string
        """
        items = filtered_items or self._items[:self._max_items]
        
        if not items:
            return ""
        
        lines = []
        for i, (value, desc) in enumerate(items):
            prefix = "> " if i == self._selected_index else "  "
            if desc:
                line = f"{prefix}{value:<30} {desc}"
            else:
                line = f"{prefix}{value}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def move_up(self) -> None:
        """Move selection up."""
        if self._selected_index > 0:
            self._selected_index -= 1
    
    def move_down(self, max_index: int) -> None:
        """Move selection down."""
        if self._selected_index < max_index - 1:
            self._selected_index += 1
    
    def get_selected(self, items: List[Tuple[str, str]]) -> Optional[str]:
        """Get currently selected value."""
        if 0 <= self._selected_index < len(items):
            return items[self._selected_index][0]
        return None
    
    def reset(self) -> None:
        """Reset menu state."""
        self._selected_index = 0
        self._filter_text = ""


class CommandCompleter:
    """Provides command completions for /commands."""
    
    def __init__(self) -> None:
        self._commands: List[Tuple[str, str]] = []
    
    def set_commands(self, commands: List[dict]) -> None:
        """Set available commands from registry."""
        self._commands = [
            (f"/{cmd['name']}", cmd['description'][:50])
            for cmd in commands
        ]
    
    def get_completions(self, text: str) -> List[Tuple[str, str]]:
        """Get command completions for text."""
        if not text.startswith("/"):
            return []
        
        query = text[1:].lower()
        return [
            (cmd, desc) for cmd, desc in self._commands
            if query in cmd[1:].lower()
        ]


class FileCompleter:
    """Provides file path completions for @file."""
    
    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def get_completions(self, text: str) -> List[Tuple[str, str]]:
        """Get file completions for text."""
        if not text.startswith("@"):
            return []
        
        path_text = text[1:]  # Remove @
        
        try:
            if not path_text:
                search_dir = self._base_dir
                prefix = ""
            else:
                path = Path(path_text).expanduser()
                if path.is_absolute():
                    if path.is_dir():
                        search_dir = path
                        prefix = path_text
                    else:
                        search_dir = path.parent
                        prefix = str(path.parent) + os.sep if path.parent != Path(".") else ""
                else:
                    full_path = self._base_dir / path
                    if full_path.is_dir():
                        search_dir = full_path
                        prefix = path_text
                    else:
                        search_dir = full_path.parent
                        prefix = str(path.parent) + os.sep if str(path.parent) != "." else ""
            
            if not prefix.endswith(os.sep) and prefix:
                prefix += os.sep
            
            items = []
            if search_dir.exists():
                for item in sorted(search_dir.iterdir())[:50]:
                    name = item.name
                    if item.is_dir():
                        items.append((f"@{prefix}{name}/", "[DIR]"))
                    else:
                        size = item.stat().st_size
                        size_str = self._format_size(size)
                        items.append((f"@{prefix}{name}", size_str))
            
            # Filter by partial name
            if path_text and not path_text.endswith(os.sep):
                partial = Path(path_text).name.lower()
                items = [
                    (path, desc) for path, desc in items
                    if partial in Path(path[1:]).name.lower()
                ]
            
            return items
            
        except (OSError, PermissionError):
            return []
    
    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.0f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


class ShellCompleter:
    """Provides shell command completions for !command."""
    
    COMMON_COMMANDS = [
        ("!ls", "List directory contents"),
        ("!dir", "List directory (Windows)"),
        ("!cd", "Change directory"),
        ("!pwd", "Print working directory"),
        ("!cat", "Display file contents"),
        ("!type", "Display file (Windows)"),
        ("!echo", "Print text"),
        ("!grep", "Search in files"),
        ("!find", "Find files"),
        ("!git status", "Git status"),
        ("!git diff", "Git diff"),
        ("!git log", "Git log"),
        ("!python", "Run Python"),
        ("!pip", "Python package manager"),
        ("!npm", "Node package manager"),
        ("!node", "Run Node.js"),
    ]
    
    def get_completions(self, text: str) -> List[Tuple[str, str]]:
        """Get shell command completions."""
        if not text.startswith("!"):
            return []
        
        query = text[1:].lower()
        return [
            (cmd, desc) for cmd, desc in self.COMMON_COMMANDS
            if query in cmd[1:].lower()
        ]


class InteractiveCompleter:
    """
    Main interactive completer that handles all completion types.
    """
    
    def __init__(self, console: Console) -> None:
        self._console = console
        self._menu = AutocompleteMenu(console)
        self._command_completer = CommandCompleter()
        self._file_completer = FileCompleter()
        self._shell_completer = ShellCompleter()
        self._active_completer: Optional[str] = None
        self._current_items: List[Tuple[str, str]] = []
    
    def set_commands(self, commands: List[dict]) -> None:
        """Set available commands."""
        self._command_completer.set_commands(commands)
    
    def get_completions(self, text: str) -> Tuple[List[Tuple[str, str]], str]:
        """
        Get completions for current text.
        
        Args:
            text: Current input text
            
        Returns:
            Tuple of (completions, completer_type)
        """
        text = text.strip()
        
        if text.startswith("/"):
            self._active_completer = "command"
            items = self._command_completer.get_completions(text)
        elif text.startswith("@"):
            self._active_completer = "file"
            items = self._file_completer.get_completions(text)
        elif text.startswith("!"):
            self._active_completer = "shell"
            items = self._shell_completer.get_completions(text)
        else:
            self._active_completer = None
            items = []
        
        self._current_items = items
        self._menu.set_items(items)
        return items, self._active_completer or ""
    
    def render_menu(self) -> str:
        """Render current completion menu."""
        return self._menu.render(self._current_items)
    
    def move_up(self) -> None:
        """Move selection up."""
        self._menu.move_up()
    
    def move_down(self) -> None:
        """Move selection down."""
        self._menu.move_down(len(self._current_items))
    
    def get_selected(self) -> Optional[str]:
        """Get selected completion."""
        return self._menu.get_selected(self._current_items)
    
    def reset(self) -> None:
        """Reset completer state."""
        self._menu.reset()
        self._current_items = []
        self._active_completer = None
    
    @property
    def has_completions(self) -> bool:
        """Check if there are completions available."""
        return len(self._current_items) > 0
    
    @property
    def active_type(self) -> Optional[str]:
        """Get active completer type."""
        return self._active_completer
