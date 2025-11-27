"""Help command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult
from ..registry import get_command_registry


class HelpCommand(SlashCommand):
    """Display help information."""
    
    name = "help"
    description = "Show help information for commands"
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
        
        lines = [
            "# LLM SuperCLI Help",
            "",
            "## Available Commands",
            ""
        ]
        
        for cmd in commands:
            aliases = f" ({', '.join(cmd['aliases'])})" if cmd['aliases'] else ""
            lines.append(f"**/{cmd['name']}**{aliases} - {cmd['description']}")
        
        lines.extend([
            "",
            "## Special Syntax",
            "",
            "- `!command` - Execute shell command",
            "- `@file` - Include file contents in prompt",
            "",
            "Type `/help <command>` for detailed help on a specific command."
        ])
        
        return CommandResult.success("\n".join(lines))
