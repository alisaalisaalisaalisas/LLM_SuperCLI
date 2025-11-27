"""Billing command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class BillingCommand(SlashCommand):
    """View billing information."""
    
    name = "billing"
    description = "View billing and subscription information"
    requires_auth = True
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        from ...auth import get_session_manager
        
        if not get_session_manager().is_authenticated():
            return CommandResult.error("Please login first with /login")
        
        return CommandResult.success(
            "# Billing Information\n\n"
            "Billing information is not available in the open-source version.\n"
            "For enterprise billing, contact support."
        )
