"""
Interactive input handler using prompt_toolkit for llm_supercli.
Provides real-time autocomplete with dropdown menus.
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


# Custom style for the prompt - dark theme like Qwen
PROMPT_STYLE = Style.from_dict({
    'prompt': '#00ff00',  # bright green
    'path': '#00ff00',    # bright green
    'model': '#00d7d7',  # cyan for model
    'context': '#00d7d7',
    'bottom-toolbar': 'bg:#1a1a1a #666666',
    'bottom-toolbar.text': '#666666',
    'completion-menu.completion': 'bg:#262626 #ffffff',
    'completion-menu.completion.current': 'bg:#00aaaa #000000 bold',
    'completion-menu.meta.completion': 'bg:#262626 #666666',
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
    - Status bar showing directory, model, context
    - Dropdown autocomplete for /, @, !
    - Tab/Arrow navigation
    - Command history
    """
    
    def __init__(self) -> None:
        self._completer = CLICompleter()
        self._history = InMemoryHistory()
        self._session: Optional[PromptSession] = None
        self._current_text = ''
        self._cwd = os.getcwd()
        self._model = 'groq/llama-3.3-70b'
        self._context_pct = 100
    
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
    
    def get_input(self, prompt: str = '>>> ') -> str:
        """Get input with interactive autocomplete and dropdown menus."""
        self._current_text = ''
        
        if self._session is None:
            self._session = self._create_session()
        
        try:
            result = self._session.prompt(prompt)
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
