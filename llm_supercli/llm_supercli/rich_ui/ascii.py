"""
ASCII art and banners for llm_supercli.
"""
from typing import Optional

from rich.console import Console
from rich.text import Text

from ..constants import APP_NAME, APP_VERSION


MAIN_BANNER = r"""
 ██╗     ██╗     ███╗   ███╗    ███████╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗     ██╗
 ██║     ██║     ████╗ ████║    ██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██║
 ██║     ██║     ██╔████╔██║    ███████╗██║   ██║██████╔╝█████╗  ██████╔╝██║     ██║     ██║
 ██║     ██║     ██║╚██╔╝██║    ╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██║
 ███████╗███████╗██║ ╚═╝ ██║    ███████║╚██████╔╝██║     ███████╗██║  ██║╚██████╗███████╗██║
 ╚══════╝╚══════╝╚═╝     ╚═╝    ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝
"""

SMALL_BANNER = r"""
 ╔═╗╦ ╦╔═╗╔═╗╦═╗╔═╗╦  ╦
 ╚═╗║ ║╠═╝║╣ ╠╦╝║  ║  ║
 ╚═╝╚═╝╩  ╚═╝╩╚═╚═╝╩═╝╩
"""

MEDIUM_BANNER = r"""
  _     _     __  __   ____                       ____ _     ___ 
 | |   | |   |  \/  | / ___| _   _ _ __   ___ _ _/ ___| |   |_ _|
 | |   | |   | |\/| | \___ \| | | | '_ \ / _ \ '__| |  | |    | | 
 | |___| |___| |  | |  ___) | |_| | |_) |  __/ |  | |__| |___ | | 
 |_____|_____|_|  |_| |____/ \__,_| .__/ \___|_|   \____|_____|___|
                                 |_|                              
"""

MINI_BANNER = r"""
╔═══════════════════════════════════╗
║        LLM SuperCLI v{version}        ║
╚═══════════════════════════════════╝
"""

ICONS = {
    "robot": "🤖",
    "user": "👤",
    "system": "⚙️",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "thinking": "💭",
    "code": "💻",
    "file": "📄",
    "folder": "📁",
    "key": "🔑",
    "lock": "🔒",
    "unlock": "🔓",
    "clock": "🕐",
    "lightning": "⚡",
    "fire": "🔥",
    "star": "⭐",
    "check": "✓",
    "cross": "✗",
    "arrow_right": "→",
    "arrow_left": "←",
    "arrow_up": "↑",
    "arrow_down": "↓",
    "bullet": "•",
    "diamond": "◆",
    "circle": "○",
    "square": "□",
}

ASCII_ICONS = {
    "robot": "[*]",
    "user": "[U]",
    "system": "[S]",
    "success": "[+]",
    "error": "[X]",
    "warning": "[!]",
    "info": "[i]",
    "thinking": "[?]",
    "code": "[#]",
    "file": "[F]",
    "folder": "[D]",
    "key": "[K]",
    "lock": "[L]",
    "unlock": "[O]",
    "clock": "[T]",
    "lightning": "[Z]",
    "fire": "[~]",
    "star": "[*]",
    "check": "[v]",
    "cross": "[x]",
    "arrow_right": "->",
    "arrow_left": "<-",
    "arrow_up": "^",
    "arrow_down": "v",
    "bullet": "*",
    "diamond": "<>",
    "circle": "o",
    "square": "[]",
}

SPINNERS = [
    "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"
]

ASCII_SPINNERS = [
    "|", "/", "-", "\\"
]

PROGRESS_BARS = {
    "filled": "█",
    "empty": "░",
    "half": "▓",
}

ASCII_PROGRESS_BARS = {
    "filled": "#",
    "empty": "-",
    "half": "=",
}


def _can_use_unicode() -> bool:
    """Check if the terminal supports Unicode."""
    import sys
    try:
        "\U0001f464".encode(sys.stdout.encoding or 'utf-8')
        return True
    except (UnicodeEncodeError, LookupError):
        return False


class ASCIIArt:
    """
    ASCII art manager for rendering banners and decorative elements.
    Supports both Unicode and pure ASCII modes for different terminal capabilities.
    """
    
    def __init__(self, use_unicode: Optional[bool] = None) -> None:
        """
        Initialize ASCII art manager.
        
        Args:
            use_unicode: Whether to use Unicode characters (emoji, etc.)
                        Auto-detected if not specified.
        """
        if use_unicode is None:
            use_unicode = _can_use_unicode()
        self.use_unicode = use_unicode
        self._icons = ICONS if use_unicode else ASCII_ICONS
        self._spinners = SPINNERS if use_unicode else ASCII_SPINNERS
        self._progress = PROGRESS_BARS if use_unicode else ASCII_PROGRESS_BARS
    
    def get_banner(self, size: str = "small") -> str:
        """
        Get the application banner.
        
        Args:
            size: Banner size ('large', 'small', or 'mini')
            
        Returns:
            Banner string
        """
        if size == "large":
            return MAIN_BANNER
        elif size == "mini":
            return MINI_BANNER.format(version=APP_VERSION)
        return SMALL_BANNER
    
    def get_icon(self, name: str, fallback: str = "") -> str:
        """
        Get an icon by name.
        
        Args:
            name: Icon name
            fallback: Fallback string if icon not found
            
        Returns:
            Icon string
        """
        return self._icons.get(name, fallback)
    
    def get_spinner_frames(self) -> list[str]:
        """Get spinner animation frames."""
        return self._spinners.copy()
    
    def progress_bar(self, progress: float, width: int = 20) -> str:
        """
        Create a progress bar string.
        
        Args:
            progress: Progress value (0.0 to 1.0)
            width: Width of the progress bar
            
        Returns:
            Progress bar string
        """
        progress = max(0.0, min(1.0, progress))
        filled = int(width * progress)
        empty = width - filled
        
        return (
            self._progress["filled"] * filled +
            self._progress["empty"] * empty
        )
    
    def box(self, content: str, title: Optional[str] = None, width: int = 40) -> str:
        """
        Create a simple ASCII box around content.
        
        Args:
            content: Content to box
            title: Optional title for the box
            width: Width of the box
            
        Returns:
            Boxed content string
        """
        if self.use_unicode:
            top_left, top_right = "╭", "╮"
            bottom_left, bottom_right = "╰", "╯"
            horizontal, vertical = "─", "│"
        else:
            top_left = top_right = bottom_left = bottom_right = "+"
            horizontal, vertical = "-", "|"
        
        lines = []
        inner_width = width - 2
        
        if title:
            title_display = f" {title} "
            padding = inner_width - len(title_display)
            left_pad = padding // 2
            right_pad = padding - left_pad
            top_line = top_left + horizontal * left_pad + title_display + horizontal * right_pad + top_right
        else:
            top_line = top_left + horizontal * inner_width + top_right
        
        lines.append(top_line)
        
        for line in content.split('\n'):
            if len(line) > inner_width:
                line = line[:inner_width - 3] + "..."
            padded = line.ljust(inner_width)
            lines.append(f"{vertical}{padded}{vertical}")
        
        lines.append(bottom_left + horizontal * inner_width + bottom_right)
        
        return '\n'.join(lines)
    
    def divider(self, width: int = 40, style: str = "single") -> str:
        """
        Create a horizontal divider.
        
        Args:
            width: Width of the divider
            style: Divider style ('single', 'double', 'dashed')
            
        Returns:
            Divider string
        """
        if self.use_unicode:
            chars = {
                "single": "─",
                "double": "═",
                "dashed": "╌",
                "thick": "━",
            }
        else:
            chars = {
                "single": "-",
                "double": "=",
                "dashed": "-",
                "thick": "=",
            }
        
        return chars.get(style, chars["single"]) * width
    
    def render_banner_panel(self, console: Console) -> None:
        """
        Render the banner without bordered panel.
        
        Args:
            console: Rich console to render to
            
        Requirements: 1.5 - Render banner without bordered panel
        """
        banner_text = Text(self.get_banner("small"), style="bold cyan")
        console.print(banner_text)
        console.print(f"[bold white]{APP_NAME}[/bold white] [dim]v{APP_VERSION}[/dim]")
        console.print()  # Add spacing
    
    def status_indicator(self, status: str) -> str:
        """
        Get a status indicator icon.
        
        Args:
            status: Status type ('online', 'offline', 'busy', 'error')
            
        Returns:
            Status indicator string
        """
        indicators = {
            "online": ("🟢", "[O]"),
            "offline": ("⚫", "[_]"),
            "busy": ("🟡", "[~]"),
            "error": ("🔴", "[!]"),
            "connected": ("🔗", "[+]"),
            "disconnected": ("⛓️‍💥", "[-]"),
        }
        
        unicode_icon, ascii_icon = indicators.get(status, ("❓", "[?]"))
        return unicode_icon if self.use_unicode else ascii_icon
    
    def model_badge(self, provider: str, model: str) -> str:
        """
        Create a model badge string.
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            Badge string
        """
        if self.use_unicode:
            return f"🏷️ {provider}/{model}"
        return f"[{provider}/{model}]"
    
    def token_display(self, input_tokens: int, output_tokens: int) -> str:
        """
        Create a token count display.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Token display string
        """
        arrow = "→" if self.use_unicode else "->"
        return f"📊 {input_tokens} {arrow} {output_tokens}" if self.use_unicode else f"[{input_tokens} {arrow} {output_tokens}]"
