"""Logout command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class LogoutCommand(SlashCommand):
    """Logout from current session."""
    
    name = "logout"
    description = "Logout from current OAuth session"
    usage = "[google|github|all]"
    examples = ["/logout", "/logout google", "/logout all"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute logout command."""
        from ...auth import get_session_manager
        
        session_manager = get_session_manager()
        provider = args.strip().lower()
        
        if not session_manager.is_authenticated():
            return CommandResult.success("Not currently logged in.")
        
        if provider == "all":
            session_manager.clear_all_sessions()
            return CommandResult.success("Logged out from all providers.")
        
        if provider:
            if session_manager.remove_session(provider):
                return CommandResult.success(f"Logged out from {provider.title()}.")
            else:
                return CommandResult.error(f"Not logged in to {provider.title()}.")
        
        active = session_manager.get_active_session()
        if active:
            session_manager.remove_session(active.provider)
            return CommandResult.success(
                f"Logged out from {active.provider.title()} "
                f"({active.user_name or active.user_email})."
            )
        
        return CommandResult.success("Not currently logged in.")
