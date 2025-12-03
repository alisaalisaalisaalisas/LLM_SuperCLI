"""Message renderer with state machine for streaming content display.

This module provides the MessageRenderer class that manages message rendering
with a state machine approach. It handles transitions between different phases
(thinking, reasoning, responding, tool calls) and coordinates with StreamBuffer
for content deduplication.

Requirements addressed:
- 1.1: Append new content without clearing previous content
- 1.2: Display final reasoning in styled panel
- 1.3: Maintain reasoning display while beginning response
- 4.3: Transition from streaming to final display without re-rendering
- 5.1: Replace spinner cleanly without artifacts
- 5.2: Finalize content without re-rendering entire message
- 5.3: Display error and clean up partial content
"""

import logging
from typing import Optional, Tuple

from rich.console import Console, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from llm_supercli.rich_ui.message_state import MessagePhase, ToolCallRecord
from llm_supercli.rich_ui.stream_buffer import StreamBuffer
from llm_supercli.rich_ui.content_parser import parse_think_tags, filter_tool_syntax
from llm_supercli.rich_ui.theme import ThemeManager


logger = logging.getLogger(__name__)


class MessageRenderer:
    """Renderer for streaming messages with state machine management.
    
    The MessageRenderer manages the display of streaming content from LLM
    responses. It uses a state machine to track the current phase of rendering
    and coordinates with StreamBuffer for content deduplication.
    
    Key features:
    - State machine for tracking rendering phases
    - Deduplication of reasoning and response content
    - Clean transitions between phases without flickering
    - Proper cleanup on errors or interruptions
    
    State transitions:
        IDLE → THINKING (start_message)
        THINKING → REASONING (stream_reasoning)
        THINKING → RESPONDING (stream_response)
        REASONING → RESPONDING (stream_response)
        RESPONDING → TOOL_CALL (display_tool_call)
        TOOL_CALL → RESPONDING (stream_response)
        * → COMPLETE (finalize)
        * → ERROR (abort)
    
    Attributes:
        _console: Rich Console for output
        _theme: ThemeManager for styling
        _phase: Current MessagePhase
        _buffer: StreamBuffer for content accumulation
        _live: Optional Live context for dynamic updates
        _static_content: List of completed renderables
    """
    
    def __init__(
        self,
        console: Console,
        theme: ThemeManager,
    ) -> None:
        """Initialize the MessageRenderer.
        
        Args:
            console: Rich Console instance for output
            theme: ThemeManager for styling
        """
        self._console = console
        self._theme = theme
        self._phase = MessagePhase.IDLE
        self._buffer = StreamBuffer()
        self._live: Optional[Live] = None
        self._static_content: list[RenderableType] = []
        self._in_thinking = False  # Track if inside <think> tags
        self._response_printed = False  # Track if final response was already printed
        self._reasoning_printed = False  # Track if reasoning was already printed

    @property
    def phase(self) -> MessagePhase:
        """Get the current rendering phase."""
        return self._phase
    
    @property
    def buffer(self) -> StreamBuffer:
        """Get the stream buffer (for testing/inspection)."""
        return self._buffer
    
    @property
    def is_active(self) -> bool:
        """Check if renderer is actively displaying content."""
        return self._phase not in (MessagePhase.IDLE, MessagePhase.COMPLETE, MessagePhase.ERROR)
    
    def start_message(self) -> None:
        """Begin a new message, show thinking indicator.
        
        Transitions from IDLE to THINKING state and displays a spinner
        to indicate the model is processing.
        
        Requirements: 7.1, 7.2 - Thinking indicator with cancel hint
        
        Raises:
            RuntimeError: If called when not in IDLE state
        """
        if self._phase != MessagePhase.IDLE:
            logger.warning(
                f"start_message called in {self._phase.value} state, "
                "expected IDLE. Resetting state."
            )
            self._cleanup_live()
            self._buffer.clear()
        
        self._phase = MessagePhase.THINKING
        self._buffer.clear()
        self._static_content.clear()
        self._in_thinking = False
        self._response_printed = False
        self._reasoning_printed = False
        
        # Build thinking indicator with animated spinner and cancel hint (Requirements 7.1, 7.2)
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.table import Table
        
        spinner = Progress(
            SpinnerColumn(style=self._theme.get_style("spinner") or "cyan"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )
        spinner.add_task("Thinking...", total=None)
        
        # Create layout with spinner + cancel hint
        layout = Table.grid(expand=True)
        layout.add_column(ratio=1)  # Spinner column (expands)
        layout.add_column(justify="right")  # Cancel hint column (right-aligned)
        layout.add_row(spinner, Text("Ctrl+X to cancel", style="dim"))
        
        # Start live display with animated spinner
        # Use transient=True to prevent panel stacking/duplication
        self._live = Live(
            layout,
            console=self._console,
            refresh_per_second=10,
            vertical_overflow="visible",
            transient=True,
        )
        self._live.start()
    
    def stream_reasoning(self, chunk: str) -> None:
        """Stream reasoning content progressively.
        
        Accumulates reasoning content and updates the display. Handles
        deduplication to ensure content is only displayed once.
        
        Args:
            chunk: New reasoning content chunk
        """
        if not chunk:
            return
        
        # Transition to REASONING if needed
        if self._phase == MessagePhase.THINKING:
            self._phase = MessagePhase.REASONING
        
        # Append to buffer (handles deduplication)
        new_content = self._buffer.append_reasoning(chunk)
        
        # Update display if we have content
        if self._buffer.reasoning and self._live:
            self._update_reasoning_display()
    
    def stream_response(self, chunk: str) -> None:
        """Stream response content progressively.
        
        Accumulates response content and updates the display. Handles
        deduplication and filters tool call syntax from display.
        
        Args:
            chunk: New response content chunk
        """
        if not chunk:
            return
        
        # Transition to RESPONDING if needed
        if self._phase in (MessagePhase.THINKING, MessagePhase.REASONING, MessagePhase.TOOL_CALL):
            # If transitioning from REASONING, finalize reasoning display
            if self._phase == MessagePhase.REASONING and self._buffer.reasoning:
                self._finalize_reasoning_panel()
            self._phase = MessagePhase.RESPONDING
        
        # Append to buffer (handles deduplication)
        new_content = self._buffer.append_response(chunk)
        
        # Update display if we have content
        if self._buffer.response and self._live:
            self._update_response_display()

    def stream_content(self, chunk: str) -> None:
        """Stream content, automatically parsing think tags.
        
        This is a convenience method that parses content for <think> tags
        and routes to the appropriate stream method.
        
        Args:
            chunk: Raw content chunk that may contain think tags
        """
        if not chunk:
            return
        
        # Parse think tags
        parsed = parse_think_tags(chunk, self._in_thinking)
        self._in_thinking = parsed.in_thinking
        
        # Route content to appropriate handlers
        if parsed.reasoning:
            self.stream_reasoning(parsed.reasoning)
        
        if parsed.response:
            self.stream_response(parsed.response)
    
    def display_tool_call(self, call: ToolCallRecord) -> bool:
        """Display a tool call (deduplicated).
        
        Displays the tool call header if it hasn't been displayed before.
        Uses the buffer's deduplication to prevent duplicate displays.
        
        Requirements addressed:
        - 2.1: Display tool name and arguments exactly once
        - 2.2: Display each tool call in deterministic order with visual separators
        
        Args:
            call: The tool call record to display
            
        Returns:
            True if the tool call was displayed, False if duplicate
        """
        # Check if already displayed
        if not self._buffer.add_tool_call(call):
            return False
        
        # Transition to TOOL_CALL phase
        if self._phase == MessagePhase.RESPONDING:
            # Finalize current response display before showing tool
            self._finalize_response_panel()
        
        self._phase = MessagePhase.TOOL_CALL
        
        # Add visual separator if this is not the first tool call
        if len(self._buffer.tool_calls) > 1:
            self._console.print(Text("─" * 40, style="dim"))
        
        # Format and display tool call header
        header = self._format_tool_header(call)
        self._console.print(header)
        
        # Mark as displayed
        call.displayed = True
        return True
    
    def display_tool_result(self, call: ToolCallRecord) -> None:
        """Display tool result beneath its call.
        
        Requirements addressed:
        - 2.3: Display success or failure indicator with brief result preview
        - 3.1: Display result immediately below tool call header
        - 3.2: Display truncated preview with character/line count for large results
        - 3.3: Display error message with failure indicator
        - 3.4: Maintain consistent visual hierarchy between calls and results
        
        Args:
            call: The tool call record with result to display
        """
        if call.result is None:
            return
        
        result_display = self._format_tool_result(call)
        # Indent result to show hierarchy under tool call
        self._console.print(result_display)
    
    def finalize(self) -> Tuple[str, str]:
        """Complete message and return content.
        
        Finalizes the current message, cleaning up the live display
        and returning the accumulated content.
        
        Returns:
            Tuple of (response_content, reasoning_content)
        """
        # Get content before cleanup
        response = self._buffer.response
        reasoning = self._buffer.reasoning
        
        # Filter tool syntax from response for clean return
        filtered_response = filter_tool_syntax(response) if response else ""
        
        # Clean up live display FIRST to clear streaming content
        self._cleanup_live()
        
        # Finalize any pending displays (only if not already printed)
        # Check reasoning first, then response (both can be displayed)
        if reasoning and not self._reasoning_printed:
            self._finalize_reasoning_panel()
        
        if response and not self._response_printed:
            self._finalize_response_panel()
        
        # Transition to COMPLETE
        self._phase = MessagePhase.COMPLETE
        
        return filtered_response, reasoning
    
    @property
    def response_already_printed(self) -> bool:
        """Check if the response was already printed during finalization."""
        return self._response_printed
    
    @property
    def reasoning_already_printed(self) -> bool:
        """Check if the reasoning was already printed during finalization."""
        return self._reasoning_printed
    
    def abort(self, error: Optional[str] = None) -> Tuple[str, str]:
        """Abort current message, optionally show error.
        
        Cleans up the current state and optionally displays an error
        message. Returns any partial content that was accumulated.
        
        Args:
            error: Optional error message to display
            
        Returns:
            Tuple of (partial_response, partial_reasoning)
            
        Requirements: 1.6 - Display error without bordered panel
        """
        # Get partial content before cleanup
        response = self._buffer.response
        reasoning = self._buffer.reasoning
        
        # Clean up live display
        self._cleanup_live()
        
        # Display error if provided (without border)
        if error:
            error_header = Text()
            error_header.append("❌ ", style="red bold")
            error_header.append("Error", style="red bold")
            self._console.print(error_header)
            self._console.print(Text(error, style=self._theme.get_style("error_message")))
            self._console.print()  # Add spacing
        
        # Transition to ERROR state
        self._phase = MessagePhase.ERROR
        
        return response, reasoning

    def reset(self) -> None:
        """Reset renderer to IDLE state for a new message.
        
        Clears all buffers and resets state. Should be called before
        starting a new message if the previous message completed.
        """
        self._cleanup_live()
        self._buffer.clear()
        self._static_content.clear()
        self._phase = MessagePhase.IDLE
        self._in_thinking = False
        self._response_printed = False
        self._reasoning_printed = False
    
    # -------------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------------
    
    def _cleanup_live(self) -> None:
        """Clean up the Live display context and clear streaming content."""
        if self._live:
            try:
                # Update with empty content before stopping to clear the display
                self._live.update(Text(""))
                self._live.stop()
            except Exception as e:
                logger.debug(f"Error stopping live display: {e}")
            finally:
                self._live = None
    
    def _update_reasoning_display(self) -> None:
        """Update the live display with current reasoning content.
        
        Displays reasoning during streaming with a cursor indicator.
        The 💭 header is only added in _finalize_reasoning_panel to avoid duplicates.
        
        Requirements: 5.1, 5.2 - Yellow panel with real-time updates
        """
        if not self._live or not self._buffer.reasoning:
            return
        
        # Clean the reasoning content for display
        display_text = self._buffer.reasoning.strip()
        if not display_text:
            return
        
        # Create text with proper newline handling - no emoji header during streaming
        # The emoji will be added in _finalize_reasoning_panel
        # Use underscore cursor for better terminal compatibility
        content_text = Text(display_text + "_", style="dim italic")
        
        self._live.update(content_text)
    
    def _update_response_display(self) -> None:
        """Update the live display with current response content.
        
        Displays response during streaming with markdown rendering for proper formatting.
        The 🤖 header is only added in _finalize_response_panel to avoid duplicates.
        
        Requirements: 4.2, 4.3 - Assistant panel with cyan border and markdown
        """
        if not self._live:
            return
        
        # Filter tool syntax from display
        display_text = filter_tool_syntax(self._buffer.response) if self._buffer.response else ""
        if not display_text.strip():
            # Show minimal placeholder during streaming
            # Use underscore cursor for better terminal compatibility
            self._live.update(Text("_", style="dim"))
            return
        
        # Add cursor to the end of the content - no emoji header during streaming
        # The emoji will be added in _finalize_response_panel
        # Use underscore cursor for better terminal compatibility
        content_with_cursor = display_text + "_"
        markdown_content = Markdown(content_with_cursor)
        
        self._live.update(markdown_content)
    
    def _finalize_reasoning_panel(self) -> None:
        """Finalize reasoning display.
        
        Print the reasoning panel as static content with yellow border,
        then restart live display for response streaming.
        
        Requirements: 5.1, 5.3 - Yellow panel finalized before response
        """
        if not self._buffer.reasoning:
            return
        
        # Stop live display
        self._cleanup_live()
        
        # Print reasoning without border
        display_text = self._buffer.reasoning.strip()
        if display_text:
            # Mark that we've printed the reasoning BEFORE printing
            self._reasoning_printed = True
            
            content = Text()
            content.append("💭 ", style="yellow")
            content.append(display_text, style="dim italic")
            self._console.print(content)
            self._console.print()  # Add spacing
        
        # Restart live display for response streaming
        self._live = Live(
            Text("", style="dim"),
            console=self._console,
            refresh_per_second=15,
            vertical_overflow="visible",
            transient=True,
        )
        self._live.start()
    
    def _finalize_response_panel(self) -> None:
        """Finalize response display.
        
        Print the final response panel and stop the live display.
        Sets a flag to indicate the response was already printed.
        """
        # Stop live display first to clear streaming content
        self._cleanup_live()
        
        if not self._buffer.response:
            return
        
        # Print final response without border
        display_text = filter_tool_syntax(self._buffer.response)
        if display_text.strip():
            # Mark that we've printed the final response BEFORE printing
            self._response_printed = True
            
            self._console.print(Text("🤖 ", style="bold cyan"), end="")
            self._console.print(Markdown(display_text))
            self._console.print()  # Add spacing
    
    def _format_tool_header(self, call: ToolCallRecord) -> RenderableType:
        """Format a tool call header for display.
        
        Creates a consistent, styled header for tool calls showing the tool
        name and a preview of arguments.
        
        Requirements addressed:
        - 2.1: Display tool name and arguments exactly once
        
        Args:
            call: The tool call record
            
        Returns:
            Formatted renderable for the tool header
        """
        tool_color = self._theme.get_color("info") or "cyan"
        
        # Build the header text
        header = Text()
        header.append("🔧 ", style="bold")
        header.append(call.name, style=f"bold {tool_color}")
        
        # Format arguments preview
        if call.arguments:
            args_parts = []
            for key, value in call.arguments.items():
                # Format the value with truncation for long strings
                if isinstance(value, str):
                    if len(value) > 40:
                        display_val = f'"{value[:37]}..."'
                    else:
                        display_val = f'"{value}"'
                elif isinstance(value, (dict, list)):
                    # Show type and length for complex types
                    display_val = f"<{type(value).__name__}:{len(value)}>"
                else:
                    display_val = str(value)
                
                args_parts.append(f"{key}={display_val}")
                
                # Limit to 3 arguments in preview
                if len(args_parts) >= 3:
                    if len(call.arguments) > 3:
                        args_parts.append("...")
                    break
            
            args_str = ", ".join(args_parts)
            header.append("(", style="dim")
            header.append(args_str, style="dim")
            header.append(")", style="dim")
        
        return header
    
    def _format_tool_result(self, call: ToolCallRecord) -> RenderableType:
        """Format a tool result for display.
        
        Creates a formatted display of the tool result with success/failure
        indicators and truncation for large results.
        
        Requirements addressed:
        - 2.3: Display success or failure indicator with brief result preview
        - 3.2: Display truncated preview with character/line count for large results
        - 3.3: Display error message with failure indicator
        - 3.4: Maintain consistent visual hierarchy between calls and results
        
        Args:
            call: The tool call record with result
            
        Returns:
            Formatted renderable for the tool result
        """
        if call.result is None:
            return Text("")
        
        result_text = Text()
        
        # Add indentation for visual hierarchy
        indent = "  "
        
        if call.success:
            # Truncate large results
            result_preview, was_truncated, metadata = self._truncate_result(call.result)
            
            if result_preview.strip():
                # Add result preview with indentation
                for line in result_preview.split('\n'):
                    result_text.append(indent)
                    result_text.append(line, style="dim")
                    result_text.append("\n")
            
            # Add truncation metadata if applicable
            if was_truncated and metadata:
                result_text.append(indent)
                result_text.append(f"... ({metadata})", style="dim italic")
                result_text.append("\n")
            
            # Add success indicator
            success_color = self._theme.get_color("success") or "green"
            result_text.append(indent)
            result_text.append("✓ ", style=f"bold {success_color}")
            result_text.append("Success", style=success_color)
        else:
            # Display error with failure indicator
            error_color = self._theme.get_color("error") or "red"
            result_text.append(indent)
            result_text.append("✗ ", style=f"bold {error_color}")
            result_text.append("Failed: ", style=f"bold {error_color}")
            result_text.append(call.result, style=error_color)
        
        return result_text
    
    def _truncate_result(
        self, 
        result: str, 
        max_chars: int = 200, 
        max_lines: int = 5
    ) -> tuple[str, bool, str]:
        """Truncate a large result for preview display.
        
        Requirements addressed:
        - 3.2: Display truncated preview with character/line count for large results
        
        Args:
            result: The result string to truncate
            max_chars: Maximum characters to show
            max_lines: Maximum lines to show
            
        Returns:
            Tuple of (truncated_content, was_truncated, metadata_string)
            - truncated_content: The truncated result string
            - was_truncated: True if truncation occurred
            - metadata_string: Human-readable size info (e.g., "1234 chars, 50 lines")
        """
        if not result:
            return "", False, ""
        
        lines = result.split('\n')
        total_lines = len(lines)
        total_chars = len(result)
        
        # Build metadata string
        metadata_parts = []
        if total_chars > 0:
            metadata_parts.append(f"{total_chars} chars")
        if total_lines > 1:
            metadata_parts.append(f"{total_lines} lines")
        metadata = ", ".join(metadata_parts)
        
        # Check if truncation needed
        needs_truncation = total_chars > max_chars or total_lines > max_lines
        
        if not needs_truncation:
            return result, False, metadata
        
        # Truncate by lines first
        if total_lines > max_lines:
            truncated = '\n'.join(lines[:max_lines])
        else:
            truncated = result
        
        # Then truncate by characters
        if len(truncated) > max_chars:
            truncated = truncated[:max_chars]
        
        return truncated, True, metadata
