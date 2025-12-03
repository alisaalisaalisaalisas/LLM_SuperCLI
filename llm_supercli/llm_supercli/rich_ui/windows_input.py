"""
Windows-compatible interactive input with dropdown menus.
Uses msvcrt for reliable character input on Windows.
"""
import os
import sys
from pathlib import Path
from typing import List, Optional, Callable

from rich.console import Console
from rich.text import Text

# Windows-specific imports
if sys.platform == 'win32':
    import msvcrt


class DropdownMenu:
    """Dropdown menu for file/command selection."""
    
    def __init__(self, console: Console):
        self.console = console
        self.items: List[tuple] = []  # (display, value, meta)
        self.selected = 0
        self.visible = False
        self.max_visible = 10
    
    def set_items(self, items: List[tuple]):
        """Set menu items as (display, value, meta) tuples."""
        self.items = items[:20]  # Limit items
        self.selected = 0
    
    def move_up(self):
        if self.items:
            self.selected = (self.selected - 1) % len(self.items)
    
    def move_down(self):
        if self.items:
            self.selected = (self.selected + 1) % len(self.items)
    
    def get_selected_value(self) -> Optional[str]:
        if self.items and 0 <= self.selected < len(self.items):
            return self.items[self.selected][1]
        return None
    
    def render(self) -> str:
        """Render menu as string."""
        if not self.items:
            return ""
        
        lines = []
        start = max(0, self.selected - self.max_visible // 2)
        end = min(len(self.items), start + self.max_visible)
        
        for i in range(start, end):
            display, value, meta = self.items[i]
            if i == self.selected:
                lines.append(f"  [reverse] {display} [/reverse] [dim]{meta}[/dim]")
            else:
                lines.append(f"   {display}  [dim]{meta}[/dim]")
        
        if len(self.items) > self.max_visible:
            lines.append(f"  [dim]... {len(self.items)} items total[/dim]")
        
        return "\n".join(lines)


def get_files_in_dir(path: str = "") -> List[tuple]:
    """Get files and folders in directory."""
    items = []
    try:
        if not path:
            search_dir = Path.cwd()
        else:
            p = Path(path).expanduser()
            if p.is_dir():
                search_dir = p
            elif p.parent.exists():
                search_dir = p.parent
            else:
                search_dir = Path.cwd()
        
        for item in sorted(search_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:20]:
            if item.is_dir():
                items.append((f"{item.name}/", f"@{item.name}/", "[DIR]"))
            else:
                try:
                    size = item.stat().st_size
                    if size < 1024:
                        meta = f"{size} B"
                    elif size < 1024 * 1024:
                        meta = f"{size // 1024} KB"
                    else:
                        meta = f"{size // (1024*1024)} MB"
                except:
                    meta = ""
                items.append((item.name, f"@{item.name}", meta))
    except Exception:
        pass
    return items


def get_commands(commands: List[dict]) -> List[tuple]:
    """Get command list for dropdown."""
    items = []
    for cmd in commands:
        name = cmd.get('name', '')
        desc = cmd.get('description', '')[:40]
        items.append((f"/{name}", f"/{name}", desc))
    return items


class WindowsInput:
    """
    Interactive input handler for Windows.
    Shows dropdown menus for @, /, ! prefixes.
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.commands: List[dict] = []
        self.menu = DropdownMenu(console)
        self.current_dir = ""
        self._at_start_pos = -1  # Position where @ was typed
    
    def set_commands(self, commands: List[dict]):
        """Set available slash commands."""
        self.commands = commands
    
    def _find_at_mention(self, buffer: str) -> tuple:
        """Find the current @ mention being typed. Returns (start_pos, mention_text)."""
        # Find the last @ that starts a file reference
        last_at = buffer.rfind('@')
        if last_at == -1:
            return (-1, "")
        # Check if there's a space after this @, meaning it's completed
        text_after_at = buffer[last_at + 1:]
        if ' ' in text_after_at:
            return (-1, "")
        return (last_at, text_after_at)
    
    def get_input(self, prompt: str = ">>> ") -> str:
        """Get input with dropdown support."""
        # Show current directory
        cwd = os.getcwd()
        self.current_dir = os.path.basename(cwd) or cwd
        
        buffer = ""
        menu_active = False
        self._at_start_pos = -1  # Reset @ position for new input
        
        # Print prompt
        full_prompt = f"[bold cyan]{self.current_dir}[/] {prompt}"
        self.console.print(full_prompt, end="")
        
        while True:
            if sys.platform == 'win32':
                # Windows input
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    
                    # Handle special keys
                    if char == '\r':  # Enter
                        print()  # New line
                        if menu_active and self.menu.items:
                            selected = self.menu.get_selected_value()
                            if selected:
                                # Check if we're completing @ mention mid-text
                                if self._at_start_pos >= 0:
                                    result = buffer[:self._at_start_pos] + selected
                                    self._at_start_pos = -1
                                    return result
                                return selected
                        self._at_start_pos = -1
                        return buffer
                    
                    elif char == '\x1b':  # Escape
                        if menu_active:
                            menu_active = False
                            self._at_start_pos = -1
                            self._clear_menu()
                        continue
                    
                    elif char == '\t':  # Tab
                        if menu_active and self.menu.items:
                            selected = self.menu.get_selected_value()
                            if selected:
                                # Check if we're completing a @ mention mid-text
                                at_pos, at_text = self._find_at_mention(buffer)
                                if at_pos >= 0 and self._at_start_pos >= 0:
                                    # Replace only the @mention part
                                    self._clear_line(len(buffer))
                                    buffer = buffer[:self._at_start_pos] + selected
                                    print(buffer, end="", flush=True)
                                    self._at_start_pos = -1
                                else:
                                    # Replace entire buffer (for / and ! at start)
                                    self._clear_line(len(buffer))
                                    buffer = selected
                                    print(buffer, end="", flush=True)
                                menu_active = False
                                self._clear_menu()
                        elif buffer.startswith('/'):
                            self._show_command_menu(buffer[1:])
                            menu_active = True
                        else:
                            # Check for @ anywhere in buffer
                            at_pos, at_text = self._find_at_mention(buffer)
                            if at_pos >= 0:
                                self._at_start_pos = at_pos
                                self._show_file_menu(at_text)
                                menu_active = True
                        continue
                    
                    elif char == '\x00' or char == '\xe0':  # Special key prefix
                        char2 = msvcrt.getwch()
                        if char2 == 'H':  # Up arrow
                            if menu_active:
                                self.menu.move_up()
                                self._update_menu()
                        elif char2 == 'P':  # Down arrow
                            if menu_active:
                                self.menu.move_down()
                                self._update_menu()
                        continue
                    
                    elif char == '\x08':  # Backspace
                        if buffer:
                            buffer = buffer[:-1]
                            print('\b \b', end="", flush=True)
                            if menu_active:
                                # Check if @ mention still valid
                                at_pos, at_text = self._find_at_mention(buffer)
                                if at_pos < 0 or (self._at_start_pos >= 0 and at_pos != self._at_start_pos):
                                    # @ was deleted or changed, close menu
                                    menu_active = False
                                    self._at_start_pos = -1
                                    self._clear_menu()
                                else:
                                    self._update_dropdown(buffer)
                        continue
                    
                    elif char == '\x03':  # Ctrl+C
                        print()
                        return ""
                    
                    else:
                        # Regular character
                        buffer += char
                        print(char, end="", flush=True)
                        
                        # Show dropdown based on prefix or @ anywhere
                        if char == '@':
                            # @ typed - show file menu (works anywhere in buffer)
                            self._at_start_pos = len(buffer) - 1
                            self._show_file_menu("")
                            menu_active = True
                        elif char == ' ' and menu_active and self._at_start_pos >= 0:
                            # Space typed while in @ completion - close menu
                            menu_active = False
                            self._at_start_pos = -1
                            self._clear_menu()
                        elif buffer == '/':
                            self._show_command_menu("")
                            menu_active = True
                        elif buffer == '!':
                            self._show_shell_menu("")
                            menu_active = True
                        elif menu_active:
                            self._update_dropdown(buffer)
            else:
                # Non-Windows fallback
                try:
                    return input()
                except EOFError:
                    return "/quit"
    
    def _show_file_menu(self, filter_text: str):
        """Show file dropdown menu."""
        items = get_files_in_dir(filter_text)
        if filter_text:
            items = [i for i in items if filter_text.lower() in i[0].lower()]
        self.menu.set_items(items)
        self._render_menu()
    
    def _show_command_menu(self, filter_text: str):
        """Show command dropdown menu."""
        items = get_commands(self.commands)
        if filter_text:
            items = [i for i in items if filter_text.lower() in i[0].lower()]
        self.menu.set_items(items)
        self._render_menu()
    
    def _show_shell_menu(self, filter_text: str):
        """Show shell command suggestions."""
        shell_cmds = [
            ("!dir", "!dir", "List directory"),
            ("!ls", "!ls", "List files"),
            ("!cd", "!cd", "Change directory"),
            ("!pwd", "!pwd", "Current directory"),
            ("!type", "!type", "Show file"),
            ("!echo", "!echo", "Print text"),
            ("!git status", "!git status", "Git status"),
            ("!git diff", "!git diff", "Git diff"),
        ]
        if filter_text:
            shell_cmds = [i for i in shell_cmds if filter_text.lower() in i[0].lower()]
        self.menu.set_items(shell_cmds)
        self._render_menu()
    
    def _update_dropdown(self, buffer: str):
        """Update dropdown based on current buffer."""
        # Check for @ mention anywhere in buffer
        at_pos, at_text = self._find_at_mention(buffer)
        if at_pos >= 0 and self._at_start_pos >= 0:
            self._show_file_menu(at_text)
        elif buffer.startswith('/'):
            self._show_command_menu(buffer[1:])
        elif buffer.startswith('!'):
            self._show_shell_menu(buffer[1:])
    
    def _render_menu(self):
        """Render the dropdown menu below input."""
        print()  # Move to next line
        menu_text = self.menu.render()
        if menu_text:
            self.console.print(menu_text)
        # Move cursor back up (approximate)
        lines = menu_text.count('\n') + 2
        print(f"\033[{lines}A\033[999C", end="", flush=True)
    
    def _update_menu(self):
        """Update menu selection."""
        self._clear_menu()
        self._render_menu()
    
    def _clear_menu(self):
        """Clear the menu display."""
        # Clear lines below
        print("\033[J", end="", flush=True)
    
    def _clear_line(self, length: int):
        """Clear characters from current line."""
        print('\b' * length + ' ' * length + '\b' * length, end="", flush=True)


# Singleton
_windows_input: Optional[WindowsInput] = None


def get_windows_input(console: Console) -> WindowsInput:
    """Get or create Windows input handler."""
    global _windows_input
    if _windows_input is None:
        _windows_input = WindowsInput(console)
    return _windows_input
