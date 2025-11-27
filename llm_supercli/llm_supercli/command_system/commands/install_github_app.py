"""Install GitHub App command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class InstallGitHubAppCommand(SlashCommand):
    """Install GitHub App."""
    
    name = "install-github-app"
    description = "Install the GitHub App for enhanced features"
    hidden = True
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        import webbrowser
        
        url = "https://github.com/apps/llm-supercli"
        
        try:
            webbrowser.open(url)
            return CommandResult.success(
                "Opened GitHub App installation page.\n"
                "Follow the prompts to install the app on your repositories."
            )
        except Exception:
            return CommandResult.success(
                f"Visit {url} to install the GitHub App."
            )
