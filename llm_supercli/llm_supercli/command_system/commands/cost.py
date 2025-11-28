"""Cost command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


# OAuth-based free tier providers
FREE_PROVIDERS = ["gemini", "qwen"]


class CostCommand(SlashCommand):
    """Show token usage and costs."""
    
    name = "cost"
    description = "Show token usage and estimated costs"
    aliases = ["usage", "tokens"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute cost command."""
        from ...history import get_session_store
        
        store = get_session_store()
        session = store.current_session
        total = store.get_total_usage()
        
        lines = ["# Usage & Cost Summary", ""]
        
        if session:
            provider = session.provider.lower() if session.provider else ""
            is_free = provider in FREE_PROVIDERS
            
            lines.extend([
                "## Current Session",
                f"**Provider:** {session.provider.title() if session.provider else 'Unknown'}",
                f"**Model:** {session.model or 'Unknown'}",
                f"**Messages:** {session.message_count}",
                f"**Total Tokens:** {session.total_tokens:,}",
            ])
            
            if is_free:
                lines.append("**Cost:** Free (OAuth tier)")
            else:
                lines.append(f"**Estimated Cost:** ${session.total_cost:.4f}")
            
            lines.append("")
        
        lines.extend([
            "## All-Time Usage",
            f"**Total Sessions:** {store.get_session_count()}",
            f"**Total Tokens:** {total['tokens']:,}",
            f"**Total Cost:** ${total['cost']:.4f}",
            "",
            "[dim]Note: Gemini and Qwen use free OAuth tiers[/dim]"
        ])
        
        return CommandResult.success("\n".join(lines))
