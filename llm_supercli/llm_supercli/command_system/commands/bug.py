"""Bug report command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class BugCommand(SlashCommand):
    """Report a bug."""
    
    name = "bug"
    description = "Report a bug or issue"
    usage = "[description]"
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        import webbrowser
        
        if args.strip():
            return CommandResult.success(
                f"Bug report noted: {args}\n\n"
                "To submit, please open an issue at:\n"
                "https://github.com/llm-supercli/llm-supercli/issues"
            )
        
        try:
            webbrowser.open("https://github.com/llm-supercli/llm-supercli/issues/new")
            return CommandResult.success("Opened bug report page in browser")
        except Exception:
            return CommandResult.success(
                "Please report bugs at:\n"
                "https://github.com/llm-supercli/llm-supercli/issues"
            )
