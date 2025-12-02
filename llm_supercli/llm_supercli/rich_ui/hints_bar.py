"""
Hints Bar component for llm_supercli Rich UI.
Displays quick reference hints for available command prefixes.

Requirements: 3.1, 3.2 - Help Hints Bar
"""
from dataclasses import dataclass, field
from typing import List, Optional

from rich.console import Console, RenderableType
from rich.text import Text

from .theme import get_theme_manager


@dataclass
class HintItem:
    """A single hint item with command and description."""
    command: str
    description: str
    priority: int = 0  # Higher priority items shown first when truncating


@dataclass
class HintsBarConfig:
    """Configuration for hints bar display."""
    separator: str = "  "
    min_width_for_hints: int = 40
    truncate_at_width: int = 60


class HintsBar:
    """
    Help hints bar component showing quick reference for commands.
    
    Display format:
    /help for commands  /mode to switch mode  ! for shell mode
    
    Requirements:
    - 3.1: Display hints bar showing command prefixes
    - 3.2: Truncate or hide hints for narrow terminals
    """
    
    # Default hints to display
    DEFAULT_HINTS: List[HintItem] = [
        HintItem("/help", "for commands", priority=3),
        HintItem("/mode", "to switch mode", priority=2),
        HintItem("!", "for shell mode", priority=1),
    ]
    
    def __init__(
        self,
        console: Optional[Console] = None,
        config: Optional[HintsBarConfig] = None
    ) -> None:
        """
        Initialize the HintsBar.
        
        Args:
            console: Optional Rich Console instance
            config: Optional configuration
        """
        self._console = console or Console(force_terminal=True, color_system="auto")
        self._config = config or HintsBarConfig()
        self._theme = get_theme_manager()
        self._hints: List[HintItem] = list(self.DEFAULT_HINTS)
        self._width: Optional[int] = None
        self._visible: bool = True

    @property
    def hints(self) -> List[HintItem]:
        """Get the current hints list."""
        return self._hints
    
    @property
    def visible(self) -> bool:
        """Check if hints bar is visible."""
        return self._visible
    
    @visible.setter
    def visible(self, value: bool) -> None:
        """Set hints bar visibility."""
        self._visible = value
    
    def set_hints(self, hints: List[HintItem]) -> None:
        """
        Set custom hints to display.
        
        Args:
            hints: List of HintItem objects
        """
        self._hints = hints
    
    def add_hint(self, command: str, description: str, priority: int = 0) -> None:
        """
        Add a hint to the display.
        
        Args:
            command: Command prefix (e.g., "/help")
            description: Description text
            priority: Priority for truncation (higher = shown first)
        """
        self._hints.append(HintItem(command, description, priority))
        # Sort by priority descending
        self._hints.sort(key=lambda h: h.priority, reverse=True)
    
    def clear_hints(self) -> None:
        """Clear all hints."""
        self._hints.clear()
    
    def reset_hints(self) -> None:
        """Reset to default hints."""
        self._hints = list(self.DEFAULT_HINTS)
    
    def set_width(self, width: int) -> None:
        """
        Set the hints bar width.
        
        Args:
            width: Width in columns
        """
        self._width = width
    
    def _get_hints_for_width(self, width: int) -> List[HintItem]:
        """
        Get hints that fit within the given width.
        
        Requirements: 3.2 - Truncate hints for narrow terminals
        
        Args:
            width: Available width in columns
            
        Returns:
            List of hints that fit
        """
        if width < self._config.min_width_for_hints:
            return []
        
        # Sort by priority (highest first)
        sorted_hints = sorted(self._hints, key=lambda h: h.priority, reverse=True)
        
        result = []
        current_width = 0
        separator_len = len(self._config.separator)
        
        for hint in sorted_hints:
            # Calculate hint width: "command description"
            hint_text = f"{hint.command} {hint.description}"
            hint_width = len(hint_text)
            
            # Add separator width if not first item
            if result:
                hint_width += separator_len
            
            # Check if it fits
            if current_width + hint_width <= width:
                result.append(hint)
                current_width += hint_width
            elif width < self._config.truncate_at_width:
                # For narrow terminals, stop adding hints
                break
        
        return result
    
    def render(self, width: Optional[int] = None) -> RenderableType:
        """
        Render the hints bar.
        
        Requirements: 3.1, 3.2 - Render hints with responsive truncation
        
        Args:
            width: Optional width override
            
        Returns:
            Renderable hints bar
        """
        if not self._visible:
            return Text("")
        
        effective_width = width or self._width or self._console.width
        
        # Get hints that fit
        hints_to_show = self._get_hints_for_width(effective_width)
        
        if not hints_to_show:
            return Text("")
        
        # Build styled text
        return self._build_content(hints_to_show)
    
    def _build_content(self, hints: List[HintItem]) -> Text:
        """
        Build the hints bar content as styled text.
        
        Args:
            hints: List of hints to display
            
        Returns:
            Styled Text object
        """
        # Get theme colors
        muted_color = self._theme.get_color("muted") or "dim"
        primary_color = self._theme.get_color("primary") or "cyan"
        
        result = Text()
        
        for i, hint in enumerate(hints):
            # Add separator between hints
            if i > 0:
                result.append(self._config.separator, style=muted_color)
            
            # Command in primary color
            result.append(hint.command, style=f"bold {primary_color}")
            result.append(" ", style="")
            # Description in muted color
            result.append(hint.description, style=muted_color)
        
        return result
    
    def render_centered(self, width: Optional[int] = None) -> Text:
        """
        Render the hints bar centered within the given width.
        
        Args:
            width: Optional width override
            
        Returns:
            Centered Text object
        """
        content = self.render(width)
        
        if not isinstance(content, Text) or not content.plain:
            return Text("")
        
        effective_width = width or self._width or self._console.width
        content_len = len(content.plain)
        
        if content_len >= effective_width:
            return content
        
        # Calculate padding for centering
        padding = (effective_width - content_len) // 2
        
        result = Text()
        result.append(" " * padding)
        result.append_text(content)
        
        return result
    
    def print(self, width: Optional[int] = None, centered: bool = False) -> None:
        """
        Print the hints bar to console.
        
        Args:
            width: Optional width override
            centered: Whether to center the hints
        """
        if centered:
            self._console.print(self.render_centered(width))
        else:
            self._console.print(self.render(width))


# Global instance
_hints_bar: Optional[HintsBar] = None


def get_hints_bar(console: Optional[Console] = None) -> HintsBar:
    """
    Get the global HintsBar instance.
    
    Args:
        console: Optional console to use (only used on first call)
        
    Returns:
        Global HintsBar instance
    """
    global _hints_bar
    if _hints_bar is None:
        _hints_bar = HintsBar(console=console)
    return _hints_bar
