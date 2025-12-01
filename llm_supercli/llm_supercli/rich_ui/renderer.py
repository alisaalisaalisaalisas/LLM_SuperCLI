"""
Rich UI renderer for llm_supercli.
Handles rendering of messages, panels, markdown, code, and other UI elements.
"""
import sys
from typing import Any, Generator, Optional

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .theme import ThemeManager, get_theme_manager
from .ascii import ASCIIArt
from ..constants import APP_NAME, APP_VERSION


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
    
    @property
    def console(self) -> Console:
        """Get the Rich console."""
        return self._console
    
    @property
    def theme(self) -> ThemeManager:
        """Get the theme manager."""
        return self._theme_manager
    
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
        Print the application banner.
        
        Args:
            size: Banner size ('large', 'small', or 'mini')
        """
        banner = self._ascii_art.get_banner(size)
        self._console.print(
            Panel(
                Text(banner, style=self._theme_manager.get_style("prompt")),
                title=f"[bold]{APP_NAME}[/bold]",
                subtitle=f"[dim]v{APP_VERSION}[/dim]",
                border_style=self._theme_manager.get_color("primary")
            )
        )
    
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
        Print a chat message.
        
        Args:
            content: Message content
            role: Message role ('user', 'assistant', 'system')
            show_timestamp: Whether to show timestamp
            timestamp: Optional timestamp string
        """
        style_map = {
            "user": "user",
            "assistant": "assistant",
            "system": "system",
        }
        
        icon_map = {
            "user": self._ascii_art.get_icon("user"),
            "assistant": self._ascii_art.get_icon("robot"),
            "system": self._ascii_art.get_icon("system"),
        }
        
        style = self._theme_manager.get_style(f"{style_map.get(role, 'assistant')}_message")
        icon = icon_map.get(role, "")
        
        header = f"{icon} {role.capitalize()}"
        if show_timestamp and timestamp:
            header += f" [{timestamp}]"
        
        panel = Panel(
            Markdown(content) if role == "assistant" else Text(content),
            title=f"[{style}]{header}[/{style}]",
            title_align="left",
            border_style=self._theme_manager.get_color("primary") if role == "assistant" else "dim",
            padding=(0, 1)
        )
        self._console.print(panel)
    
    def print_reasoning(self, content: str) -> None:
        """
        Print reasoning/thinking content in a styled box.
        
        Args:
            content: Reasoning content to display
        """
        if not content.strip():
            return
            
        panel = Panel(
            Text(content, style="dim italic"),
            title="[yellow]💭 Reasoning[/yellow]",
            title_align="left",
            border_style="yellow",
            padding=(0, 1)
        )
        self._console.print(panel)
    
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
        Print syntax-highlighted code.
        
        Args:
            code: Code string
            language: Programming language
            line_numbers: Whether to show line numbers
            title: Optional title for the code block
        """
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=line_numbers,
            word_wrap=True
        )
        
        if title:
            panel = Panel(
                syntax,
                title=title,
                border_style=self._theme_manager.get_style("code_border")
            )
            self._console.print(panel)
        else:
            self._console.print(syntax)
    
    def print_error(self, message: str, title: str = "Error") -> None:
        """
        Print an error message.
        
        Args:
            message: Error message
            title: Error title
        """
        icon = self._ascii_art.get_icon("error")
        self._console.print(
            Panel(
                Text(message, style=self._theme_manager.get_style("error_message")),
                title=f"{icon} {title}",
                border_style="red"
            )
        )
    
    def print_warning(self, message: str, title: str = "Warning") -> None:
        """
        Print a warning message.
        
        Args:
            message: Warning message
            title: Warning title
        """
        icon = self._ascii_art.get_icon("warning")
        self._console.print(
            Panel(
                Text(message, style=self._theme_manager.get_style("warning_message")),
                title=f"{icon} {title}",
                border_style="yellow"
            )
        )
    
    def print_success(self, message: str, title: str = "Success") -> None:
        """
        Print a success message.
        
        Args:
            message: Success message
            title: Success title
        """
        icon = self._ascii_art.get_icon("success")
        self._console.print(
            Panel(
                Text(message, style="bold green"),
                title=f"{icon} {title}",
                border_style="green"
            )
        )
    
    def print_info(self, message: str, title: str = "Info") -> None:
        """
        Print an info message.
        
        Args:
            message: Info message
            title: Info title
        """
        icon = self._ascii_art.get_icon("info")
        self._console.print(
            Panel(
                Text(message, style=self._theme_manager.get_style("info_message")),
                title=f"{icon} {title}",
                border_style="blue"
            )
        )
    
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
    
    def start_spinner(self, message: str = "Thinking...") -> Live:
        """
        Start a spinner animation.
        
        Args:
            message: Message to display with spinner
            
        Returns:
            Live context for updating/stopping
        """
        spinner = Progress(
            SpinnerColumn(style=self._theme_manager.get_style("spinner")),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )
        spinner.add_task(message, total=None)
        
        self._live = Live(spinner, console=self._console, refresh_per_second=10)
        self._live.start()
        return self._live
    
    def stop_spinner(self) -> None:
        """Stop the current spinner."""
        if self._live:
            self._live.stop()
            self._live = None
    
    def start_live_reasoning(self) -> None:
        """Start live display for streaming reasoning."""
        self._reasoning_buffer = ""
        self._response_buffer = ""  # Display buffer (filtered)
        self._raw_response_buffer = ""  # Raw buffer (includes tool calls for CLI parsing)
        self._in_thinking = False
        self._first_chunk = True
        self._tag_buffer = ""  # Buffer for detecting tags
        self._in_tool_tag = False  # Track if inside a tool call tag
        self._tool_tag_buffer = ""  # Buffer for tool tag content
        self._in_python_tool = False  # Track if inside Python-style tool call
        self._python_tool_buffer = ""  # Buffer for Python tool call
        self._paren_depth = 0  # Track parenthesis depth for Python tool calls
        self._live = Live(
            Text("⠋ Thinking...", style="dim italic"),
            console=self._console,
            refresh_per_second=15,  # Faster refresh for smoother streaming
            vertical_overflow="visible"
        )
        self._live.start()
    
    def update_live_stream(self, chunk: str) -> None:
        """Update live stream with new chunk, handling <think> tags and filtering tool calls."""
        if not self._live:
            return
        
        # Initialize tracking if not present
        if not hasattr(self, '_in_tool_tag'):
            self._in_tool_tag = False
            self._tool_tag_buffer = ""
        if not hasattr(self, '_in_python_tool'):
            self._in_python_tool = False
            self._python_tool_buffer = ""
            self._paren_depth = 0
        if not hasattr(self, '_raw_response_buffer'):
            self._raw_response_buffer = ""
        
        # Always add chunk to raw buffer (for CLI tool parsing)
        self._raw_response_buffer += chunk
        
        # Tool names to filter from display
        tool_names = ['read_file', 'write_file', 'list_directory', 'create_directory', 'run_command', 'get_current_directory']
        
        # Process chunk character by character with tag detection
        i = 0
        while i < len(chunk):
            char = chunk[i]
            
            # If we're inside a Python-style tool call, track parentheses
            if self._in_python_tool:
                self._python_tool_buffer += char
                if char == '(':
                    self._paren_depth += 1
                elif char == ')':
                    self._paren_depth -= 1
                    if self._paren_depth == 0:
                        # Tool call complete - discard it
                        self._in_python_tool = False
                        self._python_tool_buffer = ""
                i += 1
                continue
            
            # Check for tag start
            if char == '<':
                self._tag_buffer = char
                i += 1
                continue
            
            # If we're building a tag
            if self._tag_buffer:
                self._tag_buffer += char
                
                # Check for complete think opening tag
                if self._tag_buffer == "<think>":
                    self._in_thinking = True
                    self._tag_buffer = ""
                # Check for complete think closing tag
                elif self._tag_buffer == "</think>":
                    self._in_thinking = False
                    self._tag_buffer = ""
                # Check for tool call tag (e.g., <read_file(, <create_directory(, etc.)
                elif '(' in self._tag_buffer and self._tag_buffer.startswith('<'):
                    self._in_tool_tag = True
                    self._tool_tag_buffer = self._tag_buffer
                    self._tag_buffer = ""
                # If tag buffer gets too long, flush it
                elif len(self._tag_buffer) > 50:
                    if self._in_thinking:
                        self._reasoning_buffer += self._tag_buffer
                    else:
                        self._response_buffer += self._tag_buffer
                    self._tag_buffer = ""
                
                i += 1
                continue
            
            # If we're inside an XML tool tag
            if self._in_tool_tag:
                self._tool_tag_buffer += char
                if char == '>' or any(self._tool_tag_buffer.endswith(f'</{t}>') for t in tool_names):
                    self._in_tool_tag = False
                    self._tool_tag_buffer = ""
                i += 1
                continue
            
            # Check for Python-style tool call start
            # Look back in response buffer to see if we're starting a tool call
            if char == '(' and not self._in_thinking:
                # Check if the buffer ends with a tool name
                for tool in tool_names:
                    if self._response_buffer.rstrip().endswith(tool):
                        # Remove the tool name from buffer and start filtering
                        self._response_buffer = self._response_buffer.rstrip()[:-len(tool)].rstrip()
                        self._in_python_tool = True
                        self._python_tool_buffer = tool + char
                        self._paren_depth = 1
                        break
                else:
                    # Not a tool call, add normally
                    if self._in_thinking:
                        self._reasoning_buffer += char
                    else:
                        self._response_buffer += char
                i += 1
                continue
            
            # Regular character - add to appropriate buffer
            if self._in_thinking:
                self._reasoning_buffer += char
            else:
                self._response_buffer += char
            i += 1
        
        # Clean tool syntax from display buffers
        import re
        display_response = self._response_buffer
        # Remove XML-style tool patterns
        display_response = re.sub(r'<\w+\([^)]*\)>[^<]*</\w+>', '', display_response)
        display_response = re.sub(r'<\w+\([^)]*\)>', '', display_response)
        # Remove Python-style tool calls (multiline support with DOTALL)
        tool_names = r'(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)'
        # Match tool_name(...) including multiline content
        display_response = re.sub(tool_names + r'\s*\([^)]*\)', '', display_response, flags=re.DOTALL)
        # Also handle cases where content has nested parens or spans multiple lines
        display_response = re.sub(tool_names + r'\s*\(.*?\)', '', display_response, flags=re.DOTALL)
        display_response = display_response.strip()
        
        # Clean tool calls and code blocks from reasoning for display
        import re
        display_reasoning = self._reasoning_buffer
        # Remove tool calls from reasoning display
        tool_pattern = r'(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)\s*\([^)]*\)'
        display_reasoning = re.sub(tool_pattern, '', display_reasoning)
        # Remove empty code blocks
        display_reasoning = re.sub(r'```\s*\n?\s*```', '', display_reasoning)
        display_reasoning = re.sub(r'```[^`]*```', '', display_reasoning)
        display_reasoning = display_reasoning.strip()
        
        # Additional cleanup - remove multiple newlines, empty code blocks, and excess whitespace
        display_response = re.sub(r'```\s*```', '', display_response)
        display_response = re.sub(r'\n{3,}', '\n\n', display_response)
        display_response = re.sub(r'\n\s*\n\s*\n', '\n\n', display_response)
        display_response = display_response.strip()
        
        # Update display based on what content we have
        # Only show panels if there's actual meaningful content
        if self._in_thinking and display_reasoning and len(display_reasoning.strip()) > 10:
            panel = Panel(
                Text(display_reasoning, style="dim italic"),
                title="[yellow]💭 Reasoning[/yellow]",
                border_style="yellow",
                padding=(0, 1)
            )
            self._live.update(panel)
        elif display_response and len(display_response.strip()) > 5:
            from rich.markdown import Markdown
            icon = self._ascii_art.get_icon("robot")
            panel = Panel(
                Markdown(display_response),
                title=f"[{self._theme_manager.get_style('assistant_message')}]{icon} Assistant[/{self._theme_manager.get_style('assistant_message')}]",
                title_align="left",
                border_style=self._theme_manager.get_color("primary"),
                padding=(0, 1)
            )
            self._live.update(panel)
        else:
            self._live.update(Text("⠋ Thinking...", style="dim italic"))
    
    def stop_live_stream(self) -> tuple:
        """
        Stop live stream and return buffers.
        
        Returns:
            Tuple of (response_content, reasoning_content)
            Note: response_content includes raw tool calls for parsing by CLI
        """
        if self._live:
            self._live.stop()
            self._live = None
        
        reasoning = getattr(self, '_reasoning_buffer', '')
        # Return raw response including tool calls (CLI needs them for parsing)
        response = getattr(self, '_raw_response_buffer', getattr(self, '_response_buffer', ''))
        
        # If reasoning contains what looks like the actual response (markdown headers,
        # structured content), move it to response and keep only the thinking part
        if reasoning and not response:
            # Look for markers that indicate actual response content
            import re
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
                response = '\n'.join(response_lines).strip()
        
        return response.strip(), reasoning.strip()
    
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


_renderer: Optional[RichRenderer] = None


def get_renderer() -> RichRenderer:
    """Get the global renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = RichRenderer()
    return _renderer
