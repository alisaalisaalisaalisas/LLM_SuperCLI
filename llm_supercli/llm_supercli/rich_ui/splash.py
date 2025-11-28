"""Cyberpunk neon splash screen for llm_supercli."""
from rich.console import Console
from rich.text import Text
from rich.style import Style
from rich.color import Color
import pyfiglet
from ..constants import APP_VERSION

# Cyberpunk border characters
TL = "╭"  # top-left
TR = "╮"  # top-right  
BL = "╰"  # bottom-left
BR = "╯"  # bottom-right
H = "─"   # horizontal
V = "│"   # vertical

def get_gradient_color(position: float) -> str:
    """
    Get a color from a Green -> Yellow -> Red gradient based on position (0.0 to 1.0).
    """
    # Green: #00FF00 (0, 255, 0)
    # Yellow: #FFFF00 (255, 255, 0)
    # Red: #FF0000 (255, 0, 0)
    
    if position < 0.5:
        # Green to Yellow
        # R: 0 -> 255, G: 255 -> 255, B: 0
        ratio = position * 2
        r = int(0 + (255 - 0) * ratio)
        g = 255
        b = 0
    else:
        # Yellow to Red
        # R: 255, G: 255 -> 0, B: 0
        ratio = (position - 0.5) * 2
        r = 255
        g = int(255 + (0 - 255) * ratio)
        b = 0
        
    return f"rgb({r},{g},{b})"

def print_splash(console: Console = None) -> None:
    """Print the cyberpunk neon splash screen."""
    console = console or Console()
    width = console.width or 90
    
    # Generate Logo - force single line by using large width
    try:
        f = pyfiglet.Figlet(font='ansi_shadow', width=500)
    except:
        f = pyfiglet.Figlet(width=500) # Fallback
        
    if width < 95:
        logo_text = f.renderText('SuperCLI')
    else:
        logo_text = f.renderText('LLMSuperCLI')
        
    logo_lines = logo_text.split('\n')
    # Remove empty first/last lines if any
    if logo_lines and not logo_lines[0].strip(): 
        logo_lines.pop(0)
    if logo_lines and not logo_lines[-1].strip(): 
        logo_lines.pop()
    
    max_line_width = max(len(line) for line in logo_lines) if logo_lines else 0
    frame_width = max_line_width + 8
    
    # Build the frame
    lines = []
    
    # Top border with circuit corners - BRIGHT NEON GREEN
    neon_green = "bright_green"
    top = f"[{neon_green}]╭─┬{'─' * (frame_width - 6)}┬─╮[/{neon_green}]"
    lines.append(Text.from_markup(top))
    lines.append(Text.from_markup(f"[{neon_green}]│ │{' ' * (frame_width - 6)}│ │[/{neon_green}]"))
    lines.append(Text.from_markup(f"[{neon_green}]├─╯{' ' * (frame_width - 6)}╰─┤[/{neon_green}]"))
    
    # Render Logo with Gradient
    for line in logo_lines:
        text = Text()
        # Left padding/border
        text.append("│ ", style=neon_green)
        
        # Centering padding
        padding_len = (frame_width - 4 - len(line)) // 2
        text.append(" " * padding_len)
        
        # Gradient text
        for i, char in enumerate(line):
            if char.strip():
                # Calculate relative position in the full logo width for gradient
                # We use max_line_width to ensure consistent gradient across lines
                rel_pos = i / max_line_width if max_line_width > 0 else 0
                color = get_gradient_color(rel_pos)
                text.append(char, style=color)
            else:
                text.append(char)
                
        # Right padding
        right_padding = frame_width - 4 - len(line) - padding_len
        text.append(" " * right_padding)
        
        # Right border
        text.append(" │", style=neon_green)
        lines.append(text)
    
    # Empty lines before version
    for _ in range(2):
        lines.append(Text.from_markup(f"[{neon_green}]│{' ' * (frame_width - 2)}│[/{neon_green}]"))
    
    # Version line with red circle (right-aligned)
    version_text = Text()
    version_text.append("│ ", style=neon_green)
    version_str = f"v{APP_VERSION}"
    
    # Calculate padding to right-align the version circle
    # Format: "│ <spaces> ( v1.0.0 ) │"
    # frame_width accounts for both borders (│), so inner width is frame_width - 2
    circle_content = f"( {version_str} )"
    inner_width = frame_width - 2  # subtract both border characters
    padding_before_circle = inner_width - len(circle_content) -2  # -2 for final space before right border
    version_text.append(" " * padding_before_circle)
    
    # Red circle around version
    version_text.append("( ", style="bold red")
    version_text.append(version_str, style="bold red")
    version_text.append(" )", style="bold red")
    version_text.append(" ", style="")
    version_text.append("│", style=neon_green)
    lines.append(version_text)
    
    # Bottom border with circuit corners
    lines.append(Text.from_markup(f"[{neon_green}]├─╮{' ' * (frame_width - 6)}╭─┤[/{neon_green}]"))
    lines.append(Text.from_markup(f"[{neon_green}]│ │{' ' * (frame_width - 6)}│ │[/{neon_green}]"))
    lines.append(Text.from_markup(f"[{neon_green}]╰─┴{'─' * (frame_width - 6)}┴─╯[/{neon_green}]"))
    
    # Print with dark background effect
    console.print()
    for line in lines:
        console.print(line)
    console.print()
