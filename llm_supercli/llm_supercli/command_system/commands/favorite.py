"""Favorite command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class FavoriteCommand(SlashCommand):
    """Manage favorites."""
    
    name = "favorite"
    description = "Add or manage favorite sessions"
    aliases = ["fav", "star"]
    usage = "[add|remove|list]"
    examples = ["/favorite", "/favorite add", "/favorite list"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute favorite command."""
        from ...history import get_session_store, get_favorites_manager
        
        store = get_session_store()
        favorites = get_favorites_manager()
        
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0].lower() if parts else "add"
        subargs = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "add":
            return self._add_favorite(store, favorites, subargs)
        elif subcommand == "remove":
            return self._remove_favorite(store, favorites, subargs)
        elif subcommand == "list":
            return self._list_favorites(favorites)
        else:
            return CommandResult.error(
                f"Unknown subcommand: {subcommand}. Use: add, remove, list"
            )
    
    def _add_favorite(self, store, favorites, session_id: str) -> CommandResult:
        """Add current or specified session to favorites."""
        if session_id:
            session = store.load_session(session_id)
        else:
            session = store.current_session
        
        if not session:
            return CommandResult.error(
                "No session to favorite. Start a chat or specify a session ID."
            )
        
        fav = favorites.add_favorite(
            item_type="session",
            reference_id=session.id,
            title=session.title
        )
        
        session.is_favorite = True
        store.save_session(session)
        
        return CommandResult.success(f"⭐ Added **{session.title}** to favorites")
    
    def _remove_favorite(self, store, favorites, session_id: str) -> CommandResult:
        """Remove a session from favorites."""
        if session_id:
            ref_id = session_id
        elif store.current_session:
            ref_id = store.current_session.id
        else:
            return CommandResult.error("No session specified")
        
        if favorites.remove_favorite("session", ref_id):
            session = store.load_session(ref_id)
            if session:
                session.is_favorite = False
                store.save_session(session)
            return CommandResult.success("Removed from favorites")
        else:
            return CommandResult.error("Session is not in favorites")
    
    def _list_favorites(self, favorites) -> CommandResult:
        """List all favorite sessions."""
        fav_list = favorites.list_favorites(item_type="session")
        
        if not fav_list:
            return CommandResult.success(
                "No favorites yet. Use `/favorite add` to save a session."
            )
        
        lines = ["# ⭐ Favorites", ""]
        for fav in fav_list:
            tags = " ".join(f"`{t}`" for t in fav.tags) if fav.tags else ""
            lines.append(f"- **{fav.title}** ({fav.reference_id[:8]}...) {tags}")
        
        return CommandResult.success("\n".join(lines))
