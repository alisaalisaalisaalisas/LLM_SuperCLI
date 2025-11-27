"""Account command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class AccountCommand(SlashCommand):
    """View account information."""
    
    name = "account"
    description = "View current account and authentication status"
    aliases = ["whoami", "me"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute account command."""
        from ...auth import get_session_manager
        from ...history import get_session_store
        
        session_manager = get_session_manager()
        store = get_session_store()
        
        lines = ["# Account Information", ""]
        
        if session_manager.is_authenticated():
            user = session_manager.get_user_info()
            lines.extend([
                "## Authentication",
                f"**Status:** ✅ Logged in",
                f"**Provider:** {user.get('provider', 'Unknown').title()}",
                f"**Name:** {user.get('name', 'N/A')}",
                f"**Email:** {user.get('email', 'N/A')}",
                ""
            ])
        else:
            lines.extend([
                "## Authentication",
                "**Status:** ❌ Not logged in",
                "",
                "Use `/login google` or `/login github` to authenticate.",
                ""
            ])
        
        usage = store.get_total_usage()
        session_count = store.get_session_count()
        
        lines.extend([
            "## Usage Statistics",
            f"**Total Sessions:** {session_count}",
            f"**Total Tokens:** {usage['tokens']:,}",
            f"**Total Cost:** ${usage['cost']:.4f}",
        ])
        
        return CommandResult.success("\n".join(lines))
