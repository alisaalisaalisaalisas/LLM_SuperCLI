"""Review command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class ReviewCommand(SlashCommand):
    """Review code."""
    
    name = "review"
    description = "Request a code review"
    usage = "[file|diff]"
    examples = ["/review main.py", "/review --diff"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        return CommandResult.success(
            "# Code Review\n\n"
            "To request a code review, include the file with @filename:\n\n"
            "```\n"
            "@main.py Please review this code for bugs and improvements\n"
            "```\n\n"
            "Or paste the code directly in your message."
        )
