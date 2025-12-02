"""
Layout Manager for llm_supercli Rich UI.
Coordinates fixed terminal layout with three regions: header, content, footer.

Requirements: 9.1, 9.2, 9.3 - Terminal responsiveness and layout management
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
import shutil

from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text


@dataclass
class LayoutConfig:
    """Configuration for layout dimensions and thresholds.
    
    Requirements: 9.2, 9.3 - Responsive layout configuration
    """
    min_width: int = 60
    max_width: int = 160
    compact_threshold: int = 80
    wide_threshold: int = 120  # Threshold for centering content
    status_bar_height: int = 1
    hints_bar_height: int = 1
    input_panel_height: int = 3
    header_height: int = 0  # 0 when banner hidden
    footer_total_height: int = 5  # status + hints + input
    # Padding settings
    normal_padding: tuple = (0, 1)  # (vertical, horizontal) for normal mode
    compact_padding: tuple = (0, 0)  # (vertical, horizontal) for compact mode
    # Text truncation settings
    compact_max_text_length: int = 60  # Max text length in compact mode


@dataclass
class LayoutRegion:
    """Represents a layout region with content and visibility."""
    name: str
    content: Optional[RenderableType] = None
    visible: bool = True
    height: Optional[int] = None


class LayoutManager:
    """
    Coordinates the fixed terminal layout with three regions.
    
    Regions:
    - Header Region: Banner on startup, then hidden
    - Content Region: Scrollable message/panel area
    - Footer Region: Fixed status bar + hints + input
    
    Requirements:
    - 9.1: Reflow panel content when terminal width changes
    - 9.2: Use compact layout mode for narrow terminals (< 80 cols)
    - 9.3: Center content with max-width constraint for wide terminals (> 120 cols)
    """
    
    def __init__(
        self,
        console: Optional[Console] = None,
        config: Optional[LayoutConfig] = None
    ) -> None:
        """
        Initialize the LayoutManager.
        
        Args:
            console: Optional Rich Console instance
            config: Optional layout configuration
        """
        self._console = console or Console(force_terminal=True, color_system="auto")
        self._config = config or LayoutConfig()
        
        # Layout regions
        self._header = LayoutRegion(name="header", visible=False)
        self._content = LayoutRegion(name="content", visible=True)
        self._footer = LayoutRegion(name="footer", visible=True)
        
        # Cached terminal dimensions
        self._terminal_width: int = 0
        self._terminal_height: int = 0
        self._update_terminal_size()
        
        # Layout mode
        self._compact_mode: bool = False
        self._update_layout_mode()
    
    @property
    def console(self) -> Console:
        """Get the Rich console."""
        return self._console
    
    @property
    def config(self) -> LayoutConfig:
        """Get the layout configuration."""
        return self._config
    
    @property
    def terminal_width(self) -> int:
        """Get current terminal width."""
        self._update_terminal_size()
        return self._terminal_width
    
    @property
    def terminal_height(self) -> int:
        """Get current terminal height."""
        self._update_terminal_size()
        return self._terminal_height
    
    @property
    def is_compact_mode(self) -> bool:
        """Check if layout is in compact mode.
        
        Requirements: 9.2 - Compact mode for narrow terminals
        """
        self._update_layout_mode()
        return self._compact_mode
    
    @property
    def content_width(self) -> int:
        """Get the effective content width.
        
        Requirements: 
        - 9.1: Content width adapts to terminal
        - 9.3: Max-width constraint for wide terminals
        """
        self._update_terminal_size()
        width = self._terminal_width
        
        # Apply max-width constraint for wide terminals
        if width > self._config.max_width:
            return self._config.max_width
        
        # Ensure minimum width
        if width < self._config.min_width:
            return self._config.min_width
        
        return width
    
    def _update_terminal_size(self) -> None:
        """Update cached terminal dimensions."""
        size = shutil.get_terminal_size(fallback=(80, 24))
        self._terminal_width = size.columns
        self._terminal_height = size.lines
    
    def _update_layout_mode(self) -> None:
        """Update layout mode based on terminal width.
        
        Requirements: 9.2 - Compact mode for narrow terminals (< 80 cols)
        """
        self._update_terminal_size()
        self._compact_mode = self._terminal_width < self._config.compact_threshold
    
    def get_content_height(self) -> int:
        """Get available height for content region.
        
        Returns:
            Available height in lines for content
        """
        self._update_terminal_size()
        
        # Calculate footer height
        footer_height = self._config.footer_total_height
        
        # Calculate header height (0 if hidden)
        header_height = self._config.header_height if self._header.visible else 0
        
        # Content gets remaining space
        content_height = self._terminal_height - footer_height - header_height
        
        return max(content_height, 1)
    
    def get_panel_width(self) -> int:
        """Get width for panels, respecting max-width constraint.
        
        Requirements: 9.1, 9.3 - Panel width adaptation
        
        Returns:
            Width in columns for panels
        """
        width = self.content_width
        
        # In compact mode, use full width minus minimal padding
        if self._compact_mode:
            return max(width - 2, self._config.min_width - 2)
        
        # Normal mode: use content width minus padding
        return width - 4
    
    def get_horizontal_padding(self) -> int:
        """Get horizontal padding for centering content.
        
        Requirements: 9.3 - Center content with max-width constraint
        
        Returns:
            Padding in columns for each side
        """
        self._update_terminal_size()
        
        if self._terminal_width <= self._config.wide_threshold:
            return 0
        
        # Center content by adding padding for wide terminals
        effective_max = min(self._config.max_width, self._terminal_width)
        total_padding = self._terminal_width - effective_max
        return total_padding // 2
    
    def get_panel_padding(self) -> tuple:
        """Get padding tuple for panels based on layout mode.
        
        Requirements: 9.2 - Reduce padding in compact mode
        
        Returns:
            Tuple of (vertical, horizontal) padding
        """
        if self._compact_mode:
            return self._config.compact_padding
        return self._config.normal_padding
    
    def truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Truncate text for compact mode display.
        
        Requirements: 9.2 - Truncate long text in compact mode
        
        Args:
            text: Text to potentially truncate
            max_length: Optional max length override
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if not self._compact_mode:
            return text
        
        limit = max_length or self._config.compact_max_text_length
        if len(text) <= limit:
            return text
        
        return text[:limit - 3] + "..."
    
    def should_show_element(self, element_name: str) -> bool:
        """Check if an optional element should be shown based on layout mode.
        
        Requirements: 9.2 - Hide non-essential elements in compact mode
        
        Args:
            element_name: Name of the element to check
            
        Returns:
            True if element should be shown
        """
        # Elements that are hidden in compact mode
        compact_hidden = {"hints_bar", "banner_subtitle", "extended_status"}
        
        if self._compact_mode and element_name in compact_hidden:
            return False
        return True
    
    def set_header_visible(self, visible: bool) -> None:
        """Set header region visibility.
        
        Args:
            visible: Whether header should be visible
        """
        self._header.visible = visible
        self._config.header_height = 8 if visible else 0
    
    def set_header_content(self, content: RenderableType) -> None:
        """Set header region content.
        
        Args:
            content: Renderable content for header
        """
        self._header.content = content
    
    def set_footer_content(self, content: RenderableType) -> None:
        """Set footer region content.
        
        Args:
            content: Renderable content for footer
        """
        self._footer.content = content
    
    def render_layout(self) -> None:
        """Render the complete layout to console.
        
        This renders header (if visible), then allows content to flow,
        with footer rendered at the bottom.
        """
        # Render header if visible
        if self._header.visible and self._header.content:
            self._render_centered(self._header.content)
    
    def render_content(self, content: RenderableType) -> None:
        """Render content in the content region.
        
        Args:
            content: Renderable content to display
        """
        self._render_centered(content)
    
    def render_footer(self) -> None:
        """Render the footer region."""
        if self._footer.content:
            self._render_centered(self._footer.content)
    
    def _render_centered(self, content: RenderableType) -> None:
        """Render content with centering for wide terminals.
        
        Requirements: 9.3 - Center content with max-width constraint
        
        Args:
            content: Renderable content to display
        """
        padding = self.get_horizontal_padding()
        
        if padding > 0:
            # Add horizontal padding for centering
            self._console.print(" " * padding, end="")
        
        self._console.print(content)
    
    def wrap_for_width(self, content: RenderableType) -> RenderableType:
        """Wrap content to respect max-width constraint for wide terminals.
        
        Requirements: 9.3 - Center content with max-width constraint
        
        For wide terminals (> 120 cols), this wraps content in a container
        that centers it with appropriate padding.
        
        Args:
            content: Content to potentially wrap
            
        Returns:
            Original content or wrapped content for centering
        """
        if not self.is_wide_terminal():
            return content
        
        # For wide terminals, we need to constrain width
        # The content will be rendered with horizontal padding
        from rich.padding import Padding
        
        padding = self.get_horizontal_padding()
        if padding > 0:
            return Padding(content, (0, padding, 0, padding))
        
        return content
    
    def get_effective_width(self) -> int:
        """Get the effective content width considering all constraints.
        
        Requirements: 9.2, 9.3 - Responsive width calculation
        
        Returns:
            Effective width for content rendering
        """
        self._update_terminal_size()
        
        # For wide terminals, use max_width
        if self._terminal_width > self._config.wide_threshold:
            return min(self._config.max_width, self._terminal_width)
        
        # For compact mode, use full width minus minimal margins
        if self._compact_mode:
            return max(self._terminal_width - 2, self._config.min_width)
        
        # Normal mode: use terminal width minus standard margins
        return self._terminal_width - 4
    
    def create_panel(
        self,
        content: RenderableType,
        title: Optional[str] = None,
        border_style: str = "dim",
        padding: Optional[tuple] = None,
        truncate_title: bool = True
    ) -> Panel:
        """Create a panel that respects layout width constraints.
        
        Requirements: 9.1, 9.2 - Panel width adaptation and compact mode
        
        Args:
            content: Panel content
            title: Optional panel title
            border_style: Border style
            padding: Panel padding (vertical, horizontal), uses layout default if None
            truncate_title: Whether to truncate title in compact mode
            
        Returns:
            Panel with appropriate width
        """
        # Use layout-appropriate padding if not specified
        if padding is None:
            padding = self.get_panel_padding()
        elif self._compact_mode:
            # Override to compact padding in compact mode
            padding = self._config.compact_padding
        
        # Truncate title in compact mode if requested
        effective_title = title
        if title and truncate_title and self._compact_mode:
            # Truncate title to fit narrow terminal
            max_title_len = max(20, self._terminal_width - 10)
            if len(title) > max_title_len:
                effective_title = title[:max_title_len - 3] + "..."
        
        # Determine panel width
        panel_width = None
        if self._terminal_width > self._config.wide_threshold:
            # Wide terminal: constrain to max width
            panel_width = self.get_panel_width()
        
        panel = Panel(
            content,
            title=effective_title,
            title_align="left",
            border_style=border_style,
            padding=padding,
            width=panel_width
        )
        
        return panel
    
    def get_layout_info(self) -> dict:
        """Get current layout information for debugging.
        
        Returns:
            Dictionary with layout state information
        """
        return {
            "terminal_width": self._terminal_width,
            "terminal_height": self._terminal_height,
            "content_width": self.content_width,
            "content_height": self.get_content_height(),
            "panel_width": self.get_panel_width(),
            "compact_mode": self._compact_mode,
            "wide_mode": self._terminal_width > self._config.wide_threshold,
            "header_visible": self._header.visible,
            "horizontal_padding": self.get_horizontal_padding(),
            "panel_padding": self.get_panel_padding(),
            "scroll_region_height": self.get_scroll_region_height(),
        }
    
    def is_wide_terminal(self) -> bool:
        """Check if terminal is in wide mode (> 120 cols).
        
        Requirements: 9.3 - Wide terminal detection
        
        Returns:
            True if terminal width exceeds wide threshold
        """
        self._update_terminal_size()
        return self._terminal_width > self._config.wide_threshold
    
    def get_scroll_region_height(self) -> int:
        """Get the height of the scrollable content region.
        
        Requirements: 9.4 - Scroll behavior for long content
        
        The scroll region is the area between the header and footer
        where content can scroll while keeping the footer fixed.
        
        Returns:
            Height in lines for the scroll region
        """
        self._update_terminal_size()
        
        # Total height minus footer
        footer_height = self._config.footer_total_height
        header_height = self._config.header_height if self._header.visible else 0
        
        return max(1, self._terminal_height - footer_height - header_height)
    
    def setup_scroll_region(self) -> None:
        """Set up terminal scroll region to keep footer fixed.
        
        Requirements: 9.4 - Ensure footer stays fixed during scroll
        
        This uses ANSI escape sequences to define a scroll region
        that excludes the footer area, allowing content to scroll
        while the footer remains in place.
        """
        import sys
        
        self._update_terminal_size()
        
        # Calculate scroll region bounds
        scroll_top = 1  # 1-indexed
        scroll_bottom = self._terminal_height - self._config.footer_total_height
        
        if scroll_bottom <= scroll_top:
            return  # Terminal too small for scroll region
        
        # ANSI escape sequence to set scroll region: ESC[top;bottomr
        # This tells the terminal to only scroll content within this region
        scroll_region_cmd = f"\033[{scroll_top};{scroll_bottom}r"
        
        # Move cursor to top of scroll region
        move_cursor_cmd = f"\033[{scroll_top};1H"
        
        sys.stdout.write(scroll_region_cmd + move_cursor_cmd)
        sys.stdout.flush()
    
    def reset_scroll_region(self) -> None:
        """Reset terminal scroll region to full terminal.
        
        Requirements: 9.4 - Clean up scroll region on exit
        
        This should be called when exiting the application to restore
        normal terminal behavior.
        """
        import sys
        
        # Reset scroll region to full terminal: ESC[r
        sys.stdout.write("\033[r")
        sys.stdout.flush()
    
    def content_fits_in_viewport(self, content_lines: int) -> bool:
        """Check if content fits within the scroll region without scrolling.
        
        Requirements: 9.4 - Scroll behavior management
        
        Args:
            content_lines: Number of lines in the content
            
        Returns:
            True if content fits without scrolling
        """
        return content_lines <= self.get_scroll_region_height()
    
    def get_footer_position(self) -> int:
        """Get the line position where footer should be rendered.
        
        Requirements: 9.4 - Fixed footer positioning
        
        Returns:
            Line number (1-indexed) for footer start
        """
        self._update_terminal_size()
        return self._terminal_height - self._config.footer_total_height + 1
    
    def move_to_footer(self) -> None:
        """Move cursor to footer position for rendering.
        
        Requirements: 9.4 - Fixed footer rendering
        """
        import sys
        
        footer_line = self.get_footer_position()
        # ANSI escape sequence to move cursor: ESC[line;columnH
        sys.stdout.write(f"\033[{footer_line};1H")
        sys.stdout.flush()
    
    def clear_content_region(self) -> None:
        """Clear the content region while preserving footer.
        
        Requirements: 9.4 - Scroll behavior management
        """
        import sys
        
        self._update_terminal_size()
        
        # Move to top of content region
        sys.stdout.write("\033[1;1H")
        
        # Clear from cursor to start of footer
        scroll_height = self.get_scroll_region_height()
        for _ in range(scroll_height):
            sys.stdout.write("\033[2K\n")  # Clear line and move down
        
        # Move back to top
        sys.stdout.write("\033[1;1H")
        sys.stdout.flush()


class ScrollRegionContext:
    """Context manager for scroll region management.
    
    Requirements: 9.4 - Scroll behavior for long content
    
    Usage:
        with ScrollRegionContext(layout_manager):
            # Content rendered here will scroll
            # Footer remains fixed
    """
    
    def __init__(self, layout_manager: LayoutManager) -> None:
        self._layout = layout_manager
        self._enabled = False
    
    def __enter__(self) -> 'ScrollRegionContext':
        """Set up scroll region on entry."""
        try:
            self._layout.setup_scroll_region()
            self._enabled = True
        except Exception:
            # Scroll region setup may fail on some terminals
            self._enabled = False
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Reset scroll region on exit."""
        if self._enabled:
            try:
                self._layout.reset_scroll_region()
            except Exception:
                pass
        return None


# Global instance
_layout_manager: Optional[LayoutManager] = None


def get_layout_manager(console: Optional[Console] = None) -> LayoutManager:
    """Get the global LayoutManager instance.
    
    Args:
        console: Optional console to use (only used on first call)
        
    Returns:
        Global LayoutManager instance
    """
    global _layout_manager
    if _layout_manager is None:
        _layout_manager = LayoutManager(console=console)
    return _layout_manager
