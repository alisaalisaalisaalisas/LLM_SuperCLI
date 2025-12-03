"""Responsive splash screen for llm_supercli.

Requirements:
- 10.1: Display ASCII art logo with branding on startup
- 10.2: Use smaller banner variant for narrow terminals
- 10.3: Show startup instructions below banner
"""
from rich.console import Console
from rich.text import Text
from rich.align import Align
import shutil

from ..constants import APP_VERSION
from .theme import get_theme_manager
# Import banners from ascii.py to avoid duplication
from .ascii import MAIN_BANNER as FULL_BANNER, SMALL_BANNER, MINI_BANNER

# Compact threshold for small banner variant (Req 10.2)
COMPACT_WIDTH_THRESHOLD = 80

# Minimal banner for very narrow terminals (< 60 cols)
MINIMAL_BANNER = "SuperCLI"

# Startup instructions shown below banner - Req 10.3
STARTUP_INSTRUCTIONS = """
Type a message to start chatting, or use these commands:
  /help     Show all commands
  /model    Switch model or provider
  /mode     Change interaction mode
  !cmd      Execute shell command
  @file     Include file in prompt
"""

# Compact startup instructions for narrow terminals
COMPACT_INSTRUCTIONS = """
/help for commands  |  /model to switch  |  ! for shell
"""


def get_gradient_color(position: float) -> str:
    """Get a color from a Green -> Yellow -> Red gradient.
    
    Args:
        position: Position in gradient (0.0 to 1.0)
        
    Returns:
        RGB color string
    """
    if position < 0.5:
        # Green to Yellow
        ratio = position * 2
        r = int(255 * ratio)
        g = 255
        b = 0
    else:
        # Yellow to Red
        ratio = (position - 0.5) * 2
        r = 255
        g = int(255 * (1 - ratio))
        b = 0
    
    return f"rgb({r},{g},{b})"


def _get_terminal_width() -> int:
    """Get current terminal width."""
    size = shutil.get_terminal_size(fallback=(80, 24))
    return size.columns


def _render_banner_with_gradient(banner_text: str, width: int) -> Text:
    """Render banner text with gradient coloring.
    
    Args:
        banner_text: ASCII art banner string
        width: Terminal width for centering
        
    Returns:
        Rich Text object with gradient colors
    """
    lines = banner_text.strip().split('\n')
    max_line_width = max(len(line) for line in lines) if lines else 0
    
    result = Text()
    
    for line in lines:
        # Calculate centering padding
        padding = max(0, (width - len(line)) // 2)
        result.append(" " * padding)
        
        # Apply gradient to each character
        for i, char in enumerate(line):
            if char.strip():
                rel_pos = i / max_line_width if max_line_width > 0 else 0
                color = get_gradient_color(rel_pos)
                result.append(char, style=color)
            else:
                result.append(char)
        
        result.append("\n")
    
    return result


def _get_banner_for_width(width: int) -> str:
    """Select appropriate banner based on terminal width.
    
    Requirements: 10.2 - Use smaller banner variant for narrow terminals
    
    Args:
        width: Terminal width in columns
        
    Returns:
        Appropriate banner string
    """
    if width < 60:
        return MINIMAL_BANNER
    elif width < COMPACT_WIDTH_THRESHOLD:
        return SMALL_BANNER
    else:
        return FULL_BANNER


def _get_instructions_for_width(width: int) -> str:
    """Select appropriate instructions based on terminal width.
    
    Requirements: 10.3 - Show startup instructions below banner
    
    Args:
        width: Terminal width in columns
        
    Returns:
        Appropriate instructions string
    """
    if width < COMPACT_WIDTH_THRESHOLD:
        return COMPACT_INSTRUCTIONS
    else:
        return STARTUP_INSTRUCTIONS


def print_splash(console: Console = None) -> None:
    """Print the responsive splash screen.
    
    Requirements:
    - 10.1: Display ASCII art logo with branding
    - 10.2: Use smaller banner variant for narrow terminals
    - 10.3: Show startup instructions below banner
    
    Args:
        console: Optional Rich Console instance
    """
    console = console or Console()
    width = console.width or _get_terminal_width()
    
    # Get theme colors
    theme_manager = get_theme_manager()
    primary_color = theme_manager.get_color("primary") or "#00d7d7"
    success_color = theme_manager.get_color("success") or "#00ff00"
    muted_color = theme_manager.get_color("muted") or "#666666"
    
    # Select appropriate banner for terminal width (Req 10.2)
    banner_text = _get_banner_for_width(width)
    
    # Render banner with gradient
    banner = _render_banner_with_gradient(banner_text, width)
    
    # Version text
    version_text = Text()
    version_text.append("v", style=muted_color)
    version_text.append(APP_VERSION, style=f"bold {primary_color}")
    
    # Print banner
    console.print()
    console.print(banner)
    
    # Print version centered
    console.print(Align.center(version_text))
    console.print()
    
    # Print startup instructions (Req 10.3) - no border, just centered text
    instructions = _get_instructions_for_width(width)
    instructions_text = Text(instructions.strip(), style=muted_color)
    console.print(Align.center(instructions_text))
    
    console.print()


def print_minimal_splash(console: Console = None) -> None:
    """Print a minimal splash for very constrained environments.
    
    Args:
        console: Optional Rich Console instance
    """
    console = console or Console()
    
    theme_manager = get_theme_manager()
    primary_color = theme_manager.get_color("primary") or "#00d7d7"
    muted_color = theme_manager.get_color("muted") or "#666666"
    
    # Simple one-line header
    header = Text()
    header.append("LLM SuperCLI ", style=f"bold {primary_color}")
    header.append(f"v{APP_VERSION}", style=muted_color)
    header.append(" | ", style=muted_color)
    header.append("/help", style=primary_color)
    header.append(" for commands", style=muted_color)
    
    console.print()
    console.print(Align.center(header))
    console.print()
