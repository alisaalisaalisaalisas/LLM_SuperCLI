"""Streaming progress indicator for extended silence detection.

This module provides the StreamingProgressIndicator class that tracks
streaming activity and displays a "still thinking" indicator when no
content arrives for an extended period.

Requirements addressed:
- 5.1: WHILE streaming is active THEN the CLI SHALL display a visual indicator
- 5.4: WHEN no content arrives for an extended period THEN the CLI SHALL show
       a "still thinking" indicator
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


@dataclass
class StreamingProgressConfig:
    """Configuration for streaming progress indicator.
    
    Attributes:
        thinking_timeout_seconds: Time in seconds before showing "still thinking"
        update_interval_seconds: How often to check for timeout
        show_cancel_hint: Whether to show "Ctrl+X to cancel" hint
    """
    thinking_timeout_seconds: float = 5.0
    update_interval_seconds: float = 0.5
    show_cancel_hint: bool = True


class StreamingProgressIndicator:
    """Tracks streaming activity and shows "still thinking" indicator.
    
    This class monitors streaming activity and displays a visual indicator
    when no content has arrived for an extended period. It integrates with
    the existing streaming infrastructure without interfering with normal
    content display.
    
    Usage:
        indicator = StreamingProgressIndicator(console)
        indicator.start()
        
        # During streaming:
        indicator.on_content_received()  # Call when content arrives
        indicator.check_timeout()  # Call periodically to check for silence
        
        indicator.stop()
    
    Requirements:
    - 5.1: Display visual indicator while streaming is active
    - 5.4: Show "still thinking" when no content arrives for extended period
    """
    
    def __init__(
        self,
        console: Console,
        config: Optional[StreamingProgressConfig] = None,
        on_timeout_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize the streaming progress indicator.
        
        Args:
            console: Rich Console for output
            config: Optional configuration (uses defaults if not provided)
            on_timeout_callback: Optional callback when timeout occurs
        """
        self._console = console
        self._config = config or StreamingProgressConfig()
        self._on_timeout_callback = on_timeout_callback
        
        # Timing state
        self._start_time: Optional[float] = None
        self._last_content_time: Optional[float] = None
        self._is_active: bool = False
        self._is_showing_thinking: bool = False
        
        # Live display for "still thinking" indicator
        self._thinking_live: Optional[Live] = None
    
    @property
    def is_active(self) -> bool:
        """Check if the indicator is currently active."""
        return self._is_active
    
    @property
    def is_showing_thinking(self) -> bool:
        """Check if the "still thinking" indicator is currently displayed."""
        return self._is_showing_thinking
    
    @property
    def seconds_since_last_content(self) -> float:
        """Get seconds since last content was received.
        
        Returns:
            Seconds since last content, or 0 if not active or no content yet
        """
        if not self._is_active or self._last_content_time is None:
            return 0.0
        return time.time() - self._last_content_time
    
    def start(self) -> None:
        """Start tracking streaming activity.
        
        Call this when streaming begins. Resets all timing state.
        """
        current_time = time.time()
        self._start_time = current_time
        self._last_content_time = current_time
        self._is_active = True
        self._is_showing_thinking = False
    
    def stop(self) -> None:
        """Stop tracking and clean up any displayed indicators.
        
        Call this when streaming ends. Cleans up the "still thinking"
        indicator if it's displayed.
        """
        self._hide_thinking_indicator()
        self._is_active = False
        self._start_time = None
        self._last_content_time = None
    
    def on_content_received(self) -> None:
        """Record that content was received.
        
        Call this whenever streaming content arrives. This resets the
        timeout timer and hides the "still thinking" indicator if shown.
        """
        if not self._is_active:
            return
        
        self._last_content_time = time.time()
        
        # Hide "still thinking" indicator if it was shown
        if self._is_showing_thinking:
            self._hide_thinking_indicator()
    
    def check_timeout(self) -> bool:
        """Check if timeout has occurred and show indicator if needed.
        
        Call this periodically during streaming to check if the timeout
        threshold has been exceeded. If so, displays the "still thinking"
        indicator.
        
        Returns:
            True if timeout occurred and indicator was shown, False otherwise
        """
        if not self._is_active:
            return False
        
        # Check if we've exceeded the timeout threshold
        if self.seconds_since_last_content >= self._config.thinking_timeout_seconds:
            if not self._is_showing_thinking:
                self._show_thinking_indicator()
                
                # Call timeout callback if provided
                if self._on_timeout_callback:
                    self._on_timeout_callback()
                
                return True
        
        return False
    
    def _show_thinking_indicator(self) -> None:
        """Display the "still thinking" indicator.
        
        Shows a spinner with "Still thinking..." message and optional
        cancel hint.
        
        Requirements: 5.4 - Show "still thinking" indicator
        """
        if self._is_showing_thinking:
            return
        
        # Create spinner with "Still thinking..." message
        spinner = Progress(
            SpinnerColumn(style="yellow"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )
        spinner.add_task("Still thinking...", total=None)
        
        # Create layout with optional cancel hint
        if self._config.show_cancel_hint:
            layout = Table.grid(expand=True)
            layout.add_column(ratio=1)
            layout.add_column(justify="right")
            layout.add_row(spinner, Text("Ctrl+X to cancel", style="dim"))
            display_content = layout
        else:
            display_content = spinner
        
        # Start live display
        self._thinking_live = Live(
            display_content,
            console=self._console,
            refresh_per_second=10,
            transient=True,
        )
        self._thinking_live.start()
        self._is_showing_thinking = True
    
    def _hide_thinking_indicator(self) -> None:
        """Hide the "still thinking" indicator.
        
        Stops and cleans up the live display.
        """
        if self._thinking_live:
            try:
                self._thinking_live.stop()
            except Exception:
                pass
            finally:
                self._thinking_live = None
        
        self._is_showing_thinking = False
    
    def get_elapsed_time(self) -> float:
        """Get total elapsed time since streaming started.
        
        Returns:
            Seconds since start, or 0 if not active
        """
        if not self._is_active or self._start_time is None:
            return 0.0
        return time.time() - self._start_time


# Default timeout configuration
DEFAULT_THINKING_TIMEOUT = 5.0  # seconds
