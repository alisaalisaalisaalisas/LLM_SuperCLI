"""
Interactive input handler using prompt_toolkit for llm_supercli.
Provides real-time autocomplete with dropdown menus and bordered input panel.

Requirements: 2.1, 2.2, 2.3, 2.4 - Input Prompt Panel
"""
import os
from pathlib import Path
from typing import List, Optional, Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .theme import get_theme_manager


# Default placeholder text for input panel
DEFAULT_PLACEHOLDER = "> Type a message or /command..."


# Custom style for the prompt - dark theme
PROMPT_STYLE = Style.from_dict({
    'prompt': '#00ff00',  # bright green
    'path': '#6a4c93',    # dark violet for path
    'model': '#00d7d7',   # cyan for model
    'context': '#00d7d7',
    'bottom-toolbar': 'bg:#1a1a1a #666666',
    'bottom-toolbar.text': '#666666',
    'completion-menu.completion': 'bg:#262626 #ffffff',
    'completion-menu.completion.current': 'bg:#00aaaa #000000 bold',
    'completion-menu.meta.completion': 'bg:#262626 #666666',
    'completion-menu.meta.completion.current': 'bg:#00aaaa #000000',
    'placeholder': '#666666 italic',
})


class CLICompleter(Completer):
    """
    Custom completer that handles /, @, and ! prefixes.
    
    Requirements: 2.4 - Autocomplete dropdown for /, @, and ! prefixes
    """
    
    def __init__(self) -> None:
        self._commands: List[tuple] = []
        self._shell_commands = [
            ('ls', 'List directory contents'),
            ('dir', 'List directory (Windows)'),
            ('cd', 'Change directory'),
            ('pwd', 'Print working directory'),
            ('cat', 'Display file contents'),
            ('type', 'Display file (Windows)'),
            ('echo', 'Print text'),
            ('git status', 'Git status'),
            ('git diff', 'Git diff'),
            ('git log', 'Git log'),
            ('python', 'Run Python'),
            ('pip install', 'Install package'),
            ('npm', 'Node package manager'),
        ]

    def set_commands(self, commands: List[dict]) -> None:
        """Set available slash commands."""
        self._commands = [
            (cmd['name'], cmd['description'][:50])
            for cmd in commands
        ]
    
    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completions based on current input."""
        text = document.text_before_cursor
        
        if not text:
            return
        
        try:
            if text.startswith('/'):
                yield from self._get_command_completions(text, document)
            elif text.startswith('!'):
                yield from self._get_shell_completions(text, document)
            else:
                # Check for @ anywhere in text (for file completion mid-sentence)
                at_pos = text.rfind('@')
                if at_pos >= 0:
                    # Check if there's a space after the @, meaning it's completed
                    text_after_at = text[at_pos:]
                    if ' ' not in text_after_at[1:]:
                        # Active @ mention - get file completions
                        yield from self._get_file_completions_at(text, at_pos, document)
        except Exception:
            pass
    
    def _get_file_completions_at(self, full_text: str, at_pos: int, document: Document) -> Iterable[Completion]:
        """Get file completions for @ at any position in text."""
        # Extract the @... part being typed
        at_text = full_text[at_pos:]
        path_text = at_text[1:]  # Remove @
        
        try:
            if not path_text:
                search_dir = Path.cwd()
                prefix = ''
            else:
                path = Path(path_text).expanduser()
                if path.is_dir():
                    search_dir = path
                    prefix = path_text.rstrip('/\\') + os.sep
                elif path.parent.exists():
                    search_dir = path.parent
                    prefix = str(path.parent)
                    if prefix != '.':
                        prefix += os.sep
                    else:
                        prefix = ''
                else:
                    return
            
            partial_name = Path(path_text).name.lower() if path_text and not path_text.endswith(os.sep) else ''
            
            # Get files quickly - limit to 20 items
            items = []
            try:
                for item in search_dir.iterdir():
                    if len(items) >= 20:
                        break
                    if partial_name and partial_name not in item.name.lower():
                        continue
                    items.append(item)
            except (OSError, PermissionError):
                return
            
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                name = item.name
                
                if item.is_dir():
                    display_name = f'{name}/'
                    meta = '[DIR]'
                else:
                    try:
                        size = item.stat().st_size
                        meta = self._format_size(size)
                    except OSError:
                        meta = ''
                    display_name = name
                
                file_ref = f'@{prefix}{name}' + ('/' if item.is_dir() else '')
                
                # Replace only from @ position to cursor
                yield Completion(
                    file_ref,
                    start_position=-len(at_text),
                    display=display_name,
                    display_meta=meta
                )
        except Exception:
            pass
    
    def _get_command_completions(self, text: str, document: Document) -> Iterable[Completion]:
        """Get slash command completions."""
        query = text[1:].lower()  # Remove /
        
        for name, desc in self._commands:
            if query in name.lower():
                yield Completion(
                    f'/{name}',
                    start_position=-len(text),
                    display=f'/{name}',
                    display_meta=desc
                )
    
    def _get_file_completions(self, text: str, document: Document) -> Iterable[Completion]:
        """Get file path completions."""
        # Handle both @ and file: prefixes
        if text.startswith('file:'):
            prefix_char = 'file:'
            path_text = text[5:]
        else:
            prefix_char = '@'
            path_text = text[1:]  # Remove @
        
        try:
            if not path_text:
                search_dir = Path.cwd()
                prefix = ''
            else:
                path = Path(path_text).expanduser()
                if path.is_dir():
                    search_dir = path
                    prefix = path_text.rstrip('/\\') + os.sep
                elif path.parent.exists():
                    search_dir = path.parent
                    prefix = str(path.parent)
                    if prefix != '.':
                        prefix += os.sep
                    else:
                        prefix = ''
                else:
                    return
            
            partial_name = Path(path_text).name.lower() if path_text and not path_text.endswith(os.sep) else ''
            
            # Get files quickly - limit to 20 items
            items = []
            try:
                for item in search_dir.iterdir():
                    if len(items) >= 20:
                        break
                    if partial_name and partial_name not in item.name.lower():
                        continue
                    items.append(item)
            except (OSError, PermissionError):
                return
            
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                name = item.name
                
                if item.is_dir():
                    display_name = f'{name}/'
                    meta = '[DIR]'
                else:
                    try:
                        size = item.stat().st_size
                        meta = self._format_size(size)
                    except OSError:
                        meta = ''
                    display_name = name
                
                full_path = f'{prefix_char}{prefix}{name}' + ('/' if item.is_dir() else '')
                
                yield Completion(
                    full_path,
                    start_position=-len(text),
                    display=display_name,
                    display_meta=meta
                )
        except Exception:
            pass
    
    def _get_shell_completions(self, text: str, document: Document) -> Iterable[Completion]:
        """Get shell command completions."""
        query = text[1:].lower()  # Remove !
        
        for cmd, desc in self._shell_commands:
            if query in cmd.lower():
                yield Completion(
                    f'!{cmd}',
                    start_position=-len(text),
                    display=f'!{cmd}',
                    display_meta=desc
                )
    
    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.0f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'


class InputPanel:
    """
    Bordered input panel component with placeholder text.
    
    Requirements:
    - 2.1: Display bordered panel with placeholder text
    - 2.2: Replace placeholder with actual input text
    - 2.3: Clear input panel after submission
    
    Display format:
    ┌─────────────────────────────────────────────────────────────────┐
    │ > Type a message or /command...                                 │
    └─────────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize the InputPanel.
        
        Args:
            console: Optional Rich Console instance
        """
        self._console = console or Console(force_terminal=True, color_system="auto")
        self._theme = get_theme_manager()
        self._placeholder = DEFAULT_PLACEHOLDER
        self._content = ""
        self._width: Optional[int] = None
    
    @property
    def placeholder(self) -> str:
        """Get the placeholder text."""
        return self._placeholder
    
    @placeholder.setter
    def placeholder(self, value: str) -> None:
        """Set the placeholder text."""
        self._placeholder = value
    
    @property
    def content(self) -> str:
        """Get the current input content."""
        return self._content
    
    def set_content(self, text: str) -> None:
        """
        Set the input content.
        
        Requirements: 2.2 - Replace placeholder with actual input text
        
        Args:
            text: Input text to display
        """
        self._content = text
    
    def clear(self) -> None:
        """
        Clear the input content.
        
        Requirements: 2.3 - Clear input panel after submission
        """
        self._content = ""
    
    def set_width(self, width: int) -> None:
        """
        Set the panel width.
        
        Args:
            width: Width in columns
        """
        self._width = width
    
    def render(self, width: Optional[int] = None) -> Panel:
        """
        Render the input panel.
        
        Requirements: 2.1 - Display bordered panel with placeholder
        
        Args:
            width: Optional width override
            
        Returns:
            Panel containing input area
        """
        effective_width = width or self._width or self._console.width
        
        # Build content text
        if self._content:
            # Show actual input text
            text = Text(self._content, style=self._theme.get_style("prompt"))
        else:
            # Show placeholder
            text = Text(self._placeholder, style="dim italic")
        
        # Get theme colors for border
        border_style = self._theme.get_color("primary") or "cyan"
        
        return Panel(
            text,
            border_style=border_style,
            padding=(0, 1),
            width=effective_width - 2 if effective_width else None,
        )
    
    def render_text(self) -> Text:
        """
        Render just the text content (without panel border).
        
        Returns:
            Text object with content or placeholder
        """
        if self._content:
            return Text(self._content, style=self._theme.get_style("prompt"))
        else:
            return Text(self._placeholder, style="dim italic")
    
    def print(self, width: Optional[int] = None) -> None:
        """
        Print the input panel to console.
        
        Args:
            width: Optional width override
        """
        self._console.print(self.render(width))


def get_status_bar(cwd: str, model: str, context_pct: int = 100) -> str:
    """Get status bar showing directory, model, and context."""
    import os
    
    # Get git branch if available
    git_branch = ""
    try:
        git_dir = os.path.join(cwd, '.git')
        if os.path.isdir(git_dir):
            head_file = os.path.join(git_dir, 'HEAD')
            if os.path.isfile(head_file):
                with open(head_file, 'r') as f:
                    ref = f.read().strip()
                    if ref.startswith('ref: refs/heads/'):
                        git_branch = f" ({ref[16:]})"
    except:
        pass
    
    # Format path (use ~ for home)
    home = os.path.expanduser('~')
    if cwd.startswith(home):
        display_path = '~' + cwd[len(home):].replace('\\', '/')
    else:
        display_path = cwd.replace('\\', '/')
    
    # Build status bar
    left = f"{display_path}{git_branch}"
    right = f"{model} ({context_pct}% context)"
    
    return f" {left}    |    {right} "


class PromptInput:
    """
    Interactive input handler with prompt_toolkit.
    
    Features:
    - Bordered input panel with placeholder text
    - Status bar showing directory, model, context
    - Dropdown autocomplete for /, @, !
    - Tab/Arrow navigation
    - Command history
    
    Requirements:
    - 2.1: Display bordered panel with placeholder text
    - 2.2: Replace placeholder with actual input text
    - 2.3: Clear input panel after submission
    - 2.4: Show autocomplete dropdown for /, @, and ! prefixes
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize the PromptInput.
        
        Args:
            console: Optional Rich Console instance
        """
        self._console = console or Console(force_terminal=True, color_system="auto")
        self._completer = CLICompleter()
        self._history = InMemoryHistory()
        self._session: Optional[PromptSession] = None
        self._current_text = ''
        self._cwd = os.getcwd()
        self._model = 'groq/llama-3.3-70b'
        self._context_pct = 100
        self._input_panel = InputPanel(console=self._console)
        self._theme = get_theme_manager()
    
    @property
    def input_panel(self) -> InputPanel:
        """Get the input panel component."""
        return self._input_panel
    
    def set_commands(self, commands: List[dict]) -> None:
        """Set available slash commands."""
        self._completer.set_commands(commands)
    
    def set_status(self, cwd: str = None, model: str = None, context_pct: int = None) -> None:
        """Update status bar info."""
        if cwd is not None:
            self._cwd = cwd
        if model is not None:
            self._model = model
        if context_pct is not None:
            self._context_pct = context_pct
    
    def set_placeholder(self, placeholder: str) -> None:
        """
        Set the input placeholder text.
        
        Requirements: 2.1 - Display placeholder text
        
        Args:
            placeholder: Placeholder text to display
        """
        self._input_panel.placeholder = placeholder
    
    def _get_toolbar(self) -> HTML:
        """Get bottom toolbar with status info."""
        return HTML(get_status_bar(self._cwd, self._model, self._context_pct))
    
    def _create_session(self) -> PromptSession:
        """Create a new prompt session."""
        return PromptSession(
            completer=self._completer,
            complete_while_typing=True,
            history=self._history,
            style=PROMPT_STYLE,
            mouse_support=False,
            reserve_space_for_menu=8,
        )
    
    def render_panel(self, width: Optional[int] = None) -> Panel:
        """
        Render the input panel for display.
        
        Requirements: 2.1 - Display bordered panel
        
        Args:
            width: Optional width override
            
        Returns:
            Panel containing input area
        """
        return self._input_panel.render(width)
    
    def get_input(self, prompt: str = '>>> ', show_panel: bool = False) -> str:
        """
        Get input with interactive autocomplete and dropdown menus.
        
        Requirements:
        - 2.2: Replace placeholder with actual input text
        - 2.3: Clear input panel after submission
        - 2.4: Show autocomplete dropdown
        
        Args:
            prompt: Prompt string to display
            show_panel: Whether to show bordered panel before input
            
        Returns:
            User input string
        """
        self._current_text = ''
        
        # Show bordered panel if requested
        if show_panel:
            self._input_panel.print()
        
        if self._session is None:
            self._session = self._create_session()
        
        try:
            result = self._session.prompt(prompt)
            self._current_text = result
            
            # Clear input panel after submission (Requirement 2.3)
            self._input_panel.clear()
            
            return result
        except EOFError:
            return '/quit'
        except KeyboardInterrupt:
            return ''
    
    def get_input_with_panel(self, width: Optional[int] = None) -> str:
        """
        Get input with bordered panel display.
        
        This method shows the bordered input panel before prompting.
        
        Requirements: 2.1, 2.2, 2.3, 2.4
        
        Args:
            width: Optional width for panel
            
        Returns:
            User input string
        """
        # Set panel width if provided
        if width:
            self._input_panel.set_width(width)
        
        return self.get_input(prompt='>>> ', show_panel=True)


# Global instances
_prompt_input: Optional[PromptInput] = None
_input_panel: Optional[InputPanel] = None


def get_prompt_input(console: Optional[Console] = None) -> PromptInput:
    """
    Get global prompt input instance.
    
    Args:
        console: Optional console to use (only used on first call)
        
    Returns:
        Global PromptInput instance
    """
    global _prompt_input
    if _prompt_input is None:
        _prompt_input = PromptInput(console=console)
    return _prompt_input


def get_input_panel(console: Optional[Console] = None) -> InputPanel:
    """
    Get global input panel instance.
    
    Args:
        console: Optional console to use (only used on first call)
        
    Returns:
        Global InputPanel instance
    """
    global _input_panel
    if _input_panel is None:
        _input_panel = InputPanel(console=console)
    return _input_panel
