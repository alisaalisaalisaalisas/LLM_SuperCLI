"""Reasoning display component for llm_supercli.

This module provides the ReasoningDisplay class that handles the display of
LLM reasoning/thinking content with proper buffering, deduplication, and
visual styling.

Requirements addressed:
- 5.1: Display reasoning in a distinct visual section (bordered box labeled "Reasoning")
- 5.2: Render text once without duplication or repetition
- 5.3: Display each step sequentially without overlapping or garbled text
- 5.4: Render special characters (unicode, escape sequences) correctly
- 5.5: Buffer and display complete thoughts rather than partial fragments
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Optional, Set

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


@dataclass
class ReasoningChunk:
    """Represents a chunk of reasoning content.
    
    Attributes:
        content: The reasoning text content
        step_number: Sequential step number for ordering
        is_complete: Whether this chunk represents a complete thought
        content_hash: Hash of normalized content for deduplication
    """
    content: str
    step_number: int = 0
    is_complete: bool = False
    content_hash: str = field(default="", repr=False)
    
    def __post_init__(self) -> None:
        """Compute content hash after initialization."""
        if not self.content_hash and self.content:
            self.content_hash = self._compute_hash(self.content)
    
    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute hash of normalized content for deduplication."""
        # Normalize: collapse whitespace, lowercase
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()


class ReasoningDisplay:
    """Display component for LLM reasoning/thinking content.
    
    Handles streaming reasoning content with:
    - Content buffering for complete thoughts
    - Duplicate detection using content hashing
    - Visual rendering in a bordered panel with "Reasoning" title
    - Proper handling of special characters (unicode, escape sequences)
    
    Requirements addressed:
    - 5.1: Display reasoning in distinct visual section (bordered box)
    - 5.2: Render text once without duplication
    - 5.3: Display steps sequentially without overlap
    - 5.4: Render special characters correctly
    - 5.5: Buffer complete thoughts before display
    
    Attributes:
        _console: Rich Console for output
        _displayed_hashes: Set of content hashes already displayed
        _buffer: Current content buffer for streaming
        _step_count: Counter for reasoning steps
        _live: Optional Live context for streaming updates
        _min_chunk_length: Minimum length before considering a chunk complete
    """
    
    # Minimum length for a chunk to be considered for deduplication
    MIN_CHUNK_LENGTH = 20
    
    # Patterns that indicate a complete thought (sentence/paragraph end)
    THOUGHT_TERMINATORS = [
        r'\.\s*$',      # Period at end
        r'\?\s*$',      # Question mark at end
        r'!\s*$',       # Exclamation at end
        r':\s*$',       # Colon at end (often precedes list)
        r'\n\n',        # Double newline (paragraph break)
        r'\n-\s',       # List item start
        r'\n\d+\.\s',   # Numbered list item
    ]
    
    def __init__(
        self,
        console: Optional[Console] = None,
        min_chunk_length: int = MIN_CHUNK_LENGTH,
    ) -> None:
        """Initialize the ReasoningDisplay.
        
        Args:
            console: Optional Rich Console instance. If not provided,
                     a new Console will be created.
            min_chunk_length: Minimum length for deduplication consideration
        """
        self._console = console or Console()
        self._displayed_hashes: Set[str] = set()
        self._buffer: str = ""
        self._step_count: int = 0
        self._live: Optional[Live] = None
        self._min_chunk_length = min_chunk_length
        self._is_streaming: bool = False
    
    @property
    def buffer(self) -> str:
        """Get the current buffer content."""
        return self._buffer
    
    @property
    def is_streaming(self) -> bool:
        """Check if currently in streaming mode."""
        return self._is_streaming
    
    @property
    def displayed_count(self) -> int:
        """Get count of unique content chunks displayed."""
        return len(self._displayed_hashes)
    
    def start_streaming(self) -> None:
        """Begin streaming mode for reasoning content.
        
        Initializes the live display context for real-time updates.
        Call this before streaming chunks with stream_chunk().
        
        Requirements: 5.5 - Buffer and display complete thoughts
        """
        if self._is_streaming:
            return
        
        self._is_streaming = True
        self._buffer = ""
        
        # Create initial panel with placeholder
        initial_panel = self._create_panel("", show_cursor=True)
        
        self._live = Live(
            initial_panel,
            console=self._console,
            refresh_per_second=15,
            vertical_overflow="visible",
            transient=True,
        )
        self._live.start()
    
    def stream_chunk(self, chunk: str) -> None:
        """Stream a chunk of reasoning content.
        
        Buffers content and updates the live display. Handles deduplication
        to ensure content is only displayed once.
        
        Args:
            chunk: New reasoning content chunk
            
        Requirements:
        - 5.2: Render text once without duplication
        - 5.4: Render special characters correctly
        - 5.5: Buffer complete thoughts
        """
        if not chunk:
            return
        
        # Handle special characters - ensure proper encoding
        chunk = self._normalize_special_chars(chunk)
        
        # Check for duplicate content
        if self._is_duplicate(chunk):
            return
        
        # Append to buffer
        self._buffer += chunk
        
        # Update live display if streaming
        if self._live and self._is_streaming:
            panel = self._create_panel(self._buffer, show_cursor=True)
            self._live.update(panel)
    
    def stop_streaming(self) -> str:
        """Stop streaming and finalize the display.
        
        Stops the live display and prints the final reasoning panel.
        Returns the complete buffered content.
        
        Returns:
            The complete reasoning content that was displayed
            
        Requirements: 5.3 - Display steps sequentially without overlap
        """
        content = self._buffer
        
        # Stop live display
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass
            finally:
                self._live = None
        
        self._is_streaming = False
        
        # Print final panel if we have content
        if content.strip():
            self._print_final_panel(content)
            self._step_count += 1
        
        # Clear buffer for next use
        self._buffer = ""
        
        return content
    
    def display(self, content: str) -> None:
        """Display reasoning content in a styled panel.
        
        This is the main method for displaying complete reasoning content.
        Handles deduplication to ensure content is only displayed once.
        
        Args:
            content: Reasoning content to display
            
        Requirements:
        - 5.1: Display in distinct visual section (bordered box)
        - 5.2: Render text once without duplication
        - 5.4: Render special characters correctly
        """
        if not content or not content.strip():
            return
        
        # Normalize special characters
        content = self._normalize_special_chars(content)
        
        # Check for duplicate content
        if self._is_duplicate(content):
            return
        
        # Mark as displayed
        self._mark_displayed(content)
        
        # Print the panel
        self._print_final_panel(content)
        self._step_count += 1
    
    def display_step(self, content: str, step_number: Optional[int] = None) -> None:
        """Display a numbered reasoning step.
        
        Displays reasoning with a step number prefix for multi-step
        reasoning processes.
        
        Args:
            content: Reasoning content for this step
            step_number: Optional step number (auto-increments if not provided)
            
        Requirements: 5.3 - Display each step sequentially
        """
        if not content or not content.strip():
            return
        
        # Use provided step number or auto-increment
        step = step_number if step_number is not None else self._step_count + 1
        
        # Normalize special characters
        content = self._normalize_special_chars(content)
        
        # Check for duplicate
        if self._is_duplicate(content):
            return
        
        # Mark as displayed
        self._mark_displayed(content)
        
        # Create step-prefixed content
        step_content = f"Step {step}:\n{content}"
        
        # Print the panel
        self._print_final_panel(step_content)
        self._step_count = step
    
    def reset(self) -> None:
        """Reset the display state for a new reasoning session.
        
        Clears all buffers and displayed content tracking.
        """
        # Stop any active streaming
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass
            finally:
                self._live = None
        
        self._displayed_hashes.clear()
        self._buffer = ""
        self._step_count = 0
        self._is_streaming = False
    
    def is_thought_complete(self, content: str) -> bool:
        """Check if content represents a complete thought.
        
        Used for buffering decisions during streaming.
        
        Args:
            content: Content to check
            
        Returns:
            True if content appears to be a complete thought
            
        Requirements: 5.5 - Buffer complete thoughts
        """
        if not content:
            return False
        
        # Check for thought terminators
        for pattern in self.THOUGHT_TERMINATORS:
            if re.search(pattern, content):
                return True
        
        return False
    
    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------
    
    def _is_duplicate(self, content: str) -> bool:
        """Check if content has already been displayed.
        
        Uses content hashing for efficient duplicate detection.
        Short content is never considered duplicate to avoid
        removing common phrases.
        
        Args:
            content: Content to check
            
        Returns:
            True if content is a duplicate
        """
        # Short content is never duplicate
        normalized = self._normalize_for_hash(content)
        if len(normalized) < self._min_chunk_length:
            return False
        
        content_hash = self._compute_hash(normalized)
        return content_hash in self._displayed_hashes
    
    def _mark_displayed(self, content: str) -> None:
        """Mark content as displayed for deduplication tracking.
        
        Args:
            content: Content that was displayed
        """
        normalized = self._normalize_for_hash(content)
        if len(normalized) >= self._min_chunk_length:
            content_hash = self._compute_hash(normalized)
            self._displayed_hashes.add(content_hash)
    
    def _normalize_for_hash(self, content: str) -> str:
        """Normalize content for hash comparison.
        
        Collapses whitespace and converts to lowercase for
        consistent comparison.
        
        Args:
            content: Content to normalize
            
        Returns:
            Normalized content string
        """
        return re.sub(r'\s+', ' ', content.strip().lower())
    
    def _compute_hash(self, content: str) -> str:
        """Compute MD5 hash of content.
        
        Args:
            content: Content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _normalize_special_chars(self, content: str) -> str:
        """Normalize special characters for proper display.
        
        Handles unicode characters and escape sequences to ensure
        they render correctly in the terminal.
        
        Args:
            content: Content with potential special characters
            
        Returns:
            Content with normalized special characters
            
        Requirements: 5.4 - Render special characters correctly
        """
        if not content:
            return content
        
        # Handle common escape sequences that might be literal strings
        # Convert literal \\n to actual newlines if they appear as text
        # But preserve actual escape sequences in the content
        
        # Handle unicode normalization - ensure consistent representation
        # This helps with characters that can be represented multiple ways
        import unicodedata
        try:
            content = unicodedata.normalize('NFC', content)
        except (TypeError, ValueError):
            pass  # Keep original if normalization fails
        
        # Handle potential encoding issues - replace invalid chars
        try:
            # Encode and decode to handle any invalid sequences
            content = content.encode('utf-8', errors='replace').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass  # Keep original if encoding fails
        
        return content
    
    def _create_panel(self, content: str, show_cursor: bool = False) -> Panel:
        """Create a Rich Panel for reasoning content.
        
        Args:
            content: Content to display in the panel
            show_cursor: Whether to show a cursor indicator (for streaming)
            
        Returns:
            Configured Rich Panel
            
        Requirements: 5.1 - Bordered box labeled "Reasoning"
        """
        # Build display text
        display_content = content.strip() if content else ""
        
        # Add cursor for streaming indication
        if show_cursor:
            display_content += "▌"
        
        # Create styled text
        text = Text(display_content, style="dim italic")
        
        # Create panel with "Reasoning" title and yellow border
        panel = Panel(
            text,
            title="💭 Reasoning",
            title_align="left",
            border_style="yellow",
            padding=(0, 1),
        )
        
        return panel
    
    def _print_final_panel(self, content: str) -> None:
        """Print the final reasoning panel.
        
        Args:
            content: Content to display
            
        Requirements: 5.1 - Display in bordered box with "Reasoning" title
        """
        panel = self._create_panel(content, show_cursor=False)
        self._console.print(panel)
        self._console.print()  # Add spacing after panel


# Global instance for convenience
_reasoning_display: Optional[ReasoningDisplay] = None


def get_reasoning_display(console: Optional[Console] = None) -> ReasoningDisplay:
    """Get the global ReasoningDisplay instance.
    
    Args:
        console: Optional Console to use (only used on first call)
        
    Returns:
        The global ReasoningDisplay instance
    """
    global _reasoning_display
    if _reasoning_display is None:
        _reasoning_display = ReasoningDisplay(console=console)
    return _reasoning_display


def display_reasoning(content: str, console: Optional[Console] = None) -> None:
    """Convenience function to display reasoning content.
    
    Args:
        content: Reasoning content to display
        console: Optional Console to use
    """
    display = get_reasoning_display(console)
    display.display(content)
