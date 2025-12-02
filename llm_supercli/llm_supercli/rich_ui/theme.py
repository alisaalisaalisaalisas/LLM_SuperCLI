"""
Theme management for llm_supercli Rich UI.
Loads and applies themes from JSON configuration files.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from rich.style import Style
from rich.theme import Theme as RichTheme

from ..constants import CONFIG_DIR, THEMES_DIR, DEFAULT_THEME


@dataclass
class ThemeColors:
    """Theme color definitions.
    
    Standardized color palette per Requirements 8.1-8.5:
    - primary: Cyan (#00d7d7) for accents and provider names (Req 8.1)
    - success: Green (#00ff00) for success indicators and prompt text (Req 8.2)
    - warning: Yellow for reasoning panels and warnings (Req 8.3)
    - error: Red for error messages and failure indicators (Req 8.4)
    - muted: Dim gray for secondary text and separators (Req 8.5)
    """
    # Primary accent color - cyan for accents and provider names (Req 8.1)
    primary: str = "#00d7d7"
    # Secondary accent color
    secondary: str = "magenta"
    # Accent color - yellow for reasoning panels (Req 8.3)
    accent: str = "#ffff00"
    # Success color - green for success indicators (Req 8.2)
    success: str = "#00ff00"
    # Warning color - yellow for warnings (Req 8.3)
    warning: str = "#ffff00"
    # Error color - red for errors and failures (Req 8.4)
    error: str = "#ff0000"
    # Info color
    info: str = "blue"
    # Muted color - dim gray for secondary text (Req 8.5)
    muted: str = "#666666"
    # Background color
    background: str = "#1a1a1a"
    # Foreground color
    foreground: str = "white"
    # Border color for panels
    border: str = "#333333"


@dataclass
class ThemeStyles:
    """Theme style definitions for different UI elements.
    
    Uses standardized color palette per Requirements 8.1-8.5:
    - Cyan (#00d7d7) for primary accents (Req 8.1)
    - Green (#00ff00) for success and prompt (Req 8.2)
    - Yellow for reasoning and warnings (Req 8.3)
    - Red for errors (Req 8.4)
    - Dim gray (#666666) for secondary text (Req 8.5)
    """
    # Prompt style - green for prompt text (Req 8.2)
    prompt: str = "bold #00ff00"
    # User message style
    user_message: str = "white"
    # Assistant message style - green (Req 8.2)
    assistant_message: str = "#00ff00"
    # System message style - dim gray (Req 8.5)
    system_message: str = "#666666 italic"
    # Error message style - red (Req 8.4)
    error_message: str = "bold #ff0000"
    # Warning message style - yellow (Req 8.3)
    warning_message: str = "bold #ffff00"
    # Info message style
    info_message: str = "blue"
    # Code block styles
    code: str = "on grey23"
    code_border: str = "grey50"
    # Panel styles - cyan for borders (Req 8.1)
    panel_border: str = "#00d7d7"
    panel_title: str = "bold #00d7d7"
    # Header/footer styles
    header: str = "bold white on blue"
    footer: str = "#666666"
    # Highlight style - yellow (Req 8.3)
    highlight: str = "bold #ffff00"
    # Link style
    link: str = "underline blue"
    # Command style
    command: str = "bold magenta"
    # Token/cost display - dim gray (Req 8.5)
    token_count: str = "#666666"
    cost: str = "#666666"
    timestamp: str = "#666666"
    # Spinner style - cyan (Req 8.1)
    spinner: str = "#00d7d7"
    # Reasoning panel style - yellow (Req 8.3)
    reasoning_border: str = "#ffff00"
    reasoning_title: str = "bold #ffff00"
    # Success indicator style - green (Req 8.2)
    success_indicator: str = "bold #00ff00"
    # Failure indicator style - red (Req 8.4)
    failure_indicator: str = "bold #ff0000"


@dataclass
class Theme:
    """Complete theme definition."""
    name: str = "default"
    description: str = "Default theme"
    colors: ThemeColors = field(default_factory=ThemeColors)
    styles: ThemeStyles = field(default_factory=ThemeStyles)
    
    def to_rich_theme(self) -> RichTheme:
        """Convert to Rich Theme object."""
        style_dict = {
            # Color definitions
            "primary": self.colors.primary,
            "secondary": self.colors.secondary,
            "accent": self.colors.accent,
            "success": self.colors.success,
            "warning": self.colors.warning,
            "error": self.colors.error,
            "info": self.colors.info,
            "muted": self.colors.muted,
            "border": self.colors.border,
            # Style definitions
            "prompt": self.styles.prompt,
            "user": self.styles.user_message,
            "assistant": self.styles.assistant_message,
            "system": self.styles.system_message,
            "error_msg": self.styles.error_message,
            "warning_msg": self.styles.warning_message,
            "info_msg": self.styles.info_message,
            "code": self.styles.code,
            "code_border": self.styles.code_border,
            "panel.border": self.styles.panel_border,
            "panel.title": self.styles.panel_title,
            "header": self.styles.header,
            "footer": self.styles.footer,
            "highlight": self.styles.highlight,
            "link": self.styles.link,
            "command": self.styles.command,
            "tokens": self.styles.token_count,
            "cost": self.styles.cost,
            "timestamp": self.styles.timestamp,
            "spinner": self.styles.spinner,
            # Reasoning panel styles (Req 8.3)
            "reasoning.border": self.styles.reasoning_border,
            "reasoning.title": self.styles.reasoning_title,
            # Success/failure indicators (Req 8.2, 8.4)
            "success_indicator": self.styles.success_indicator,
            "failure_indicator": self.styles.failure_indicator,
        }
        return RichTheme(style_dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        """Create Theme from dictionary."""
        colors = ThemeColors(**data.get('colors', {}))
        styles = ThemeStyles(**data.get('styles', {}))
        return cls(
            name=data.get('name', 'custom'),
            description=data.get('description', ''),
            colors=colors,
            styles=styles
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Theme to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'colors': {
                'primary': self.colors.primary,
                'secondary': self.colors.secondary,
                'accent': self.colors.accent,
                'success': self.colors.success,
                'warning': self.colors.warning,
                'error': self.colors.error,
                'info': self.colors.info,
                'muted': self.colors.muted,
                'background': self.colors.background,
                'foreground': self.colors.foreground,
                'border': self.colors.border,
            },
            'styles': {
                'prompt': self.styles.prompt,
                'user_message': self.styles.user_message,
                'assistant_message': self.styles.assistant_message,
                'system_message': self.styles.system_message,
                'error_message': self.styles.error_message,
                'warning_message': self.styles.warning_message,
                'info_message': self.styles.info_message,
                'code': self.styles.code,
                'code_border': self.styles.code_border,
                'panel_border': self.styles.panel_border,
                'panel_title': self.styles.panel_title,
                'header': self.styles.header,
                'footer': self.styles.footer,
                'highlight': self.styles.highlight,
                'link': self.styles.link,
                'command': self.styles.command,
                'token_count': self.styles.token_count,
                'cost': self.styles.cost,
                'timestamp': self.styles.timestamp,
                'spinner': self.styles.spinner,
                'reasoning_border': self.styles.reasoning_border,
                'reasoning_title': self.styles.reasoning_title,
                'success_indicator': self.styles.success_indicator,
                'failure_indicator': self.styles.failure_indicator,
            }
        }


class ThemeManager:
    """
    Manages loading, switching, and applying themes.
    
    Themes are loaded from JSON files in the themes directory.
    """
    
    _instance: Optional['ThemeManager'] = None
    
    def __new__(cls) -> 'ThemeManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._themes: Dict[str, Theme] = {}
        self._current_theme: Theme = Theme()
        self._themes_dir = THEMES_DIR
        self._ensure_themes_dir()
        self._load_builtin_themes()
        self._load_custom_themes()
    
    def _ensure_themes_dir(self) -> None:
        """Create themes directory if it doesn't exist."""
        self._themes_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_builtin_themes(self) -> None:
        """Load built-in themes."""
        self._themes['default'] = Theme()
        
        # Dark theme uses standardized colors with slight brightness adjustments
        dark_colors = ThemeColors(
            primary="#00d7d7",      # Cyan (Req 8.1)
            secondary="bright_magenta",
            accent="#ffff00",       # Yellow (Req 8.3)
            success="#00ff00",      # Green (Req 8.2)
            warning="#ffff00",      # Yellow (Req 8.3)
            error="#ff0000",        # Red (Req 8.4)
            info="bright_blue",
            muted="#666666",        # Dim gray (Req 8.5)
            background="#1a1a1a",
            foreground="grey93",
            border="#333333"
        )
        dark_styles = ThemeStyles(
            prompt="bold #00ff00",           # Green (Req 8.2)
            user_message="grey93",
            assistant_message="#00ff00",     # Green (Req 8.2)
            system_message="#666666 italic", # Dim gray (Req 8.5)
            error_message="bold #ff0000",    # Red (Req 8.4)
            warning_message="bold #ffff00",  # Yellow (Req 8.3)
            info_message="bright_blue",
            code="on grey15",
            code_border="grey42",
            panel_border="#00d7d7",          # Cyan (Req 8.1)
            panel_title="bold #00d7d7",      # Cyan (Req 8.1)
            header="bold white on grey23",
            footer="#666666",                # Dim gray (Req 8.5)
            highlight="bold #ffff00",        # Yellow (Req 8.3)
            link="underline bright_blue",
            command="bold bright_magenta",
            token_count="#666666",           # Dim gray (Req 8.5)
            cost="#666666",                  # Dim gray (Req 8.5)
            timestamp="#666666",             # Dim gray (Req 8.5)
            spinner="#00d7d7",               # Cyan (Req 8.1)
            reasoning_border="#ffff00",      # Yellow (Req 8.3)
            reasoning_title="bold #ffff00",  # Yellow (Req 8.3)
            success_indicator="bold #00ff00", # Green (Req 8.2)
            failure_indicator="bold #ff0000"  # Red (Req 8.4)
        )
        self._themes['dark'] = Theme(
            name="dark",
            description="Dark theme with high contrast",
            colors=dark_colors,
            styles=dark_styles
        )
        
        solarized_colors = ThemeColors(
            primary="#268bd2",
            secondary="#d33682",
            accent="#b58900",
            success="#859900",
            warning="#cb4b16",
            error="#dc322f",
            info="#2aa198",
            muted="#93a1a1",
            background="#002b36",
            foreground="#839496",
            border="#586e75"
        )
        solarized_styles = ThemeStyles(
            prompt="bold #268bd2",
            user_message="#839496",
            assistant_message="#859900",
            system_message="#657b83 italic",
            error_message="bold #dc322f",
            warning_message="bold #cb4b16",
            info_message="#2aa198",
            code="on #073642",
            code_border="#586e75",
            panel_border="#268bd2",
            panel_title="bold #268bd2",
            header="bold #fdf6e3 on #073642",
            footer="#657b83",
            highlight="bold #b58900",
            link="underline #268bd2",
            command="bold #d33682",
            token_count="#657b83",
            cost="#657b83",
            timestamp="#586e75",
            spinner="#268bd2",
            reasoning_border="#b58900",
            reasoning_title="bold #b58900",
            success_indicator="bold #859900",
            failure_indicator="bold #dc322f"
        )
        self._themes['solarized'] = Theme(
            name="solarized",
            description="Solarized dark theme",
            colors=solarized_colors,
            styles=solarized_styles
        )
    
    def _load_custom_themes(self) -> None:
        """Load custom themes from JSON files."""
        if not self._themes_dir.exists():
            return
        
        for theme_file in self._themes_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                theme = Theme.from_dict(data)
                self._themes[theme.name] = theme
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load theme {theme_file}: {e}")
    
    @property
    def current_theme(self) -> Theme:
        """Get the current active theme."""
        return self._current_theme
    
    @property
    def available_themes(self) -> list[str]:
        """Get list of available theme names."""
        return list(self._themes.keys())
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """Get a theme by name."""
        return self._themes.get(name)
    
    def set_theme(self, name: str) -> bool:
        """
        Set the active theme.
        
        Args:
            name: Name of the theme to activate
            
        Returns:
            True if theme was set, False if not found
        """
        if name in self._themes:
            self._current_theme = self._themes[name]
            return True
        return False
    
    def get_rich_theme(self) -> RichTheme:
        """Get the current theme as a Rich Theme object."""
        return self._current_theme.to_rich_theme()
    
    def get_style(self, name: str) -> str:
        """
        Get a style string from the current theme.
        
        Args:
            name: Style name (e.g., 'prompt', 'error_message')
            
        Returns:
            Style string or empty string if not found
        """
        styles = self._current_theme.styles
        return getattr(styles, name, "")
    
    def get_color(self, name: str) -> str:
        """
        Get a color from the current theme.
        
        Args:
            name: Color name (e.g., 'primary', 'error')
            
        Returns:
            Color string or empty string if not found
        """
        colors = self._current_theme.colors
        return getattr(colors, name, "")
    
    def save_theme(self, theme: Theme, filename: Optional[str] = None) -> Path:
        """
        Save a theme to a JSON file.
        
        Args:
            theme: Theme to save
            filename: Optional filename (defaults to theme.name.json)
            
        Returns:
            Path to saved theme file
        """
        if filename is None:
            filename = f"{theme.name}.json"
        
        filepath = self._themes_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(theme.to_dict(), f, indent=2)
        
        self._themes[theme.name] = theme
        return filepath
    
    def create_theme(self, name: str, base_theme: str = "default", **overrides: Any) -> Theme:
        """
        Create a new theme based on an existing one.
        
        Args:
            name: Name for the new theme
            base_theme: Name of theme to base on
            **overrides: Style/color overrides
            
        Returns:
            New Theme object
        """
        base = self._themes.get(base_theme, Theme())
        theme_dict = base.to_dict()
        theme_dict['name'] = name
        
        for key, value in overrides.items():
            if key in theme_dict.get('colors', {}):
                theme_dict['colors'][key] = value
            elif key in theme_dict.get('styles', {}):
                theme_dict['styles'][key] = value
        
        return Theme.from_dict(theme_dict)
    
    def reload_themes(self) -> None:
        """Reload all themes from files."""
        self._themes.clear()
        self._load_builtin_themes()
        self._load_custom_themes()


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return ThemeManager()
