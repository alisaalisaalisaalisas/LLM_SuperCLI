"""Help command for llm_supercli."""
from typing import Any

from rich.console import Console
from rich.text import Text

from ..base import SlashCommand, CommandResult
from ..registry import get_command_registry


class HelpCommand(SlashCommand):
    """Display help information."""
    
    name = "help"
    description = "Show available slash commands"
    aliases = ["h", "?"]
    usage = "[command]"
    examples = ["/help", "/help model", "/help mcp"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute help command."""
        registry = get_command_registry()
        
        if args.strip():
            command_name = args.strip().lstrip("/")
            help_text = registry.get_help(command_name)
            
            if help_text:
                return CommandResult.success(help_text)
            else:
                return CommandResult.error(f"Unknown command: {command_name}")
        
        commands = registry.list_commands()
        
        console = Console()
        
        max_name_len = max(len(cmd['name']) for cmd in commands) if commands else 10
        
        header = Text()
        header.append("● ", style="cyan")
        header.append("Available Commands:", style="bold")
        console.print(header)
        console.print()
        
        for cmd in sorted(commands, key=lambda x: x['name']):
            line = Text()
            line.append(f"  /{cmd['name']:<{max_name_len + 2}}", style="cyan")
            line.append(f"- {cmd['description']}", style="dim")
            console.print(line)
        
        console.print()
        console.print("Other commands will be passed to the LLM.", style="dim")
        
        return CommandResult.success("")
