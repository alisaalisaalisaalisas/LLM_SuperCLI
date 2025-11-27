"""New session command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class NewCommand(SlashCommand):
    """Start a new chat session."""
    
    name = "new"
    description = "Start a new chat session"
    aliases = ["reset"]
    usage = "[title]"
    examples = ["/new", "/new My coding project"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute new session command."""
        from ...history import get_session_store
        from ...config import get_config
        
        store = get_session_store()
        config = get_config()
        
        title = args.strip() if args.strip() else "New Chat"
        
        session = store.create_session(
            provider=config.llm.provider,
            model=config.llm.model,
            system_prompt=config.llm.system_prompt,
            title=title
        )
        
        return CommandResult.success(
            f"Started new session: **{session.title}**\n"
            f"Provider: {session.provider} | Model: {session.model}",
            data={"session_id": session.id}
        )
