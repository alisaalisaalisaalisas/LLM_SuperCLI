"""Cost command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


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
            lines.extend([
                "## Current Session",
                f"**Messages:** {session.message_count}",
                f"**Input Tokens:** ~{session.total_tokens // 2:,}",
                f"**Output Tokens:** ~{session.total_tokens // 2:,}",
                f"**Total Tokens:** {session.total_tokens:,}",
                f"**Estimated Cost:** ${session.total_cost:.4f}",
                ""
            ])
        
        lines.extend([
            "## All-Time Usage",
            f"**Total Sessions:** {store.get_session_count()}",
            f"**Total Tokens:** {total['tokens']:,}",
            f"**Total Cost:** ${total['cost']:.4f}",
        ])
        
        return CommandResult.success("\n".join(lines))
