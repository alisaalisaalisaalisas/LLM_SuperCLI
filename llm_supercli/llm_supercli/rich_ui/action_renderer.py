"""
Action renderer for the action cards system.

This module provides the ActionRenderer class that converts Action models
into Rich renderables for display in the CLI.

Requirements: 6.1, 6.2, 6.3, 6.4 - Tool execution action cards
"""
import logging
import time
from typing import Optional, Union

from rich.console import Console, RenderableType, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text
from rich.rule import Rule

from .action_models import (
    Action,
    ActionType,
    ReadFilesAction,
    SearchAction,
    FileAction,
    StatusAction,
    ThinkingAction,
    DoneAction,
    ErrorAction,
    ToolCallAction,
    ToolResultAction,
    ToolWarningAction,
    ToolProgressAction,
)
from .card_styles import CardStyle, get_card_style, CARD_STYLES
from .theme import ThemeManager


logger = logging.getLogger(__name__)

# Success/failure indicator constants (Requirements 6.2, 6.3)
SUCCESS_INDICATOR = "✓"
FAILURE_INDICATOR = "✗"


class ActionRenderer:
    """
    Renderer that converts Action models to Rich output.
    
    This class provides methods for rendering various action types as styled
    cards in the terminal. It supports theming and configurable display options.
    
    Attributes:
        console: Rich Console instance for output
        theme: ThemeManager for styling
        max_files_preview: Maximum number of files to show in file list
        max_content_preview_lines: Maximum lines of content preview to show
    """
    
    def __init__(
        self,
        console: Console,
        theme: ThemeManager,
        max_files_preview: int = 5,
        max_content_preview_lines: int = 3
    ) -> None:
        """
        Initialize the ActionRenderer.
        
        Args:
            console: Rich Console instance for output
            theme: ThemeManager for styling
            max_files_preview: Maximum number of files to show in file lists
            max_content_preview_lines: Maximum lines of content preview
        """
        self._console = console
        self._theme = theme
        self._max_files = max_files_preview
        self._max_preview_lines = max_content_preview_lines
        self._live: Optional[Live] = None

    @property
    def console(self) -> Console:
        """Get the Rich console."""
        return self._console
    
    @property
    def theme(self) -> ThemeManager:
        """Get the theme manager."""
        return self._theme
    
    def render(self, action: Action) -> None:
        """
        Render an action as a styled card.
        
        This method dispatches to type-specific render methods based on
        the action type. If rendering fails, it falls back to simple text output.
        
        Args:
            action: The Action model to render
            
        Requirements: 7.2 - Convert Action models to Rich renderables
        """
        try:
            renderable = self._action_to_renderable(action)
            self._console.print(renderable)
        except Exception as e:
            # Fallback to simple text output on error
            # Requirements: 8.4 - Fall back to simple text output on errors
            logger.warning(f"Error rendering action {action.type}: {e}")
            self._render_fallback(action)
    
    def _action_to_renderable(self, action: Action) -> RenderableType:
        """
        Convert an Action model to a Rich renderable.
        
        Args:
            action: The Action model to convert
            
        Returns:
            A Rich renderable object
            
        Requirements: 7.2 - Convert Action models to Rich renderables
        """
        dispatch_map = {
            ActionType.READ_FILES: self._render_read_files_action,
            ActionType.SEARCH: self._render_search_action,
            ActionType.CREATE_FILE: self._render_file_action,
            ActionType.UPDATE_FILE: self._render_file_action,
            ActionType.THINKING: self._render_thinking_action,
            ActionType.DONE: self._render_done_action,
            ActionType.STATUS: self._render_status_action,
            ActionType.ERROR: self._render_error_action,
            ActionType.TOOL_CALL: self._render_tool_call_action,
            ActionType.TOOL_RESULT: self._render_tool_result_action,
            ActionType.TOOL_WARNING: self._render_tool_warning_action,
            ActionType.TOOL_PROGRESS: self._render_tool_progress_action,
        }
        
        renderer = dispatch_map.get(action.type)
        if renderer:
            return renderer(action)
        
        # Unknown action type - use generic card
        return self._create_card_panel(
            action.type,
            Text(f"Unknown action: {action.type.value}")
        )
    
    def _create_card_panel(
        self,
        action_type: ActionType,
        content: RenderableType,
        title_override: Optional[str] = None,
        **format_kwargs
    ) -> Panel:
        """
        Create a styled Panel for an action card.
        
        This helper ensures consistent panel creation across all action types.
        
        Args:
            action_type: The type of action (determines styling)
            content: The content to display in the panel body
            title_override: Optional override for the title text
            **format_kwargs: Format arguments for title template (e.g., filename)
            
        Returns:
            A styled Rich Panel
            
        Requirements: 7.4 - Accept configuration for theming and display options
        """
        style = get_card_style(action_type)
        
        # Format title with any provided kwargs
        if title_override:
            title_text = title_override
        else:
            try:
                title_text = style.title_template.format(**format_kwargs)
            except KeyError:
                title_text = style.title_template
        
        # Build title with icon (extra space for better visual separation)
        title = f"{style.icon}  {title_text}"
        
        # Return content without border - just icon + title + content
        from rich.console import Group
        header = Text()
        header.append(f"{style.icon} ", style=style.title_style)
        header.append(title_text, style=style.title_style)
        
        return Group(header, content)
    
    def _render_fallback(self, action: Action) -> None:
        """
        Render a fallback text representation of an action.
        
        Used when normal rendering fails to ensure the user still sees
        information about the action.
        
        Args:
            action: The Action model to render
            
        Requirements: 8.4 - Fall back to simple text output on errors
        """
        style = get_card_style(action.type)
        fallback_text = f"{style.icon} {style.title_template}"
        
        # Add any relevant details based on action type
        if isinstance(action, ReadFilesAction):
            if action.files:
                fallback_text += f": {', '.join(action.files[:3])}"
                if len(action.files) > 3:
                    fallback_text += f" (+{len(action.files) - 3} more)"
        elif isinstance(action, SearchAction):
            if action.query:
                fallback_text += f": {action.query}"
        elif isinstance(action, FileAction):
            if action.filename:
                fallback_text = fallback_text.replace("{filename}", action.filename)
        elif isinstance(action, ErrorAction):
            if action.message:
                fallback_text += f": {action.message}"
        elif isinstance(action, StatusAction):
            # Build fallback status text
            parts = [f"⏱ {action.elapsed_time:.1f}s"]
            if action.input_tokens is not None or action.output_tokens is not None:
                total = (action.input_tokens or 0) + (action.output_tokens or 0)
                parts.append(f"📊 {total:,} tokens")
            if action.is_free_tier:
                parts.append("🆓 Free")
            elif action.credits_used is not None:
                parts.append(f"💰 ${action.credits_used:.4f}")
            fallback_text = " │ ".join(parts)
        
        self._console.print(f"[dim]{fallback_text}[/dim]")

    # -------------------------------------------------------------------------
    # Convenience methods for rendering actions
    # -------------------------------------------------------------------------
    
    def render_read_files(
        self,
        files: list[str],
        failed: list[str] = None
    ) -> None:
        """
        Convenience method for rendering file read cards.
        
        Creates a ReadFilesAction and renders it as a styled card showing
        which files were read and which failed.
        
        Args:
            files: List of successfully read file paths
            failed: Optional list of file paths that failed to read
            
        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        action = ReadFilesAction(
            type=ActionType.READ_FILES,
            files=files or [],
            failed_files=failed or []
        )
        self.render(action)

    def render_search(
        self,
        query: str,
        results_count: int = 0,
        results_preview: list[str] = None
    ) -> None:
        """
        Convenience method for rendering search cards.
        
        Creates a SearchAction and renders it as a styled card showing
        the search query and results summary.
        
        Args:
            query: The search query or pattern used
            results_count: Number of matches found (0 for no matches)
            results_preview: Optional list of result previews
            
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        action = SearchAction(
            type=ActionType.SEARCH,
            query=query,
            results_count=results_count,
            results_preview=results_preview or []
        )
        self.render(action)

    def render_file_created(
        self,
        filename: str,
        preview: Optional[str] = None
    ) -> None:
        """
        Convenience method for rendering file creation cards.
        
        Creates a FileAction with CREATE_FILE type and renders it as a styled
        card with green border showing the created filename and optional preview.
        
        Args:
            filename: Path to the created file
            preview: Optional preview of the file content (first few lines)
            
        Requirements: 3.1, 3.2, 3.3
        """
        action = FileAction(
            type=ActionType.CREATE_FILE,
            filename=filename,
            content_preview=preview
        )
        self.render(action)

    def render_file_updated(
        self,
        filename: str,
        summary: Optional[str] = None
    ) -> None:
        """
        Convenience method for rendering file update cards.
        
        Creates a FileAction with UPDATE_FILE type and renders it as a styled
        card with blue border showing the updated filename and optional change summary.
        
        Args:
            filename: Path to the updated file
            summary: Optional summary of the changes made
            
        Requirements: 4.1, 4.2, 4.3
        """
        action = FileAction(
            type=ActionType.UPDATE_FILE,
            filename=filename,
            change_summary=summary
        )
        self.render(action)

    # -------------------------------------------------------------------------
    # Thinking/Done state methods
    # -------------------------------------------------------------------------

    def start_thinking(self, message: str = "Thinking...") -> None:
        """
        Start animated thinking indicator with Live display and spinner.
        
        Displays a thinking card with an animated spinner that updates
        in real-time. The spinner uses the "dots" animation style for
        a subtle, non-distracting effect.
        
        Args:
            message: Optional message to display (default: "Thinking...")
            
        Requirements: 5.1 - Display a thinking indicator with animated spinner
        Requirements: 5.2 - Show "Thinking..." text with a subtle animation
        """
        # Stop any existing thinking display first
        if self._live is not None:
            self._stop_live_display()
        
        # Get the thinking style
        style = get_card_style(ActionType.THINKING)
        
        # Create spinner with the thinking message (no border)
        spinner = Spinner("dots", text=Text(f" {message}", style="dim italic"))
        
        # Start Live display for animation (no panel/border)
        self._live = Live(
            spinner,
            console=self._console,
            refresh_per_second=10,
            transient=True  # Remove when stopped for smooth transition
        )
        self._live.start()

    def stop_thinking(self, show_done: bool = True) -> None:
        """
        Stop thinking indicator and optionally show Done card.
        
        Stops the animated spinner and replaces it with a "Done!" card
        if show_done is True. The transition is handled smoothly by
        using transient=True on the Live display.
        
        Args:
            show_done: Whether to display a "Done!" card after stopping
            
        Requirements: 5.3 - Replace the thinking indicator with a "Done!" message
        Requirements: 5.4 - Perform the transition smoothly without flickering
        """
        self._stop_live_display()
        
        if show_done:
            # Render the Done card
            action = DoneAction(type=ActionType.DONE, message="Done!")
            self.render(action)

    def _stop_live_display(self) -> None:
        """
        Internal method to stop the Live display cleanly.
        
        Ensures the Live display is properly stopped and cleaned up
        to prevent flickering or display artifacts.
        """
        if self._live is not None:
            try:
                self._live.stop()
            except Exception as e:
                logger.warning(f"Error stopping live display: {e}")
            finally:
                self._live = None

    @property
    def is_thinking(self) -> bool:
        """
        Check if the thinking indicator is currently active.
        
        Returns:
            True if thinking animation is running, False otherwise
        """
        return self._live is not None

    # -------------------------------------------------------------------------
    # Type-specific render methods
    # -------------------------------------------------------------------------
    
    def _render_read_files_action(self, action: Action) -> RenderableType:
        """
        Render a ReadFilesAction as a card.
        
        Displays file list with truncation when exceeding max_files_preview,
        and shows failed files with error indicators.
        
        Args:
            action: ReadFilesAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        if not isinstance(action, ReadFilesAction):
            action = ReadFilesAction(
                type=ActionType.READ_FILES,
                files=action.metadata.get("files", []),
                failed_files=action.metadata.get("failed_files", [])
            )
        
        content = Text()
        
        # Handle successful files with truncation
        # Requirements: 1.2 - List each filename on a separate line
        # Requirements: 1.3 - Show first N files and indicate remaining count
        # Filter out empty file paths
        valid_files = [f for f in action.files if f]
        files_to_show = valid_files[:self._max_files]
        remaining_count = len(valid_files) - self._max_files
        
        for i, filepath in enumerate(files_to_show):
            if i > 0:
                content.append("\n")
            content.append("  ")
            content.append(filepath, style="cyan")
        
        # Show remaining count if truncated
        if remaining_count > 0:
            content.append("\n")
            content.append(f"  (+{remaining_count} more)", style="dim")
        
        # Handle failed files with error indicator
        # Requirements: 1.4 - Display failed files with error indicator
        # Filter out empty file paths
        valid_failed = [f for f in action.failed_files if f]
        if valid_failed:
            for filepath in valid_failed:
                if content.plain:  # Add newline if there's already content
                    content.append("\n")
                content.append("  ✗ ", style="red bold")
                content.append(filepath, style="red")
        
        # Handle empty case
        if not content.plain:
            content.append("No files", style="dim")
        
        return self._create_card_panel(ActionType.READ_FILES, content)
    
    def _render_search_action(self, action: Action) -> RenderableType:
        """
        Render a SearchAction as a card.
        
        Displays the search query in the card body and shows either
        the results count or "No matches found" for zero results.
        
        Args:
            action: SearchAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 2.1, 2.2, 2.3, 2.4
        """
        if not isinstance(action, SearchAction):
            action = SearchAction(
                type=ActionType.SEARCH,
                query=action.metadata.get("query", ""),
                results_count=action.metadata.get("results_count", 0),
                results_preview=action.metadata.get("results_preview", [])
            )
        
        content = Text()
        
        # Display the search query in the card body
        # Requirements: 2.2 - Show the search query or pattern in the card body
        if action.query:
            content.append("  ")
            content.append(action.query, style="yellow italic")
        
        # Show results count or "No matches found"
        # Requirements: 2.3 - Display a summary of matches found
        # Requirements: 2.4 - Indicate "No matches found" for zero results
        if action.results_count > 0:
            if content.plain:
                content.append("\n")
            content.append("  ")
            match_word = "match" if action.results_count == 1 else "matches"
            content.append(f"Found {action.results_count} {match_word}", style="dim")
        else:
            if content.plain:
                content.append("\n")
            content.append("  ")
            content.append("No matches found", style="dim italic")
        
        return self._create_card_panel(ActionType.SEARCH, content)
    
    def _render_file_action(self, action: Action) -> RenderableType:
        """
        Render a FileAction (create or update) as a card.
        
        Displays the filename in the title with appropriate styling:
        - Green border for file creation (CREATE_FILE)
        - Blue border for file updates (UPDATE_FILE)
        
        Optionally shows content preview for created files or change summary
        for updated files.
        
        Args:
            action: FileAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3
        """
        if not isinstance(action, FileAction):
            action = FileAction(
                type=action.type,
                filename=action.metadata.get("filename", ""),
                content_preview=action.metadata.get("content_preview"),
                change_summary=action.metadata.get("change_summary")
            )
        
        content = Text()
        
        # Determine what content to show based on action type
        # Requirements: 3.3 - Optionally show preview of first few lines for creation
        # Requirements: 4.3 - Optionally show summary of changes for updates
        if action.type == ActionType.CREATE_FILE and action.content_preview:
            # Show content preview for file creation
            preview_lines = action.content_preview.split('\n')
            lines_to_show = preview_lines[:self._max_preview_lines]
            
            for i, line in enumerate(lines_to_show):
                if i > 0:
                    content.append("\n")
                content.append("  ")
                # Truncate long lines
                display_line = line[:80] + "..." if len(line) > 80 else line
                content.append(display_line, style="dim")
            
            # Indicate if there are more lines
            if len(preview_lines) > self._max_preview_lines:
                content.append("\n")
                remaining = len(preview_lines) - self._max_preview_lines
                content.append(f"  (+{remaining} more lines)", style="dim italic")
                
        elif action.type == ActionType.UPDATE_FILE and action.change_summary:
            # Show change summary for file updates
            content.append("  ")
            content.append(action.change_summary, style="dim")
        
        # If no content to show, leave the card body empty (just filename in title)
        # The filename is shown in the title via the {filename} template
        
        return self._create_card_panel(
            action.type,
            content,
            filename=action.filename
        )
    
    def _render_thinking_action(self, action: Action) -> RenderableType:
        """
        Render a ThinkingAction as a card.
        
        Args:
            action: ThinkingAction to render
            
        Returns:
            Rich renderable for the action
            
        Note: Full implementation in task 7.1
        """
        if not isinstance(action, ThinkingAction):
            action = ThinkingAction(
                type=ActionType.THINKING,
                message=action.metadata.get("message", "Thinking...")
            )
        
        content = Text(action.message, style="dim italic")
        return self._create_card_panel(ActionType.THINKING, content)
    
    def _render_done_action(self, action: Action) -> RenderableType:
        """
        Render a DoneAction as a card.
        
        Args:
            action: DoneAction to render
            
        Returns:
            Rich renderable for the action
            
        Note: Full implementation in task 7.1
        """
        if not isinstance(action, DoneAction):
            action = DoneAction(
                type=ActionType.DONE,
                message=action.metadata.get("message", "Done!")
            )
        
        content = Text(action.message, style="bold green")
        return self._create_card_panel(ActionType.DONE, content)
    
    def render_status(
        self,
        elapsed_time: float,
        credits: Optional[float] = None,
        tokens: Optional[tuple[int, int]] = None,
        is_free: bool = False
    ) -> None:
        """
        Render status footer with metadata.
        
        Displays a horizontal rule styled footer showing elapsed time,
        token counts, and credits/free indicator.
        
        Args:
            elapsed_time: Time taken for the operation in seconds
            credits: Optional credits consumed (None if not applicable)
            tokens: Optional tuple of (input_tokens, output_tokens)
            is_free: Whether the provider is free-tier
            
        Requirements: 6.1 - Display a status footer with elapsed time
        Requirements: 6.2 - Show the credit usage in the status footer
        Requirements: 6.3 - Display input and output token counts
        Requirements: 6.4 - Indicate "Free" instead of credit cost for free-tier
        """
        input_tokens = tokens[0] if tokens else None
        output_tokens = tokens[1] if tokens else None
        
        action = StatusAction(
            type=ActionType.STATUS,
            elapsed_time=elapsed_time,
            credits_used=credits,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            is_free_tier=is_free
        )
        self.render(action)

    def _render_status_action(self, action: Action) -> RenderableType:
        """
        Render a StatusAction as a horizontal rule styled footer.
        
        Creates a footer with elapsed time, token counts, and credits/free
        indicator, styled with horizontal rules for visual separation.
        
        Args:
            action: StatusAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 6.1 - Display a status footer with elapsed time
        Requirements: 6.2 - Show the credit usage in the status footer
        Requirements: 6.3 - Display input and output token counts
        Requirements: 6.4 - Indicate "Free" instead of credit cost for free-tier
        """
        if not isinstance(action, StatusAction):
            action = StatusAction(
                type=ActionType.STATUS,
                elapsed_time=action.metadata.get("elapsed_time", 0.0),
                credits_used=action.metadata.get("credits_used"),
                input_tokens=action.metadata.get("input_tokens"),
                output_tokens=action.metadata.get("output_tokens"),
                is_free_tier=action.metadata.get("is_free_tier", False)
            )
        
        # Build the status parts
        parts = []
        
        # Elapsed time - always shown
        # Requirements: 6.1 - Display a status footer with elapsed time
        parts.append(f"⏱ {action.elapsed_time:.1f}s")
        
        # Token counts - shown if available
        # Requirements: 6.3 - Display input and output token counts
        if action.input_tokens is not None or action.output_tokens is not None:
            input_count = action.input_tokens or 0
            output_count = action.output_tokens or 0
            total = input_count + output_count
            parts.append(f"📊 {total:,} tokens")
        
        # Credits or Free indicator
        # Requirements: 6.4 - Indicate "Free" instead of credit cost for free-tier
        # Requirements: 6.2 - Show the credit usage in the status footer
        if action.is_free_tier:
            parts.append("🆓 Free")
        elif action.credits_used is not None:
            parts.append(f"💰 ${action.credits_used:.4f}")
        
        # Create the footer content with horizontal rule styling
        status_text = " │ ".join(parts)
        
        # Use Rule for horizontal line styling
        from rich.rule import Rule
        from rich.console import Group
        
        # Create a group with horizontal rules and status text
        footer = Group(
            Rule(style="dim"),
            Text(f"  {status_text}  ", style="dim", justify="center"),
            Rule(style="dim")
        )
        
        return footer
    
    def _render_error_action(self, action: Action) -> RenderableType:
        """
        Render an ErrorAction as a card.
        
        Args:
            action: ErrorAction to render
            
        Returns:
            Rich renderable for the action
        """
        if not isinstance(action, ErrorAction):
            action = ErrorAction(
                type=ActionType.ERROR,
                message=action.metadata.get("message", "Error"),
                details=action.metadata.get("details")
            )
        
        lines = [action.message]
        if action.details:
            lines.append(f"\n{action.details}")
        
        content = Text("\n".join(lines), style="red")
        return self._create_card_panel(ActionType.ERROR, content)

    def _render_tool_call_action(self, action: Action) -> RenderableType:
        """
        Render a ToolCallAction showing tool invocation start.
        
        Displays the tool name and parameters when a tool invocation starts.
        
        Args:
            action: ToolCallAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 4.1 - Display tool name and parameters when invocation starts
        """
        if not isinstance(action, ToolCallAction):
            action = ToolCallAction(
                type=ActionType.TOOL_CALL,
                tool_name=action.metadata.get("tool_name", ""),
                parameters=action.metadata.get("parameters", {}),
                args_preview=action.metadata.get("args_preview", "")
            )
        
        content = Text()
        
        # Show args preview or formatted args
        if action.args_preview:
            content.append("  ")
            content.append(action.args_preview, style="dim")
        elif action.parameters:
            # Format args as key=value pairs
            for i, (key, value) in enumerate(action.parameters.items()):
                if i > 0:
                    content.append("\n")
                content.append("  ")
                content.append(f"{key}", style="cyan")
                content.append("=", style="dim")
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 60:
                    str_value = str_value[:57] + "..."
                content.append(str_value, style="dim")
        
        return self._create_card_panel(
            ActionType.TOOL_CALL,
            content,
            tool_name=action.tool_name
        )

    def _render_tool_result_action(self, action: Action) -> RenderableType:
        """
        Render a ToolResultAction showing tool execution result.
        
        Displays success/failure indicator with result preview.
        
        Args:
            action: ToolResultAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 4.2 - Display result/confirmation when tool completes
        """
        if not isinstance(action, ToolResultAction):
            action = ToolResultAction(
                type=ActionType.TOOL_RESULT,
                tool_name=action.metadata.get("tool_name", ""),
                result=action.metadata.get("result", ""),
                success=action.metadata.get("success", True),
                result_preview=action.metadata.get("result_preview", "")
            )
        
        content = Text()
        
        if action.success:
            # Show result preview if available
            preview = action.result_preview or action.result
            if preview and preview.strip():
                # Truncate long previews
                if len(preview) > 100:
                    preview = preview[:97] + "..."
                content.append("  ")
                content.append(preview, style="dim")
                content.append("\n")
            content.append(f"  {SUCCESS_INDICATOR} ", style="green bold")
            content.append("Success", style="green")
        else:
            content.append(f"  {FAILURE_INDICATOR} ", style="red bold")
            error_msg = action.result_preview or action.result or "Failed"
            content.append(error_msg, style="red")
        
        return self._create_card_panel(ActionType.TOOL_RESULT, content)

    def _render_tool_warning_action(self, action: Action) -> RenderableType:
        """
        Render a ToolWarningAction for skipped tool invocations.
        
        Displays a warning when the LLM describes an action without
        actually invoking the tool.
        
        Args:
            action: ToolWarningAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 4.4 - Warn user when tool invocation is skipped
        """
        if not isinstance(action, ToolWarningAction):
            action = ToolWarningAction(
                type=ActionType.TOOL_WARNING,
                message=action.metadata.get("message", ""),
                suggested_tool=action.metadata.get("suggested_tool", ""),
                detected_action=action.metadata.get("detected_action", "")
            )
        
        content = Text()
        
        # Show warning message
        content.append("  ⚠ ", style="yellow bold")
        content.append(action.message or "Action was described but not executed", style="yellow")
        
        # Show detected action if available
        if action.detected_action:
            content.append("\n  ")
            content.append("Detected: ", style="dim")
            content.append(action.detected_action, style="dim italic")
        
        # Show suggested tool if available
        if action.suggested_tool:
            content.append("\n  ")
            content.append("Suggested tool: ", style="dim")
            content.append(action.suggested_tool, style="cyan")
        
        return self._create_card_panel(ActionType.TOOL_WARNING, content)

    def _render_tool_progress_action(self, action: Action) -> RenderableType:
        """
        Render a ToolProgressAction showing multi-tool sequence progress.
        
        Displays progress indicator for multi-tool sequences.
        
        Args:
            action: ToolProgressAction to render
            
        Returns:
            Rich renderable for the action
            
        Requirements: 4.3 - Show progress for multi-tool sequences
        """
        if not isinstance(action, ToolProgressAction):
            action = ToolProgressAction(
                type=ActionType.TOOL_PROGRESS,
                current=action.metadata.get("current", 0),
                total=action.metadata.get("total", 0),
                tool_name=action.metadata.get("tool_name", "")
            )
        
        content = Text()
        
        # Show progress bar
        if action.total > 0:
            progress_pct = (action.current / action.total) * 100
            filled = int(progress_pct / 10)
            bar = "█" * filled + "░" * (10 - filled)
            content.append(f"  [{bar}] ", style="blue")
            content.append(f"{action.current}/{action.total}", style="bold blue")
        
        # Show current tool name
        if action.tool_name:
            content.append("\n  ")
            content.append("Current: ", style="dim")
            content.append(action.tool_name, style="cyan")
        
        return self._create_card_panel(
            ActionType.TOOL_PROGRESS,
            content,
            current=action.current,
            total=action.total
        )

    # -------------------------------------------------------------------------
    # Tool execution feedback methods (Requirements 4.1, 4.2, 4.3, 4.4)
    # -------------------------------------------------------------------------

    def render_batch_header(self, count: int) -> None:
        """
        Render a header for multiple tool calls.
        
        Displays "─── Executing N tool calls ───" header when multiple
        tools are being executed in a batch.
        
        Args:
            count: Number of tool calls being executed
            
        Requirements: 6.4 - Display batch header for multiple tool calls
        """
        if count <= 0:
            return
        
        header_text = f" Executing {count} tool call{'s' if count != 1 else ''} "
        self._console.print(
            Text(f"───{header_text}───", style="dim cyan")
        )

    def render_tool_call(
        self,
        tool_name: str,
        args: Optional[dict] = None,
        args_preview: str = ""
    ) -> None:
        """
        Render a tool call action card.
        
        Displays the tool name and parameters in a styled card format.
        
        Args:
            tool_name: Name of the tool being called
            args: Optional dictionary of tool arguments
            args_preview: Optional preview string of arguments
            
        Requirements: 6.1 - Display action card with tool name and parameters
        """
        content = Text()
        
        # Show args preview or formatted args
        if args_preview:
            content.append("  ")
            content.append(args_preview, style="dim")
        elif args:
            # Format args as key=value pairs
            for i, (key, value) in enumerate(args.items()):
                if i > 0:
                    content.append("\n")
                content.append("  ")
                content.append(f"{key}", style="cyan")
                content.append("=", style="dim")
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 60:
                    str_value = str_value[:57] + "..."
                content.append(str_value, style="dim")
        
        # Print tool call without border
        header = Text()
        header.append(f"🔧 {tool_name}", style="bold cyan")
        self._console.print(header)
        if content.plain.strip():
            self._console.print(content)

    def render_tool_success(
        self,
        result: str = "",
        max_preview: int = 100
    ) -> None:
        """
        Render a success indicator for tool execution.
        
        Displays "✓ Success" with optional result preview.
        
        Args:
            result: Optional result string to preview
            max_preview: Maximum characters to show in preview
            
        Requirements: 6.2 - Show "✓ Success" indicator with result preview
        """
        # Show truncated preview if result provided
        if result and result.strip():
            preview = result[:max_preview]
            if len(result) > max_preview:
                preview += "..."
            self._console.print(f"  [dim]{preview}[/dim]")
        
        # Show success indicator
        self._console.print(f"  [{self._theme.get_color('success')}]{SUCCESS_INDICATOR} Success[/{self._theme.get_color('success')}]")

    def render_tool_failure(self, error: str) -> None:
        """
        Render a failure indicator for tool execution.
        
        Displays "✗" indicator with error message.
        
        Args:
            error: Error message to display
            
        Requirements: 6.3 - Show "✗" indicator with error message
        """
        self._console.print(f"  [{self._theme.get_color('error')}]{FAILURE_INDICATOR} {error}[/{self._theme.get_color('error')}]")

    def render_tool_separator(self) -> None:
        """
        Render a separator between tool calls.
        
        Used to visually separate multiple tool calls in a batch.
        """
        self._console.print("[dim]───[/dim]")

    def render_tool_result(
        self,
        result: str,
        success: bool = True,
        max_preview: int = 100
    ) -> None:
        """
        Render a tool result with success/failure indicator.
        
        Convenience method that calls either render_tool_success or
        render_tool_failure based on the success parameter.
        
        Args:
            result: The result string to display
            success: Whether the tool call succeeded
            max_preview: Maximum characters to show in preview
            
        Requirements: 6.2, 6.3 - Success/failure indicators
        """
        if success:
            self.render_tool_success(result, max_preview)
        else:
            self.render_tool_failure(result)

    def render_tool_progress(
        self,
        current: int,
        total: int,
        tool_name: str = ""
    ) -> None:
        """
        Render progress indicator for multi-tool sequences.
        
        Displays a progress bar and current/total count for multi-tool
        execution sequences.
        
        Args:
            current: Current tool number (1-indexed)
            total: Total number of tools in sequence
            tool_name: Optional name of current tool
            
        Requirements: 4.3 - Show progress for multi-tool sequences
        """
        if total <= 1:
            return
        
        action = ToolProgressAction(
            type=ActionType.TOOL_PROGRESS,
            current=current,
            total=total,
            tool_name=tool_name
        )
        self.render(action)

    def render_tool_warning(
        self,
        message: str,
        suggested_tool: str = "",
        detected_action: str = ""
    ) -> None:
        """
        Render a warning for skipped tool invocation.
        
        Displays a warning when the LLM describes an action without
        actually invoking the appropriate tool.
        
        Args:
            message: Warning message to display
            suggested_tool: The tool that should have been invoked
            detected_action: The action the LLM described but didn't invoke
            
        Requirements: 4.4 - Warn user when tool invocation is skipped
        """
        action = ToolWarningAction(
            type=ActionType.TOOL_WARNING,
            message=message,
            suggested_tool=suggested_tool,
            detected_action=detected_action
        )
        self.render(action)

    def render_tool_execution_start(
        self,
        tool_name: str,
        parameters: dict = None,
        current: int = 0,
        total: int = 0
    ) -> None:
        """
        Render tool execution start with optional progress.
        
        Combines tool call display with progress indicator for
        multi-tool sequences.
        
        Args:
            tool_name: Name of the tool being called
            parameters: Dictionary of tool parameters
            current: Current tool number (1-indexed, 0 to skip progress)
            total: Total number of tools in sequence
            
        Requirements: 4.1, 4.3 - Tool name/params and progress display
        """
        # Show progress if in a multi-tool sequence
        if total > 1 and current > 0:
            self.render_tool_progress(current, total, tool_name)
        
        # Show tool call
        action = ToolCallAction(
            type=ActionType.TOOL_CALL,
            tool_name=tool_name,
            parameters=parameters or {}
        )
        self.render(action)

    def render_tool_execution_complete(
        self,
        tool_name: str,
        result: str,
        success: bool = True
    ) -> None:
        """
        Render tool execution completion with result.
        
        Displays the result/confirmation when a tool completes execution.
        
        Args:
            tool_name: Name of the tool that completed
            result: Result string from tool execution
            success: Whether the tool call succeeded
            
        Requirements: 4.2 - Display result/confirmation when tool completes
        """
        # Truncate result for preview
        preview = result[:100] + "..." if len(result) > 100 else result
        
        action = ToolResultAction(
            type=ActionType.TOOL_RESULT,
            tool_name=tool_name,
            result=result,
            success=success,
            result_preview=preview
        )
        self.render(action)
