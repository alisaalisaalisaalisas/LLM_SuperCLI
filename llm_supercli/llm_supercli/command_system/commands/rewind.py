"""Rewind command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class RewindCommand(SlashCommand):
    """Rewind conversation."""
    
    name = "rewind"
    description = "Remove the last N messages from conversation"
    aliases = ["undo"]
    usage = "[count]"
    examples = ["/rewind", "/rewind 2"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute rewind command."""
        from ...history import get_session_store
        
        store = get_session_store()
        session = store.current_session
        
        if not session:
            return CommandResult.error("No active session")
        
        if not session.messages:
            return CommandResult.success("No messages to rewind")
        
        try:
            count = int(args.strip()) if args.strip() else 2
        except ValueError:
            return CommandResult.error("Please provide a valid number")
        
        count = min(count, len(session.messages))
        removed = session.rewind(count)
        store.save_session(session)
        
        lines = [f"Removed {len(removed)} message(s):", ""]
        for msg in reversed(removed):
            preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            lines.append(f"- [{msg.role}] {preview}")
        
        return CommandResult.success("\n".join(lines))
