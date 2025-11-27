"""Compress command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class CompressCommand(SlashCommand):
    """Compress conversation context."""
    
    name = "compress"
    description = "Compress conversation to reduce context size"
    usage = "[summary]"
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute compress command."""
        from ...history import get_session_store
        
        store = get_session_store()
        session = store.current_session
        
        if not session:
            return CommandResult.error("No active session to compress")
        
        if session.message_count < 4:
            return CommandResult.success(
                "Session is small enough, no compression needed."
            )
        
        original_count = session.message_count
        original_tokens = session.total_tokens
        
        system_msgs = [m for m in session.messages if m.role == "system"]
        recent_msgs = session.messages[-4:]
        
        if args.strip():
            summary = args.strip()
        else:
            all_content = "\n".join(
                f"{m.role}: {m.content[:200]}..." 
                for m in session.messages[:-4]
            )
            summary = f"[Previous conversation summary: {len(session.messages) - 4} messages about various topics]"
        
        session.messages = system_msgs
        
        session.add_message(
            role="system",
            content=f"Context summary: {summary}"
        )
        
        session.messages.extend(recent_msgs)
        session.message_count = len(session.messages)
        
        estimated_new_tokens = sum(len(m.content) // 4 for m in session.messages)
        
        store.save_session(session)
        
        return CommandResult.success(
            f"Compressed conversation:\n"
            f"- Messages: {original_count} → {session.message_count}\n"
            f"- Est. tokens: ~{original_tokens:,} → ~{estimated_new_tokens:,}"
        )
