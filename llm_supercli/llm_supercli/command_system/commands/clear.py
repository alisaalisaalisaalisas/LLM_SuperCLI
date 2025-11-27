"""Clear command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class ClearCommand(SlashCommand):
    """Clear the terminal screen."""
    
    name = "clear"
    description = "Clear the terminal screen"
    aliases = ["cls"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute clear command."""
        return CommandResult.clear()
