"""
Falling dropdown menu component for llm_supercli.
Provides inline selection menus with keyboard navigation.
"""
import sys
from typing import List, Optional, Tuple, Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live


if sys.platform == 'win32':
    import msvcrt
    HAS_MSVCRT = True
else:
    HAS_MSVCRT = False
    try:
        import termios
        import tty
        import select
        HAS_TERMIOS = True
    except ImportError:
        HAS_TERMIOS = False


def _get_key_windows() -> str:
    """Get a keypress on Windows."""
    key = msvcrt.getwch()
    if key == '\xe0' or key == '\x00':
        key2 = msvcrt.getwch()
        mapping = {'H': 'UP', 'P': 'DOWN', 'K': 'LEFT', 'M': 'RIGHT'}
        return mapping.get(key2, '')
    elif key == '\t':
        return 'TAB'
    elif key == '\r':
        return 'ENTER'
    elif key == '\x1b':
        return 'ESC'
    elif key == '\x08':
        return 'BACKSPACE'
    return key


def _get_key_unix() -> str:
    """Get a keypress on Unix systems."""
    import sys
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    mapping = {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}
                    return mapping.get(ch3, 'ESC')
            return 'ESC'
        elif ch == '\r' or ch == '\n':
            return 'ENTER'
        elif ch == '\t':
            return 'TAB'
        elif ch == '\x7f':
            return 'BACKSPACE'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_key() -> str:
    """Get a keypress cross-platform."""
    if HAS_MSVCRT:
        return _get_key_windows()
    elif HAS_TERMIOS:
        return _get_key_unix()
    return ''


class FallingMenu:
    """
    Inline falling dropdown menu with keyboard navigation.
    
    Features:
    - Arrow key navigation (UP/DOWN)
    - Enter to select
    - ESC to cancel
    - Visual highlighting of selected item
    - Support for nested menus
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        title: str = "Select Option",
        style: str = "cyan"
    ) -> None:
        self._console = console or Console()
        self._title = title
        self._style = style
        self._selected_index = 0
        self._items: List[Tuple[Any, str, str]] = []
    
    def _render_menu(self) -> Panel:
        """Render the menu panel."""
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Selector", width=2)
        table.add_column("Item", style=self._style)
        table.add_column("Description", style="dim")
        
        for i, (value, label, desc) in enumerate(self._items):
            is_selected = i == self._selected_index
            selector = ">" if is_selected else " "
            row_style = f"bold {self._style} reverse" if is_selected else ""
            table.add_row(selector, label, desc, style=row_style)
        
        return Panel(
            table,
            title=f"[bold]{self._title}[/]",
            subtitle="[dim]UP/DOWN: navigate | ENTER: select | ESC: cancel[/]",
            border_style=self._style,
            padding=(0, 1)
        )
    
    def show(
        self,
        items: List[Tuple[Any, str, str]],
        default_index: int = 0
    ) -> Optional[Any]:
        """
        Show the falling menu and get user selection.
        
        Args:
            items: List of (value, label, description) tuples
            default_index: Initial selected index
            
        Returns:
            Selected value or None if cancelled
        """
        if not items:
            self._console.print("[yellow]No options available[/]")
            return None
        
        self._items = items
        self._selected_index = min(default_index, len(items) - 1)
        
        self._console.print()
        
        with Live(self._render_menu(), console=self._console, refresh_per_second=10) as live:
            while True:
                key = get_key()
                
                if key == 'UP':
                    self._selected_index = (self._selected_index - 1) % len(self._items)
                    live.update(self._render_menu())
                
                elif key == 'DOWN':
                    self._selected_index = (self._selected_index + 1) % len(self._items)
                    live.update(self._render_menu())
                
                elif key == 'ENTER':
                    selected_value = self._items[self._selected_index][0]
                    return selected_value
                
                elif key == 'ESC' or key == 'q':
                    return None
    
    def show_with_input(
        self,
        items: List[Tuple[Any, str, str]],
        input_prompt: str = "Enter value: ",
        validator: Optional[Callable[[str], bool]] = None
    ) -> Optional[Tuple[Any, str]]:
        """
        Show menu, then prompt for input value after selection.
        
        Args:
            items: List of (value, label, description) tuples
            input_prompt: Prompt for value input
            validator: Optional function to validate input
            
        Returns:
            Tuple of (selected_key, entered_value) or None if cancelled
        """
        selected = self.show(items)
        if selected is None:
            return None
        
        self._console.print()
        self._console.print(f"[{self._style}]Selected: {selected}[/]")
        
        while True:
            try:
                value = self._console.input(f"[dim]{input_prompt}[/]")
                if validator and not validator(value):
                    self._console.print("[red]Invalid value, try again[/]")
                    continue
                return (selected, value)
            except (EOFError, KeyboardInterrupt):
                return None


class SettingsMenu:
    """
    Multi-step settings menu with falling dropdowns.
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        self._console = console or Console()
    
    def _get_providers_list(self) -> List[Tuple[str, str, str]]:
        """Get list of available providers."""
        try:
            from ..llm.provider_registry import get_provider_registry
            registry = get_provider_registry()
            providers = registry.list_providers()
            items = []
            for p in providers:
                info = registry.get_provider_info(p)
                has_key = info.get("has_api_key", False) if info else False
                status = "[OK]" if has_key else "[No Key]"
                items.append((p, p.title(), status))
            return items
        except Exception:
            return [
                ("groq", "Groq", "Fast inference"),
                ("openrouter", "OpenRouter", "Multi-provider"),
                ("gemini", "Gemini", "Google AI"),
                ("qwen", "Qwen", "Alibaba AI"),
            ]
    
    def _get_models_list(self, provider: str) -> List[Tuple[str, str, str]]:
        """Get list of models for a provider."""
        try:
            from ..llm.provider_registry import get_provider_registry
            registry = get_provider_registry()
            info = registry.get_provider_info(provider)
            if info and info.get("available_models"):
                models = info["available_models"][:30]  # Limit to 30
                return [(m, m, "") for m in models]
        except Exception:
            pass
        return []
    
    def show(self, config) -> Optional[Tuple[str, Any]]:
        """
        Show interactive settings menu.
        
        Returns:
            Tuple of (setting_key, new_value) or None if cancelled
        """
        # Step 1: Select category
        categories = [
            ("llm", "LLM Settings", "Provider, model, temperature, max_tokens"),
            ("ui", "UI Settings", "Theme, streaming, syntax highlighting"),
            ("mcp", "MCP Settings", "Enable/disable MCP features"),
        ]
        
        cat_menu = FallingMenu(
            self._console,
            title="Settings Category",
            style="cyan"
        )
        
        selected_cat = cat_menu.show(categories)
        if selected_cat is None:
            return None
        
        # Step 2: Select setting within category
        settings_by_cat = {
            "llm": [
                ("provider", "Provider", f"Current: {config.llm.provider}"),
                ("model", "Model", f"Current: {config.llm.model}"),
                ("temperature", "Temperature", f"Current: {config.llm.temperature}"),
                ("max_tokens", "Max Tokens", f"Current: {config.llm.max_tokens}"),
            ],
            "ui": [
                ("theme", "Theme", f"Current: {config.ui.theme}"),
                ("streaming", "Streaming", f"Current: {config.ui.streaming}"),
                ("markdown_rendering", "Markdown Rendering", f"Current: {config.ui.markdown_rendering}"),
                ("syntax_highlighting", "Syntax Highlighting", f"Current: {config.ui.syntax_highlighting}"),
                ("show_token_count", "Show Token Count", f"Current: {config.ui.show_token_count}"),
                ("show_cost", "Show Cost", f"Current: {config.ui.show_cost}"),
            ],
            "mcp": [
                ("enabled", "MCP Enabled", f"Current: {config.mcp.enabled}"),
                ("auto_connect", "Auto Connect", f"Current: {config.mcp.auto_connect}"),
            ],
        }
        
        settings = settings_by_cat.get(selected_cat, [])
        
        setting_menu = FallingMenu(
            self._console,
            title=f"{selected_cat.upper()} Settings",
            style="magenta"
        )
        
        selected_setting = setting_menu.show(settings)
        if selected_setting is None:
            return None
        
        # Step 3: Get new value (with special handling for different setting types)
        bool_settings = ["streaming", "markdown_rendering", "syntax_highlighting", 
                         "show_token_count", "show_cost", "enabled", "auto_connect"]
        
        if selected_setting == "provider":
            # Show provider selection dropdown
            providers = self._get_providers_list()
            if not providers:
                self._console.print("[red]No providers available[/]")
                return None
            value_menu = FallingMenu(
                self._console,
                title="Select Provider",
                style="green"
            )
            new_provider = value_menu.show(providers)
            if new_provider is None:
                return None
            
            # After selecting provider, show model selection for that provider
            models = self._get_models_list(new_provider)
            if models:
                self._console.print(f"[cyan]Provider set to: {new_provider}[/]")
                model_menu = FallingMenu(
                    self._console,
                    title=f"Select Model ({new_provider})",
                    style="green"
                )
                new_model = model_menu.show(models)
                if new_model:
                    # Return special tuple to indicate both provider and model change
                    return ("provider_and_model", (new_provider, new_model))
            
            return ("provider", new_provider)
        
        elif selected_setting == "model":
            # Show model selection dropdown for current provider
            current_provider = config.llm.provider
            models = self._get_models_list(current_provider)
            if not models:
                self._console.print(f"[yellow]No models found for {current_provider}, enter manually:[/]")
                try:
                    new_value = self._console.input("[dim]Model name: [/]")
                except (EOFError, KeyboardInterrupt):
                    return None
            else:
                value_menu = FallingMenu(
                    self._console,
                    title=f"Select Model ({current_provider})",
                    style="green"
                )
                new_value = value_menu.show(models)
        
        elif selected_setting in bool_settings:
            value_items = [
                (True, "True", "Enable this setting"),
                (False, "False", "Disable this setting"),
            ]
            value_menu = FallingMenu(
                self._console,
                title=f"Set {selected_setting}",
                style="green"
            )
            new_value = value_menu.show(value_items)
        
        elif selected_setting == "theme":
            value_items = [
                ("default", "Default", "Default dark theme"),
                ("light", "Light", "Light theme"),
                ("dark", "Dark", "Dark theme"),
                ("monokai", "Monokai", "Monokai color scheme"),
            ]
            value_menu = FallingMenu(
                self._console,
                title="Select Theme",
                style="green"
            )
            new_value = value_menu.show(value_items)
        
        else:
            self._console.print()
            try:
                new_value = self._console.input(f"[dim]Enter new value for {selected_setting}: [/]")
            except (EOFError, KeyboardInterrupt):
                return None
        
        if new_value is None:
            return None
        
        return (selected_setting, new_value)


def select_from_falling_menu(
    items: List[Tuple[Any, str, str]],
    title: str = "Select Option",
    console: Optional[Console] = None
) -> Optional[Any]:
    """
    Convenience function to show a falling menu.
    
    Args:
        items: List of (value, label, description) tuples
        title: Menu title
        console: Optional console instance
        
    Returns:
        Selected value or None
    """
    menu = FallingMenu(console, title)
    return menu.show(items)
