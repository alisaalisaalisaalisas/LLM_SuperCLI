"""
Rich UI renderer for llm_supercli.
Handles rendering of messages, panels, markdown, code, and other UI elements.
"""
import re
import sys
from typing import Any, Generator, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .theme import ThemeManager, get_theme_manager
from .ascii import ASCIIArt
from .message_renderer import MessageRenderer
from .message_state import ToolCallRecord
from .content_parser import parse_think_tags, filter_tool_syntax
from .action_renderer import ActionRenderer
from ..constants import APP_NAME, APP_VERSION
from ..io_handlers import OutputDeduplicator, deduplicate_content, recover_corrupted_output


class RichRenderer:
    """
    Main renderer for all Rich UI components.
    Provides methods for rendering messages, panels, tables, code, and more.
    """
    
    def __init__(self, console: Optional[Console] = None) -> None:
        """
        Initialize the Rich renderer.
        
        Args:
            console: Optional Rich Console instance
        """
        self._theme_manager = get_theme_manager()
        self._console = console or Console(
            theme=self._theme_manager.get_rich_theme(),
            force_terminal=True,
            color_system="auto"
        )
        self._ascii_art = ASCIIArt()  # Auto-detect Unicode support
        self._live: Optional[Live] = None
        
        # Initialize MessageRenderer for streaming content
        # Requirements: 7.1, 7.2, 7.3 - Integration with existing architecture
        self._message_renderer = MessageRenderer(self._console, self._theme_manager)
        
        # Initialize ActionRenderer for action cards system
        # Requirements: 7.4, 8.3 - Integration with action cards
        self._action_renderer = ActionRenderer(self._console, self._theme_manager)
        
        # Initialize OutputDeduplicator for removing duplicate content from responses
        # Requirements: 5.2, 6.2 - Deduplicate reasoning and response content
        self._deduplicator = OutputDeduplicator()
    
    @property
    def console(self) -> Console:
        """Get the Rich console."""
        return self._console
    
    @property
    def theme(self) -> ThemeManager:
        """Get the theme manager."""
        return self._theme_manager
    
    @property
    def action_renderer(self) -> ActionRenderer:
        """Get the ActionRenderer for rendering action cards.
        
        Returns:
            ActionRenderer instance for external access
            
        Requirements: 7.4, 8.3 - Expose action renderer for CLI integration
        """
        return self._action_renderer
    
    def update_theme(self, theme_name: str) -> bool:
        """
        Update the active theme.
        
        Args:
            theme_name: Name of the theme to activate
            
        Returns:
            True if theme was updated, False if not found
        """
        if self._theme_manager.set_theme(theme_name):
            self._console = Console(
                theme=self._theme_manager.get_rich_theme(),
                force_terminal=True
            )
            return True
        return False
    
    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console with current theme."""
        self._console.print(*args, **kwargs)
    
    def print_banner(self, size: str = "small") -> None:
        """
        Print the application banner without bordered panel.
        
        Args:
            size: Banner size ('large', 'small', or 'mini')
            
        Requirements: 1.5 - Render banner without bordered panel
        """
        banner = self._ascii_art.get_banner(size)
        # Print banner text with styling directly (no Panel wrapper)
        self._console.print(Text(banner, style=self._theme_manager.get_style("prompt")))
        # Print app name and version below banner
        self._console.print(f"[bold]{APP_NAME}[/bold] [dim]v{APP_VERSION}[/dim]")
        self._console.print()  # Add spacing
    
    def print_welcome(self) -> None:
        """Print welcome message with cyberpunk splash screen."""
        from .splash import print_splash
        print_splash(self._console)
    
    def print_message(
        self,
        content: str,
        role: str = "assistant",
        show_timestamp: bool = False,
        timestamp: Optional[str] = None
    ) -> None:
        """
        Print a chat message with role-specific styling.
        
        Renders messages in distinct panels with appropriate icons and borders:
        - User messages: 👤 icon, dim border, plain text
        - Assistant messages: 🤖 icon, cyan border, markdown rendering
        - System messages: ⚙️ icon, dim italic style
        
        Args:
            content: Message content
            role: Message role ('user', 'assistant', 'system')
            show_timestamp: Whether to show timestamp
            timestamp: Optional timestamp string
            
        Requirements: 4.1, 4.2, 4.3, 4.4 - Message panels with role icons
        Requirements: 5.2, 6.2 - Deduplicate content before rendering
        Requirements: 9.2, 9.3 - Responsive layout
        """
        from .layout_manager import get_layout_manager
        layout = get_layout_manager()
        
        # Apply deduplication to assistant messages before rendering
        # Requirements: 5.2, 6.2 - Deduplicate reasoning and response content
        if role == "assistant":
            content = self._deduplicator.deduplicate(content)
        
        # Role-specific icons and styles
        icon_map = {
            "user": "👤",
            "assistant": "🤖",
            "system": "⚙️",
        }
        
        title_style_map = {
            "user": "dim",
            "assistant": "bold cyan",
            "system": "dim italic",
        }
        
        icon = icon_map.get(role, "")
        title_style = title_style_map.get(role, "dim")
        
        # Build header with icon and role name
        header = f"{icon} {role.capitalize()}"
        if show_timestamp and timestamp:
            header += f" [{timestamp}]"
        
        # Print header without border
        self._console.print(f"[{title_style}]{header}[/{title_style}]")
        
        # Render content based on role (markdown for assistant)
        if role == "assistant":
            self._console.print(Markdown(content))
        else:
            self._console.print(Text(content))
        
        # Add spacing
        self._console.print()
    
    def print_reasoning(self, content: str) -> None:
        """
        Print reasoning/thinking content in a styled yellow panel.
        
        Displays the model's thinking process in a distinct yellow-bordered
        panel with the 💭 Reasoning header.
        
        Args:
            content: Reasoning content to display
            
        Requirements: 5.1 - Yellow-bordered panel with "💭 Reasoning" header
        Requirements: 5.2, 6.2 - Deduplicate reasoning content
        Requirements: 9.2, 9.3 - Responsive layout
        """
        if not content.strip():
            return
        
        # Apply deduplication to reasoning content
        # Requirements: 5.2, 6.2 - Deduplicate reasoning content
        content = self._deduplicator.deduplicate(content)
        
        if not content.strip():
            return
        
        from .layout_manager import get_layout_manager
        layout = get_layout_manager()
        
        # Get responsive padding from layout manager
        padding = layout.get_panel_padding()
        
        # Determine panel width for wide terminals
        panel_width = None
        if layout.is_wide_terminal():
            panel_width = layout.get_panel_width()
        
        # Print reasoning without border
        self._console.print(Text("💭 Reasoning", style="yellow"))
        self._console.print(Text(content, style="dim italic"))
        self._console.print()
    
    def print_markdown(self, content: str) -> None:
        """
        Print markdown content.
        
        Args:
            content: Markdown string
        """
        md = Markdown(content)
        self._console.print(md)
    
    def print_code(
        self,
        code: str,
        language: str = "python",
        line_numbers: bool = True,
        title: Optional[str] = None
    ) -> None:
        """
        Print syntax-highlighted code without bordered panel.
        
        Args:
            code: Code string
            language: Programming language
            line_numbers: Whether to show line numbers
            title: Optional title for the code block
            
        Requirements: 1.6 - Render code without bordered panel
        """
        # Print title if provided (without border)
        if title:
            self._console.print(f"[{self._theme_manager.get_style('code_border')}]─── {title} ───[/]")
        
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=line_numbers,
            word_wrap=True
        )
        
        self._console.print(syntax)
    
    def print_error(self, message: str, title: str = "Error") -> None:
        """
        Print an error message without bordered panel.
        
        Args:
            message: Error message
            title: Error title
            
        Requirements: 1.1 - Render error with icon and styled text without bordered panel
        """
        icon = self._ascii_art.get_icon("error")
        # Print header with icon and title
        self._console.print(f"[bold red]{icon} {title}[/bold red]")
        # Print message with error styling
        self._console.print(Text(message, style=self._theme_manager.get_style("error_message")))
        self._console.print()  # Add spacing
    
    def print_warning(self, message: str, title: str = "Warning") -> None:
        """
        Print a warning message without bordered panel.
        
        Args:
            message: Warning message
            title: Warning title
            
        Requirements: 1.2 - Render warning with icon and styled text without bordered panel
        """
        icon = self._ascii_art.get_icon("warning")
        # Print header with icon and title
        self._console.print(f"[bold yellow]{icon} {title}[/bold yellow]")
        # Print message with warning styling
        self._console.print(Text(message, style=self._theme_manager.get_style("warning_message")))
        self._console.print()  # Add spacing
    
    def print_success(self, message: str, title: str = "Success") -> None:
        """
        Print a success message without bordered panel.
        
        Args:
            message: Success message
            title: Success title
            
        Requirements: 1.4 - Render success with icon and styled text without bordered panel
        """
        icon = self._ascii_art.get_icon("check")  # Use ✓ icon per requirements
        # Print header with icon and title
        self._console.print(f"[bold green]{icon} {title}[/bold green]")
        # Print message with success styling
        self._console.print(Text(message, style="bold green"))
        self._console.print()  # Add spacing
    
    def print_info(self, message: str, title: str = "Info") -> None:
        """
        Print an info message without bordered panel.
        
        Args:
            message: Info message
            title: Info title
            
        Requirements: 1.3 - Render info with icon and styled text without bordered panel
        """
        icon = self._ascii_art.get_icon("info")
        # Print header with icon and title
        self._console.print(f"[bold blue]{icon} {title}[/bold blue]")
        # Print message with info styling
        self._console.print(Text(message, style=self._theme_manager.get_style("info_message")))
        self._console.print()  # Add spacing
    
    def print_table(
        self,
        data: list[dict],
        title: Optional[str] = None,
        columns: Optional[list[str]] = None
    ) -> None:
        """
        Print data as a table.
        
        Args:
            data: List of dictionaries with data
            title: Optional table title
            columns: Optional list of column names (uses dict keys if not provided)
        """
        if not data:
            self._console.print("[dim]No data to display[/dim]")
            return
        
        if columns is None:
            columns = list(data[0].keys())
        
        table = Table(
            title=title,
            border_style=self._theme_manager.get_color("primary")
        )
        
        for col in columns:
            table.add_column(col, style=self._theme_manager.get_color("secondary"))
        
        for row in data:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        
        self._console.print(table)
    
    def print_tree(self, data: dict, title: str = "Tree") -> None:
        """
        Print hierarchical data as a tree.
        
        Args:
            data: Nested dictionary representing tree structure
            title: Tree root title
        """
        tree = Tree(f"[bold]{title}[/bold]")
        
        def add_branches(parent: Tree, items: dict) -> None:
            for key, value in items.items():
                if isinstance(value, dict):
                    branch = parent.add(f"[bold]{key}[/bold]")
                    add_branches(branch, value)
                else:
                    parent.add(f"{key}: {value}")
        
        add_branches(tree, data)
        self._console.print(tree)
    
    def print_status(
        self,
        provider: str,
        model: str,
        tokens: Optional[tuple[int, int]] = None,
        cost: Optional[float] = None
    ) -> None:
        """
        Print current status bar.
        
        Args:
            provider: Current provider name
            model: Current model name
            tokens: Optional (input, output) token counts
            cost: Optional cost value
        """
        # OAuth-based free tier providers
        free_providers = ["gemini", "qwen"]
        is_free = provider.lower() in free_providers
        
        parts = [
            f"[bold cyan]{provider.title()}[/]",
            f"[dim]/[/dim]",
            f"[cyan]{model}[/]",
        ]
        
        if tokens:
            input_t, output_t = tokens
            total = input_t + output_t
            parts.append(f"[dim]|[/dim] [dim]{total} tokens[/]")
        
        if is_free:
            parts.append(f"[dim]|[/dim] [green]Free[/]")
        elif cost is not None and cost > 0:
            parts.append(f"[dim]|[/dim] [green]${cost:.4f}[/]")
        
        self._console.print(" ".join(parts))
    
    def start_spinner(self, message: str = "Thinking...", show_cancel_hint: bool = True) -> Live:
        """
        Start a spinner animation with optional cancel hint.
        
        Displays "Thinking..." with spinner animation and "Ctrl+X to cancel"
        hint aligned to the right side of the terminal.
        
        Args:
            message: Message to display with spinner
            show_cancel_hint: Whether to show "Ctrl+X to cancel" hint
            
        Returns:
            Live context for updating/stopping
            
        Requirements: 7.1 - Display "Thinking..." with spinner animation
        Requirements: 7.2 - Show "Ctrl+X to cancel" hint aligned right
        """
        # Create spinner with message
        spinner = Progress(
            SpinnerColumn(style=self._theme_manager.get_style("spinner")),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )
        spinner.add_task(message, total=None)
        
        # Create content with cancel hint if requested
        if show_cancel_hint:
            # Get terminal width for right alignment
            terminal_width = self._console.width or 80
            
            # Create a table layout for spinner + cancel hint
            from rich.table import Table
            layout = Table.grid(expand=True)
            layout.add_column(ratio=1)  # Spinner column (expands)
            layout.add_column(justify="right")  # Cancel hint column (right-aligned)
            layout.add_row(spinner, Text("Ctrl+X to cancel", style="dim"))
            
            self._live = Live(layout, console=self._console, refresh_per_second=10, transient=True)
        else:
            self._live = Live(spinner, console=self._console, refresh_per_second=10, transient=True)
        
        self._live.start()
        return self._live
    
    def stop_spinner(self, transition_to_content: bool = False) -> None:
        """
        Stop the current spinner with smooth transition.
        
        Stops the animated spinner. When transition_to_content is True,
        the spinner is removed cleanly to allow live content to take over.
        
        Args:
            transition_to_content: If True, prepare for live content transition
            
        Requirements: 7.3 - Replace spinner with live content smoothly
        """
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass  # Ignore errors during stop
            finally:
                self._live = None

    def start_thinking(self, message: str = "Thinking...") -> Live:
        """
        Start thinking indicator with spinner and cancel hint.
        
        Convenience method that starts a spinner with the "Ctrl+X to cancel"
        hint displayed. This is the preferred method for showing the thinking
        state during API calls.
        
        Args:
            message: Message to display (default: "Thinking...")
            
        Returns:
            Live context for updating/stopping
            
        Requirements: 7.1 - Display "Thinking..." with spinner animation
        Requirements: 7.2 - Show "Ctrl+X to cancel" hint aligned right
        """
        return self.start_spinner(message, show_cancel_hint=True)

    def stop_thinking(self, transition_to_stream: bool = True) -> None:
        """
        Stop thinking indicator and prepare for content streaming.
        
        Stops the thinking spinner and prepares for smooth transition
        to live streaming content.
        
        Args:
            transition_to_stream: If True, prepare for streaming transition
            
        Requirements: 7.3 - Replace spinner with live content smoothly
        """
        self.stop_spinner(transition_to_content=transition_to_stream)
    
    def start_live_reasoning(self) -> None:
        """Start live display for streaming reasoning.
        
        Delegates to MessageRenderer.start_message() while maintaining
        backward compatibility with existing interface.
        
        Requirements: 7.1, 7.2 - Maintain existing public interface
        Requirements: 1.1 - Deduplication now handled by MessageRenderer.buffer
        """
        # Reset MessageRenderer for new message
        if self._message_renderer.phase.value not in ("idle", "complete", "error"):
            self._message_renderer.reset()
        elif self._message_renderer.phase.value in ("complete", "error"):
            self._message_renderer.reset()
        
        # Initialize legacy buffers for backward compatibility
        # Note: _raw_response_buffer removed - deduplication handled by MessageRenderer.buffer
        self._reasoning_buffer = ""
        self._response_buffer = ""
        self._in_thinking = False
        
        # Delegate to MessageRenderer
        self._message_renderer.start_message()
    
    def update_live_stream(self, chunk: str) -> None:
        """Update live stream with new chunk, handling <think> tags and filtering tool calls.
        
        Delegates to MessageRenderer.stream_content() which handles parsing
        of think tags and routing to appropriate stream methods.
        
        Requirements: 7.1, 7.2 - Maintain existing public interface
        Requirements: 1.2, 2.1, 2.2 - Deduplication handled by MessageRenderer
        """
        if not chunk:
            return
        
        # Ensure legacy buffers exist for backward compatibility
        if not hasattr(self, '_reasoning_buffer'):
            self._reasoning_buffer = ""
        if not hasattr(self, '_response_buffer'):
            self._response_buffer = ""
        if not hasattr(self, '_in_thinking'):
            self._in_thinking = False
        
        # Delegate to MessageRenderer for streaming display
        # MessageRenderer handles think tag parsing, content routing, and deduplication
        # Note: We no longer accumulate raw chunks here - MessageRenderer.buffer handles deduplication
        self._message_renderer.stream_content(chunk)
        
        # Sync legacy buffers from MessageRenderer for backward compatibility
        self._reasoning_buffer = self._message_renderer.buffer.reasoning
        self._response_buffer = self._message_renderer.buffer.response
        self._in_thinking = self._message_renderer._in_thinking
    
    def stop_live_stream(self) -> tuple:
        """
        Stop live stream and return buffers.
        
        Delegates to MessageRenderer.finalize() while maintaining
        backward compatibility with existing interface.
        
        Requirements: 7.1, 7.2 - Maintain existing public interface
        Requirements: 1.1, 1.4, 2.3 - Return deduplicated content with tool syntax preserved
        Requirements: 5.2, 6.2 - Deduplicate reasoning and response content
        Requirements: 6.5 - Detect and recover from corrupted/garbled output
        
        Returns:
            Tuple of (response_content, reasoning_content)
            Note: response_content includes tool calls for parsing by CLI (deduplicated)
        """
        # Finalize via MessageRenderer
        filtered_response, reasoning = self._message_renderer.finalize()
        
        # Use deduplicated response from MessageRenderer.buffer
        # This preserves tool syntax for CLI parsing while ensuring no duplicates
        deduplicated_response = self._message_renderer.buffer.response
        
        # If reasoning contains what looks like the actual response (markdown headers,
        # structured content), move it to response and keep only the thinking part
        if reasoning and not deduplicated_response:
            # Find where the actual response starts (markdown headers, "Based on", etc.)
            response_markers = [
                r'^#{1,3}\s+',  # Markdown headers
                r'^Based on',   # Common response starter
                r'^\*\*[A-Z]',  # Bold headers
                r'^Here\'s',    # Common response starter
            ]
            
            lines = reasoning.split('\n')
            response_start_idx = None
            
            for i, line in enumerate(lines):
                for marker in response_markers:
                    if re.match(marker, line.strip()):
                        response_start_idx = i
                        break
                if response_start_idx is not None:
                    break
            
            if response_start_idx is not None:
                # Split: reasoning is before, response is from marker onwards
                reasoning_lines = lines[:response_start_idx]
                response_lines = lines[response_start_idx:]
                reasoning = '\n'.join(reasoning_lines).strip()
                deduplicated_response = '\n'.join(response_lines).strip()
        
        # Apply paragraph-level deduplication to remove duplicate sections
        # Requirements: 5.2, 6.2 - Deduplicate reasoning and response content
        deduplicated_response = self._deduplicator.deduplicate(deduplicated_response.strip())
        reasoning = self._deduplicator.deduplicate(reasoning.strip())
        
        # Check for and recover from corrupted output
        # Requirements: 6.5 - Detect and recover from corrupted/garbled output
        deduplicated_response, response_warning = recover_corrupted_output(deduplicated_response)
        reasoning, reasoning_warning = recover_corrupted_output(reasoning)
        
        # Display warnings if content was recovered
        if response_warning:
            self._console.print(f"[yellow]⚠ {response_warning}[/yellow]")
        if reasoning_warning:
            self._console.print(f"[yellow]⚠ {reasoning_warning}[/yellow]")
        
        return deduplicated_response, reasoning
    
    def was_response_printed(self) -> bool:
        """Check if the response was already printed during streaming finalization.
        
        Returns:
            True if the response panel was already printed, False otherwise
        """
        return self._message_renderer.response_already_printed
    
    def was_reasoning_printed(self) -> bool:
        """Check if the reasoning was already printed during streaming finalization.
        
        Returns:
            True if the reasoning panel was already printed, False otherwise
        """
        return self._message_renderer.reasoning_already_printed
    
    def stream_response(self, chunks: Generator[str, None, None]) -> str:
        """
        Stream a response with live updates.
        
        Args:
            chunks: Generator yielding response chunks
            
        Returns:
            Complete response string
        """
        full_response = ""
        
        with Live(console=self._console, refresh_per_second=10) as live:
            for chunk in chunks:
                full_response += chunk
                live.update(Markdown(full_response))
        
        return full_response
    
    def progress_bar(
        self,
        total: int,
        description: str = "Processing..."
    ) -> Progress:
        """
        Create a progress bar.
        
        Args:
            total: Total number of steps
            description: Progress description
            
        Returns:
            Progress context manager
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self._console
        )
        return progress
    
    def clear(self) -> None:
        """Clear the console."""
        self._console.clear()
    
    def rule(self, title: str = "", style: str = "dim") -> None:
        """
        Print a horizontal rule.
        
        Args:
            title: Optional title for the rule
            style: Style for the rule
        """
        self._console.rule(title, style=style)
    
    def prompt_confirm(self, message: str, default: bool = False) -> bool:
        """
        Show a confirmation prompt.
        
        Args:
            message: Confirmation message
            default: Default value
            
        Returns:
            User's choice
        """
        from rich.prompt import Confirm
        return Confirm.ask(message, default=default, console=self._console)
    
    def print_commands_help(self, commands: list[dict]) -> None:
        """
        Print help for available commands.
        
        Args:
            commands: List of command info dicts with 'name' and 'description'
        """
        table = Table(
            title="Available Commands",
            border_style=self._theme_manager.get_color("primary"),
            show_header=True,
            header_style="bold"
        )
        
        table.add_column("Command", style=self._theme_manager.get_style("command"))
        table.add_column("Description", style="dim")
        
        for cmd in sorted(commands, key=lambda x: x['name']):
            table.add_row(f"/{cmd['name']}", cmd['description'])
        
        self._console.print(table)
    
    def print_tool_call(
        self,
        tool_name: str,
        args_preview: str = "",
        icon: str = "🔧"
    ) -> None:
        """
        Print a tool call header in a styled format.
        
        Args:
            tool_name: Name of the tool being called
            args_preview: Preview of arguments (e.g., path or command)
            icon: Icon to display for the tool
        """
        if args_preview:
            self._console.print(f"[cyan]{icon} {tool_name}[/cyan]: {args_preview}")
        else:
            self._console.print(f"[cyan]{icon} {tool_name}[/cyan]")
    
    def print_tool_result(
        self,
        result: str,
        success: bool = True,
        max_preview: int = 100
    ) -> None:
        """
        Print a tool result with success/failure indicator.
        
        Args:
            result: The result string to display
            success: Whether the tool call succeeded
            max_preview: Maximum characters to show in preview
        """
        if success:
            # Show truncated preview
            preview = result[:max_preview] + "..." if len(result) > max_preview else result
            if preview.strip():
                self._console.print(f"[dim]{preview}[/dim]")
            self._console.print("[green]✓ Success[/green]")
        else:
            self._console.print(f"[red]✗ {result}[/red]")
    
    def print_tool_section_header(self, num_calls: int) -> None:
        """
        Print a header for multiple tool calls.
        
        Args:
            num_calls: Number of tool calls being executed
        """
        self._console.print(f"[dim]─── Executing {num_calls} tool calls ───[/dim]")
    
    def print_tool_separator(self) -> None:
        """Print a separator between tool calls."""
        self._console.print("[dim]───[/dim]")

    def print_tool_warning(
        self,
        message: str,
        suggested_tool: str = "",
        detected_action: str = ""
    ) -> None:
        """
        Print a warning for skipped tool invocation.
        
        Displays a warning when the LLM describes an action without
        actually invoking the appropriate tool.
        
        Args:
            message: Warning message to display
            suggested_tool: The tool that should have been invoked
            detected_action: The action the LLM described but didn't invoke
            
        Requirements: 4.4 - Warn user when tool invocation is skipped
        """
        self._console.print()
        self._console.print("[yellow]⚠ Warning: Action not executed[/yellow]")
        self._console.print(f"  [yellow]{message}[/yellow]")
        
        if detected_action:
            self._console.print(f"  [dim]Detected: {detected_action}[/dim]")
        
        if suggested_tool:
            self._console.print(f"  [dim]Suggested tool: [cyan]{suggested_tool}[/cyan][/dim]")
        
        self._console.print()

    def print_tool_progress(
        self,
        current: int,
        total: int,
        tool_name: str = ""
    ) -> None:
        """
        Print progress indicator for multi-tool sequences.
        
        Displays a progress bar and current/total count.
        
        Args:
            current: Current tool number (1-indexed)
            total: Total number of tools in sequence
            tool_name: Optional name of current tool
            
        Requirements: 4.3 - Show progress for multi-tool sequences
        """
        if total <= 1:
            return
        
        progress_pct = (current / total) * 100
        filled = int(progress_pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        progress_text = f"[{bar}] {current}/{total}"
        if tool_name:
            progress_text += f" - {tool_name}"
        
        self._console.print(f"[blue]{progress_text}[/blue]")

    def print_file_creation_summary(
        self,
        files: list[str],
        directories: list[str] = None
    ) -> None:
        """
        Print a summary of created files and directories.
        
        Displays a confirmation message showing which files were created
        and their locations.
        
        Args:
            files: List of file paths that were created
            directories: Optional list of directory paths that were created
            
        Requirements: 2.4 - Confirm which files were created and their locations
        """
        directories = directories or []
        
        if not files and not directories:
            return
        
        self._console.print()
        
        total = len(files) + len(directories)
        self._console.print(f"[green]✓ Created {total} item(s):[/green]")
        
        # Show directories first
        for dir_path in directories:
            self._console.print(f"  [cyan]📁 {dir_path}[/cyan]")
        
        # Show files
        for file_path in files:
            self._console.print(f"  [green]📄 {file_path}[/green]")
        
        self._console.print()

    def print_write_error_with_remediation(
        self,
        error_message: str,
        file_path: str,
        remediation_steps: list[str]
    ) -> None:
        """
        Print a write file error with remediation suggestions.
        
        Displays the error message and a list of suggested steps
        to resolve the issue.
        
        Args:
            error_message: The error message to display
            file_path: The file path that failed
            remediation_steps: List of suggested remediation steps
            
        Requirements: 2.5 - Report write_file errors and suggest remediation
        """
        self._console.print()
        self._console.print(f"[red]✗ Failed to write '{file_path}'[/red]")
        self._console.print(f"  [red]{error_message}[/red]")
        
        if remediation_steps:
            self._console.print()
            self._console.print("[yellow]Suggested remediation steps:[/yellow]")
            for i, step in enumerate(remediation_steps, 1):
                self._console.print(f"  [dim]{i}.[/dim] {step}")
        
        self._console.print()

    def print_empty_directory_message(self, path: str) -> None:
        """
        Print an informative message for an empty directory.
        
        Displays a message explaining the directory is empty and
        suggests possible actions.
        
        Args:
            path: The path to the empty directory
            
        Requirements: 1.4 - Report empty directory rather than assuming files exist
        """
        from ..io_handlers import handle_empty_directory
        
        message = handle_empty_directory(path)
        self._console.print()
        self._console.print("[yellow]📁 Empty Directory[/yellow]")
        for line in message.split('\n'):
            if line.strip():
                self._console.print(f"  {line}")
        self._console.print()

    def print_corrupted_output_warning(self, warning: str, issues: list[str] = None) -> None:
        """
        Print a warning about corrupted output that was recovered.
        
        Displays a warning message and optionally lists the issues
        that were detected and fixed.
        
        Args:
            warning: The warning message
            issues: Optional list of specific issues detected
            
        Requirements: 6.5 - Detect and recover from corrupted/garbled output
        """
        self._console.print()
        self._console.print(f"[yellow]⚠ Output Recovery[/yellow]")
        self._console.print(f"  [yellow]{warning}[/yellow]")
        
        if issues:
            self._console.print()
            self._console.print("  [dim]Issues detected:[/dim]")
            for issue in issues:
                self._console.print(f"    [dim]• {issue}[/dim]")
        
        self._console.print()


_renderer: Optional[RichRenderer] = None


def get_renderer() -> RichRenderer:
    """Get the global renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = RichRenderer()
    return _renderer
