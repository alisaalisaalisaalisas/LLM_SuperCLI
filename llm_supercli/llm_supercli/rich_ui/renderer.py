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
        """Print welcome message with instructions."""
        self.print_banner("small")
        self._console.print()
        self._console.print("[dim]Tips:[/dim]")
        self._console.print("[dim]1. Ask questions, edit files, or run commands[/dim]")
        self._console.print("[dim]2. Use [bold]@file[/bold] to include file contents[/dim]")
        self._console.print("[dim]3. Use [bold]/help[/bold] for more information[/dim]")
        self._console.print()
    
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


_renderer: Optional[RichRenderer] = None


def get_renderer() -> RichRenderer:
    """Get the global renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = RichRenderer()
    return _renderer
