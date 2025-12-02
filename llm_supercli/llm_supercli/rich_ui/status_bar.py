"""
Status Bar component for llm_supercli Rich UI.
Provides a fixed footer showing session, mode, provider, and context info.

Requirements: 1.1, 1.2, 1.3, 1.4 - Fixed Status Bar Layout
Requirements: 9.2 - Compact mode for narrow terminals
"""
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .theme import get_theme_manager

if TYPE_CHECKING:
    from .layout_manager import LayoutManager


@dataclass
class StatusBarData:
    """Data model for status bar content.
    
    Requirements: 1.1 - Status bar showing session/branch, mode, provider:model, context
    """
    session_name: str = "new"
    branch: str = "main"
    mode_icon: str = "💻"
    mode_name: str = "Code"
    provider: str = "groq"
    model: str = "llama-3.3-70b"
    is_free: bool = False
    context_percent: int = 0


class StatusBar:
    """
    Fixed footer component showing session info.
    
    Display format:
    ┌────────────────────────────────────────────────────────────────┐
    │ new / main                    Code │ MiniMax: M2 (free) │ 18% │
    └────────────────────────────────────────────────────────────────┘
    
    Requirements:
    - 1.1: Display status bar fixed at terminal bottom
    - 1.2: Adapt width to match terminal width
    - 1.3: Immediately update when provider or mode changes
    - 1.4: Update context percentage in real-time
    """
    
    def __init__(self, console: Optional[Console] = None, layout_manager: Optional['LayoutManager'] = None) -> None:
        """
        Initialize the StatusBar.
        
        Args:
            console: Optional Rich Console instance
            layout_manager: Optional LayoutManager for responsive behavior
        """
        self._console = console or Console(force_terminal=True, color_system="auto")
        self._theme = get_theme_manager()
        self._data = StatusBarData()
        self._width: Optional[int] = None
        self._layout_manager = layout_manager
        self._compact_mode: bool = False
    
    def set_layout_manager(self, layout_manager: 'LayoutManager') -> None:
        """Set the layout manager for responsive behavior."""
        self._layout_manager = layout_manager
    
    def _is_compact_mode(self) -> bool:
        """Check if we should use compact mode.
        
        Requirements: 9.2 - Compact mode for narrow terminals
        """
        if self._layout_manager:
            return self._layout_manager.is_compact_mode
        # Fallback: check width directly
        width = self._width or self._console.width or 80
        return width < 80
    
    @property
    def data(self) -> StatusBarData:
        """Get current status bar data."""
        return self._data
    
    def update(
        self,
        session_name: Optional[str] = None,
        branch: Optional[str] = None,
        mode_icon: Optional[str] = None,
        mode_name: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        is_free: Optional[bool] = None,
        context_percent: Optional[int] = None
    ) -> None:
        """
        Update status bar data.
        
        Requirements: 1.3, 1.4 - Real-time updates
        
        Args:
            session_name: Session name to display
            branch: Git branch name
            mode_icon: Icon for current mode
            mode_name: Name of current mode
            provider: LLM provider name
            model: Model name
            is_free: Whether using free tier
            context_percent: Context usage percentage
        """
        if session_name is not None:
            self._data.session_name = session_name
        if branch is not None:
            self._data.branch = branch
        if mode_icon is not None:
            self._data.mode_icon = mode_icon
        if mode_name is not None:
            self._data.mode_name = mode_name
        if provider is not None:
            self._data.provider = provider
        if model is not None:
            self._data.model = model
        if is_free is not None:
            self._data.is_free = is_free
        if context_percent is not None:
            self._data.context_percent = context_percent
    
    def set_width(self, width: int) -> None:
        """
        Set the status bar width.
        
        Requirements: 1.2 - Adapt width to terminal
        
        Args:
            width: Width in columns
        """
        self._width = width
    
    def render(self, width: Optional[int] = None) -> RenderableType:
        """
        Render the status bar.
        
        Requirements: 1.1, 1.2 - Render fixed status bar with proper width
        
        Args:
            width: Optional width override
            
        Returns:
            Renderable status bar
        """
        effective_width = width or self._width or self._console.width
        
        # Build status bar content
        content = self._build_content(effective_width)
        
        return content
    
    def _build_content(self, width: int) -> Text:
        """
        Build the status bar content as styled text.
        
        Args:
            width: Available width
            
        Returns:
            Styled Text object
        """
        # Check if we should use compact mode
        if self._is_compact_mode():
            return self._build_compact_content(width)
        
        # Get theme colors
        primary_color = self._theme.get_color("primary")
        success_color = self._theme.get_color("success")
        muted_color = self._theme.get_color("muted")
        
        # Build left section: session / branch
        left_section = Text()
        left_section.append(f"{self._data.session_name}", style="bold")
        left_section.append(" / ", style=muted_color)
        left_section.append(f"{self._data.branch}", style=muted_color)
        
        # Build center section: mode
        center_section = Text()
        center_section.append(f"{self._data.mode_icon} ", style="")
        center_section.append(f"{self._data.mode_name}", style="bold")
        
        # Build right section: provider:model (free) | context%
        right_section = Text()
        right_section.append(f"{self._data.provider.title()}", style=f"bold {primary_color}")
        right_section.append(": ", style=muted_color)
        right_section.append(f"{self._data.model}", style=primary_color)
        
        if self._data.is_free:
            right_section.append(" (free)", style=success_color)
        
        right_section.append(" │ ", style=muted_color)
        
        # Color context percentage based on usage
        context_style = self._get_context_style()
        right_section.append(f"{self._data.context_percent}%", style=context_style)
        
        # Calculate spacing
        left_len = len(left_section.plain)
        center_len = len(center_section.plain)
        right_len = len(right_section.plain)
        
        # Available space for padding (account for borders and padding)
        available = width - 4  # 2 for borders, 2 for padding
        total_content = left_len + center_len + right_len
        
        if total_content >= available:
            # Content doesn't fit: use compact mode
            return self._build_compact_content(width)
        
        # Calculate padding to distribute content
        remaining = available - total_content
        left_pad = remaining // 3
        right_pad = remaining - left_pad
        
        # Build final text
        result = Text()
        result.append_text(left_section)
        result.append(" " * left_pad)
        result.append_text(center_section)
        result.append(" " * right_pad)
        result.append_text(right_section)
        
        return result
    
    def _build_compact_content(self, width: int) -> Text:
        """
        Build compact status bar for narrow terminals.
        
        Requirements: 1.2 - Adapt to terminal width
        
        Args:
            width: Available width
            
        Returns:
            Compact styled Text
        """
        primary_color = self._theme.get_color("primary")
        muted_color = self._theme.get_color("muted")
        
        result = Text()
        
        # Abbreviated content
        result.append(f"{self._data.mode_icon}", style="")
        result.append(" │ ", style=muted_color)
        result.append(f"{self._data.provider[:4]}", style=f"bold {primary_color}")
        result.append(" │ ", style=muted_color)
        
        context_style = self._get_context_style()
        result.append(f"{self._data.context_percent}%", style=context_style)
        
        return result
    
    def _get_context_style(self) -> str:
        """
        Get style for context percentage based on usage level.
        
        Returns:
            Style string for context display
        """
        percent = self._data.context_percent
        
        if percent >= 90:
            return "bold red"
        elif percent >= 70:
            return "bold yellow"
        elif percent >= 50:
            return "yellow"
        else:
            return "green"
    
    def render_panel(self, width: Optional[int] = None) -> Panel:
        """
        Render the status bar as a bordered panel.
        
        Args:
            width: Optional width override
            
        Returns:
            Panel containing status bar
        """
        effective_width = width or self._width or self._console.width
        content = self._build_content(effective_width - 4)  # Account for panel borders
        
        return Panel(
            content,
            border_style="dim",
            padding=(0, 1),
            height=3
        )
    
    def print(self, width: Optional[int] = None) -> None:
        """
        Print the status bar to console.
        
        Args:
            width: Optional width override
        """
        self._console.print(self.render(width))


# Global instance
_status_bar: Optional[StatusBar] = None


def get_status_bar(console: Optional[Console] = None) -> StatusBar:
    """
    Get the global StatusBar instance.
    
    Args:
        console: Optional console to use (only used on first call)
        
    Returns:
        Global StatusBar instance
    """
    global _status_bar
    if _status_bar is None:
        _status_bar = StatusBar(console=console)
    return _status_bar
