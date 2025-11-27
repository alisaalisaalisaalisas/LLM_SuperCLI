"""Quit command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class QuitCommand(SlashCommand):
    """Exit the CLI."""
    
    name = "quit"
    description = "Exit the CLI"
    aliases = ["exit", "q", "bye"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute quit command."""
        return CommandResult.exit("Goodbye! 👋")
