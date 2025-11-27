"""Logout command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class LogoutCommand(SlashCommand):
    """Logout from current session."""
    
    name = "logout"
    description = "Logout from OAuth session or LLM provider"
    usage = "[gemini|qwen|google|github|all]"
    examples = [
        "/logout gemini  # Logout from Gemini API",
        "/logout qwen    # Logout from Qwen/DashScope",
        "/logout google  # Logout from Google account",
        "/logout all     # Logout from all providers",
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute logout command."""
        from ...auth import get_session_manager, GeminiOAuth, QwenOAuth
        
        session_manager = get_session_manager()
        provider = args.strip().lower()
        
        # Handle Gemini logout
        if provider == "gemini":
            from pathlib import Path
            creds_file = Path.home() / ".gemini" / "oauth_creds.json"
            if creds_file.exists():
                creds_file.unlink()
                return CommandResult.success("Logged out from Gemini.")
            return CommandResult.success("Not logged in to Gemini.")
        
        # Handle Qwen logout
        if provider == "qwen":
            oauth = QwenOAuth()
            if oauth.logout():
                return CommandResult.success("Logged out from Qwen (DashScope).")
            return CommandResult.success("Not logged in to Qwen.")
        
        # Handle "all" - also logout from LLM providers
        if provider == "all":
            session_manager.clear_all_sessions()
            # Also clear LLM provider credentials
            from pathlib import Path
            gemini_creds = Path.home() / ".gemini" / "oauth_creds.json"
            qwen_creds = Path.home() / ".qwen" / "oauth_creds.json"
            if gemini_creds.exists():
                gemini_creds.unlink()
            if qwen_creds.exists():
                qwen_creds.unlink()
            return CommandResult.success("Logged out from all providers (including Gemini and Qwen).")
        
        if not session_manager.is_authenticated():
            return CommandResult.success("Not currently logged in.")
        
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
