"""
Interactive input handler with autocomplete for llm_supercli.
Provides rich interactive prompts with dropdown menus.
"""
import sys
import os
from typing import List, Optional, Tuple

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.table import Table

from .theme import get_theme_manager
from .autocomplete import InteractiveCompleter
from ..constants import SLASH_PREFIX, SHELL_PREFIX, FILE_PREFIX


# Try to import keyboard handling
if sys.platform == 'win32':
    import msvcrt
    HAS_MSVCRT = True
else:
    HAS_MSVCRT = False
    try:
        import termios
        import tty
        HAS_TERMIOS = True
    except ImportError:
        HAS_TERMIOS = False


def get_key_windows() -> str:
    """Get a keypress on Windows."""
    if msvcrt.kbhit():
        key = msvcrt.getwch()
        if key == '\xe0':  # Special key prefix
            key2 = msvcrt.getwch()
            if key2 == 'H':
                return 'UP'
            elif key2 == 'P':
                return 'DOWN'
            elif key2 == 'K':
                return 'LEFT'
            elif key2 == 'M':
                return 'RIGHT'
            return ''
        elif key == '\t':
            return 'TAB'
        elif key == '\r':
            return 'ENTER'
        elif key == '\x1b':
            return 'ESC'
        elif key == '\x08':
            return 'BACKSPACE'
        return key
    return ''


class InteractiveInput:
    """
    Interactive input handler with visual autocomplete.
    
    Supports:
    - Tab completion with dropdown menu
    - Arrow key navigation
    - Mode indicators (bash mode, file mode)
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize interactive input."""
        self._theme = get_theme_manager()
        self._console = console or Console(theme=self._theme.get_rich_theme())
        self._completer = InteractiveCompleter(self._console)
        self._buffer = ""
        self._cursor_pos = 0
        self._history: List[str] = []
        self._history_index = -1
        self._show_menu = False
        self._mode: Optional[str] = None
    
    def set_commands(self, commands: List[dict]) -> None:
        """Set available commands for completion."""
        self._completer.set_commands(commands)
    
    def _detect_mode(self, text: str) -> Optional[str]:
        """Detect input mode from text."""
        text = text.strip()
        if text.startswith(SHELL_PREFIX):
            return "shell"
        elif text.startswith(FILE_PREFIX):
            return "file"
        elif text.startswith(SLASH_PREFIX):
            return "command"
        return None
    
    def _get_mode_indicator(self) -> str:
        """Get mode indicator text."""
        if self._mode == "shell":
            return "[bold yellow]Shell mode[/] [dim]- Execute shell commands[/]"
        elif self._mode == "file":
            return "[bold cyan]File mode[/] [dim]- Include file contents[/]"
        elif self._mode == "command":
            return "[bold magenta]Command mode[/] [dim]- Slash commands[/]"
        return ""
    
    def _render_input_line(self, prompt: str) -> Text:
        """Render the input line with cursor."""
        text = Text()
        text.append(prompt, style=self._theme.get_style("prompt"))
        text.append(self._buffer)
        return text
    
    def _render_menu(self) -> Optional[Panel]:
        """Render the autocomplete menu."""
        items, completer_type = self._completer.get_completions(self._buffer)
        
        if not items:
            return None
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Item", style="cyan")
        table.add_column("Desc", style="dim")
        
        for i, (value, desc) in enumerate(items[:10]):
            prefix = "> " if i == self._completer._menu._selected_index else "  "
            style = "bold cyan" if i == self._completer._menu._selected_index else ""
            table.add_row(f"{prefix}{value}", desc, style=style)
        
        title = {
            "command": "Commands",
            "file": "Files",
            "shell": "Shell"
        }.get(completer_type, "Suggestions")
        
        return Panel(
            table,
            title=f"[bold]{title}[/]",
            subtitle="[dim]Tab: select | Arrows: navigate | Esc: close[/]",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def get_input(self, prompt: str = ">>> ") -> str:
        """
        Get input with interactive autocomplete.
        
        This is a simplified version that falls back to standard input
        but shows completions on Tab press.
        """
        self._buffer = ""
        self._show_menu = False
        self._mode = None
        
        while True:
            # Show mode indicator if active
            mode = self._detect_mode(self._buffer)
            if mode != self._mode:
                self._mode = mode
                indicator = self._get_mode_indicator()
                if indicator:
                    self._console.print(indicator)
            
            # Show prompt and get character
            styled_prompt = Text(prompt, style=self._theme.get_style("prompt"))
            self._console.print(styled_prompt, end="")
            self._console.print(self._buffer, end="")
            
            try:
                if HAS_MSVCRT:
                    # Windows interactive mode
                    return self._windows_input(prompt)
                else:
                    # Fallback to simple input
                    return self._simple_input(prompt)
            except (EOFError, KeyboardInterrupt):
                return "/quit"
    
    def _simple_input(self, prompt: str) -> str:
        """Simple input fallback with Tab completion display."""
        # Print prompt
        styled_prompt = Text(prompt, style=self._theme.get_style("prompt"))
        
        # Show mode if detected from initial chars
        line = input()
        self._buffer = line
        
        # Detect mode
        mode = self._detect_mode(line)
        if mode:
            self._mode = mode
        
        # If ends with Tab or user wants completion
        if line.endswith('\t') or (not line.strip() and line):
            line = line.rstrip('\t')
            items, _ = self._completer.get_completions(line)
            if items:
                self._console.print()
                menu = self._render_menu()
                if menu:
                    self._console.print(menu)
                # Let user continue
                return self._simple_input(prompt)
        
        if line.strip():
            self._history.append(line)
        
        return line
    
    def _windows_input(self, prompt: str) -> str:
        """Windows interactive input with real-time completion."""
        self._buffer = ""
        self._cursor_pos = 0
        
        while True:
            # Clear and redraw
            self._console.print(f"\r{prompt}{self._buffer}", end="")
            
            # Check for key
            if msvcrt.kbhit():
                key = get_key_windows()
                
                if key == 'ENTER':
                    self._console.print()  # New line
                    result = self._buffer
                    if result.strip():
                        self._history.append(result)
                    self._buffer = ""
                    self._show_menu = False
                    return result
                
                elif key == 'TAB':
                    # Show/use completion
                    items, _ = self._completer.get_completions(self._buffer)
                    if items:
                        if self._show_menu:
                            # Select current item
                            selected = self._completer.get_selected()
                            if selected:
                                self._buffer = selected
                                self._show_menu = False
                                self._completer.reset()
                        else:
                            # Show menu
                            self._show_menu = True
                            self._console.print()
                            menu = self._render_menu()
                            if menu:
                                self._console.print(menu)
                
                elif key == 'UP':
                    if self._show_menu:
                        self._completer.move_up()
                        self._console.print()
                        menu = self._render_menu()
                        if menu:
                            self._console.print(menu)
                    else:
                        # History navigation
                        if self._history and self._history_index < len(self._history) - 1:
                            self._history_index += 1
                            self._buffer = self._history[-(self._history_index + 1)]
                
                elif key == 'DOWN':
                    if self._show_menu:
                        self._completer.move_down()
                        self._console.print()
                        menu = self._render_menu()
                        if menu:
                            self._console.print(menu)
                    else:
                        # History navigation
                        if self._history_index > 0:
                            self._history_index -= 1
                            self._buffer = self._history[-(self._history_index + 1)]
                        elif self._history_index == 0:
                            self._history_index = -1
                            self._buffer = ""
                
                elif key == 'ESC':
                    if self._show_menu:
                        self._show_menu = False
                        self._completer.reset()
                    else:
                        self._buffer = ""
                
                elif key == 'BACKSPACE':
                    if self._buffer:
                        self._buffer = self._buffer[:-1]
                    self._show_menu = False
                
                elif len(key) == 1 and key.isprintable():
                    self._buffer += key
                    self._show_menu = False
                    
                    # Auto-show menu for special prefixes
                    mode = self._detect_mode(self._buffer)
                    if mode and len(self._buffer) >= 1:
                        items, _ = self._completer.get_completions(self._buffer)
                        if items and len(items) <= 10:
                            self._show_menu = True
                            self._console.print()
                            menu = self._render_menu()
                            if menu:
                                self._console.print(menu)


class SimpleInteractiveInput:
    """
    Simpler interactive input that works cross-platform.
    Shows completions but uses standard input.
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        self._theme = get_theme_manager()
        self._console = console or Console(theme=self._theme.get_rich_theme())
        self._completer = InteractiveCompleter(self._console)
        self._history: List[str] = []
    
    def set_commands(self, commands: List[dict]) -> None:
        """Set available commands."""
        self._completer.set_commands(commands)
    
    def get_input(self, prompt: str = ">>> ") -> str:
        """Get input with completion hints."""
        # Show prompt
        styled_prompt = Text(prompt, style=self._theme.get_style("prompt"))
        self._console.print(styled_prompt, end="")
        
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            self._console.print()
            return "/quit"
        
        # Detect mode and show indicator
        mode = self._get_mode(line)
        if mode:
            self._show_mode_indicator(mode)
        
        # Show completions hint on partial input
        if line and not line.endswith(' '):
            items, ctype = self._completer.get_completions(line)
            if items and len(items) > 0:
                self._show_completion_hint(items, ctype)
        
        if line.strip():
            self._history.append(line)
        
        return line
    
    def _get_mode(self, text: str) -> Optional[str]:
        """Get mode from text."""
        text = text.strip()
        if text.startswith("!"):
            return "shell"
        elif text.startswith("@"):
            return "file"
        elif text.startswith("/"):
            return "command"
        return None
    
    def _show_mode_indicator(self, mode: str) -> None:
        """Show mode indicator."""
        indicators = {
            "shell": "[bold yellow]Shell mode active[/]",
            "file": "[bold cyan]File inclusion mode[/]",
            "command": "[bold magenta]Command mode[/]"
        }
        if mode in indicators:
            self._console.print(indicators[mode])
    
    def _show_completion_hint(self, items: List[Tuple[str, str]], ctype: str) -> None:
        """Show completion hint."""
        if len(items) <= 5:
            hints = [item[0] for item in items]
            self._console.print(f"[dim]Suggestions: {', '.join(hints)}[/]")
        else:
            self._console.print(f"[dim]{len(items)} matches - press Tab for menu[/]")
