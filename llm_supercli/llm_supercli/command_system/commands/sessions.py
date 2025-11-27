"""Sessions command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult
from ...utils import format_timestamp


class SessionsCommand(SlashCommand):
    """Manage chat sessions."""
    
    name = "sessions"
    description = "List and manage chat sessions"
    aliases = ["history"]
    usage = "[list|load|delete|search] [args]"
    examples = [
        "/sessions",
        "/sessions list",
        "/sessions load abc123",
        "/sessions delete abc123",
        "/sessions search python"
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute sessions command."""
        from ...history import get_session_store
        
        store = get_session_store()
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0].lower() if parts else "list"
        subargs = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "list":
            return self._list_sessions(store)
        elif subcommand == "load":
            return self._load_session(store, subargs)
        elif subcommand == "delete":
            return self._delete_session(store, subargs)
        elif subcommand == "search":
            return self._search_sessions(store, subargs)
        else:
            return CommandResult.error(
                f"Unknown subcommand: {subcommand}. "
                "Use: list, load, delete, search"
            )
    
    def _list_sessions(self, store) -> CommandResult:
        """List recent sessions."""
        sessions = store.list_sessions(limit=20)
        
        if not sessions:
            return CommandResult.success("No sessions found. Start a new chat!")
        
        lines = ["# Recent Sessions", ""]
        for s in sessions:
            star = "⭐ " if s.get("is_favorite") else ""
            time_str = format_timestamp(s["updated_at"], "%Y-%m-%d %H:%M")
            lines.append(
                f"- {star}**{s['title'][:40]}** ({s['id'][:8]}...)\n"
                f"  {s['provider']}/{s['model']} | {s['message_count']} msgs | {time_str}"
            )
        
        return CommandResult.success("\n".join(lines), data=sessions)
    
    def _load_session(self, store, session_id: str) -> CommandResult:
        """Load a specific session."""
        if not session_id:
            return CommandResult.error("Please provide a session ID")
        
        session = store.load_session(session_id)
        if session:
            return CommandResult.success(
                f"Loaded session: **{session.title}**\n"
                f"{session.message_count} messages | "
                f"{session.total_tokens} tokens | ${session.total_cost:.4f}",
                data={"session": session}
            )
        else:
            return CommandResult.error(f"Session not found: {session_id}")
    
    def _delete_session(self, store, session_id: str) -> CommandResult:
        """Delete a session."""
        if not session_id:
            return CommandResult.error("Please provide a session ID")
        
        if store.delete_session(session_id):
            return CommandResult.success(f"Deleted session: {session_id}")
        else:
            return CommandResult.error(f"Session not found: {session_id}")
    
    def _search_sessions(self, store, query: str) -> CommandResult:
        """Search sessions."""
        if not query:
            return CommandResult.error("Please provide a search query")
        
        results = store.search_sessions(query)
        
        if not results:
            return CommandResult.success(f"No sessions found matching: {query}")
        
        lines = [f"# Search Results for '{query}'", ""]
        for s in results:
            lines.append(f"- **{s['title'][:40]}** ({s['id'][:8]}...)")
        
        return CommandResult.success("\n".join(lines), data=results)
