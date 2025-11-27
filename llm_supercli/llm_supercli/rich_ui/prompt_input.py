"""
Interactive input handler using prompt_toolkit for llm_supercli.
Provides real-time autocomplete with dropdown menus.
"""
import os
from pathlib import Path
from typing import List, Optional, Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.layout.processors import Processor, Transformation


# Custom style for the prompt
PROMPT_STYLE = Style.from_dict({
    'prompt': 'bold cyan',
    'mode-shell': 'bold yellow',
    'mode-file': 'bold cyan', 
    'mode-command': 'bold magenta',
    'bottom-toolbar': 'bg:#333333 #ffffff',
    'completion-menu.completion': 'bg:#333333 #ffffff',
    'completion-menu.completion.current': 'bg:#00aaaa #000000',
    'completion-menu.meta.completion': 'bg:#333333 #888888',
    'completion-menu.meta.completion.current': 'bg:#00aaaa #000000',
})


class CLICompleter(Completer):
    """
    Custom completer that handles /, @, and ! prefixes.
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
        
        if text.startswith('/'):
            yield from self._get_command_completions(text, document)
        elif text.startswith('@'):
            yield from self._get_file_completions(text, document)
        elif text.startswith('!'):
            yield from self._get_shell_completions(text, document)
    
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
            
            for item in sorted(search_dir.iterdir())[:30]:
                name = item.name
                if partial_name and partial_name not in name.lower():
                    continue
                
                if item.is_dir():
                    display_name = f'{name}/'
                    meta = '[DIR]'
                else:
                    size = item.stat().st_size
                    meta = self._format_size(size)
                    display_name = name
                
                full_path = f'@{prefix}{name}' + ('/' if item.is_dir() else '')
                
                yield Completion(
                    full_path,
                    start_position=-len(text),
                    display=display_name,
                    display_meta=meta
                )
        except (OSError, PermissionError):
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


def get_mode_toolbar(text: str) -> str:
    """Get toolbar text based on current input mode."""
    text = text.strip()
    
    if text.startswith('!'):
        return '<mode-shell>Shell mode</mode-shell> - Execute shell command | Tab: autocomplete | Enter: execute'
    elif text.startswith('@'):
        return '<mode-file>File mode</mode-file> - Include file contents | Tab: browse files | Enter: confirm'
    elif text.startswith('/'):
        return '<mode-command>Command mode</mode-command> - Slash commands | Tab: autocomplete | Enter: execute'
    else:
        return '<b>Chat mode</b> - Type message | <b>/</b>command | <b>!</b>shell | <b>@</b>file'


class PromptInput:
    """
    Interactive input handler with prompt_toolkit.
    
    Features:
    - Real-time mode indicator in toolbar
    - Dropdown autocomplete for /, @, !
    - Tab/Arrow navigation
    - Command history
    """
    
    def __init__(self) -> None:
        self._completer = CLICompleter()
        self._history = InMemoryHistory()
        self._session: Optional[PromptSession] = None
        self._current_text = ''
    
    def set_commands(self, commands: List[dict]) -> None:
        """Set available slash commands."""
        self._completer.set_commands(commands)
    
    def _get_toolbar(self) -> HTML:
        """Get bottom toolbar based on current input."""
        return HTML(get_mode_toolbar(self._current_text))
    
    def _create_session(self, prompt_text: str) -> PromptSession:
        """Create a new prompt session."""
        return PromptSession(
            completer=self._completer,
            complete_while_typing=True,
            history=self._history,
            style=PROMPT_STYLE,
            bottom_toolbar=self._get_toolbar,
            complete_in_thread=True,
            mouse_support=True,
        )
    
    def get_input(self, prompt: str = '>>> ') -> str:
        """
        Get input with interactive autocomplete.
        
        Args:
            prompt: Prompt string to display
            
        Returns:
            User input string
        """
        self._current_text = ''
        
        if self._session is None:
            self._session = self._create_session(prompt)
        
        try:
            # Custom key bindings to track current text
            bindings = KeyBindings()
            
            @bindings.add('c-c')
            def _(event):
                """Handle Ctrl+C."""
                event.app.exit(result='')
            
            result = self._session.prompt(
                HTML(f'<prompt>{prompt}</prompt>'),
                key_bindings=bindings,
                refresh_interval=0.5,
            )
            
            self._current_text = result
            return result
            
        except EOFError:
            return '/quit'
        except KeyboardInterrupt:
            return ''


# Global instance
_prompt_input: Optional[PromptInput] = None


def get_prompt_input() -> PromptInput:
    """Get global prompt input instance."""
    global _prompt_input
    if _prompt_input is None:
        _prompt_input = PromptInput()
    return _prompt_input
