"""Cyberpunk neon splash screen for llm_supercli."""
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from ..constants import APP_VERSION

NEON_LOGO = """
██╗     ██╗     ███╗   ███╗███████╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗     ██╗
██║     ██║     ████╗ ████║██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██║
██║     ██║     ██╔████╔██║███████╗██║   ██║██████╔╝█████╗  ██████╔╝██║     ██║     ██║
██║     ██║     ██║╚██╔╝██║╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██║
███████╗███████╗██║ ╚═╝ ██║███████║╚██████╔╝██║     ███████╗██║  ██║╚██████╗███████╗██║
╚══════╝╚══════╝╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝
"""

NEON_LOGO_SMALL = """
███████╗██╗   ██╗██████╗ ███████╗██████╗  ██████╗██╗     ██╗
██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██║
███████╗██║   ██║██████╔╝█████╗  ██████╔╝██║     ██║     ██║
╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗██║     ██║     ██║
███████║╚██████╔╝██║     ███████╗██║  ██║╚██████╗███████╗██║
╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝
"""

# Cyberpunk border characters
TL = "╭"  # top-left
TR = "╮"  # top-right  
BL = "╰"  # bottom-left
BR = "╯"  # bottom-right
H = "─"   # horizontal
V = "│"   # vertical
CIRCUIT_TL = "┌──┐"
CIRCUIT_TR = "┌──┐"
CIRCUIT_BL = "└──┘"
CIRCUIT_BR = "└──┘"


def print_splash(console: Console = None) -> None:
    """Print the cyberpunk neon splash screen."""
    console = console or Console()
    width = console.width or 90
    
    # Adjust for terminal width
    if width < 95:
        logo = NEON_LOGO_SMALL
        inner_width = 65
    else:
        logo = NEON_LOGO
        inner_width = 87
    
    frame_width = inner_width + 4
    
    # Build the frame
    lines = []
    
    # Top border with circuit corners
    top = f"[green]╭─┬{'─' * (frame_width - 6)}┬─╮[/green]"
    lines.append(top)
    lines.append(f"[green]│ │{' ' * (frame_width - 6)}│ │[/green]")
    lines.append(f"[green]├─╯{' ' * (frame_width - 6)}╰─┤[/green]")
    
    # Logo lines with neon gradient effect
    logo_lines = logo.strip().split('\n')
    for i, line in enumerate(logo_lines):
        # Create gradient: green -> yellow -> red
        if i < 2:
            style = "bold green"
        elif i < 4:
            style = "bold yellow"
        else:
            style = "bold red"
        
        padded = line.center(frame_width - 4)
        lines.append(f"[green]│[/green] [{style}]{padded}[/{style}] [green]│[/green]")
    
    # Empty line before version
    lines.append(f"[green]│{' ' * (frame_width - 2)}│[/green]")
    
    # Version line (right-aligned)
    version_str = f"v{APP_VERSION}"
    version_line = f"{' ' * (frame_width - len(version_str) - 4)}{version_str}"
    lines.append(f"[green]│[/green] [dim cyan]{version_line}[/dim cyan] [green]│[/green]")
    
    # Bottom border with circuit corners
    lines.append(f"[green]├─╮{' ' * (frame_width - 6)}╭─┤[/green]")
    lines.append(f"[green]│ │{' ' * (frame_width - 6)}│ │[/green]")
    lines.append(f"[green]╰─┴{'─' * (frame_width - 6)}┴─╯[/green]")
    
    # Print with dark background effect
    console.print()
    for line in lines:
        console.print(line)
    console.print()
