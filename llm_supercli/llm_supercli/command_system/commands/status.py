"""Status command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class StatusCommand(SlashCommand):
    """Show current status."""
    
    name = "status"
    description = "Show current CLI status and configuration"
    aliases = ["info"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute status command."""
        from ...config import get_config
        from ...llm import get_provider_registry
        from ...mcp import get_mcp_manager
        from ...history import get_session_store
        from ...auth import get_session_manager
        
        config = get_config()
        registry = get_provider_registry()
        mcp = get_mcp_manager()
        store = get_session_store()
        auth = get_session_manager()
        
        provider = registry.get(config.llm.provider)
        
        lines = ["# LLM SuperCLI Status", ""]
        
        lines.extend([
            "## LLM Configuration",
            f"**Provider:** {config.llm.provider}",
            f"**Model:** {config.llm.model}",
            f"**API Key:** {'[+] Set' if provider and provider.api_key else '[-] Not set'}",
            f"**Temperature:** {config.llm.temperature}",
            f"**Max Tokens:** {config.llm.max_tokens}",
            ""
        ])
        
        if auth.is_authenticated():
            user = auth.get_user_info()
            lines.extend([
                "## Authentication",
                f"**Status:** [+] Logged in ({user.get('provider', 'Unknown').title()})",
                f"**User:** {user.get('name', user.get('email', 'Unknown'))}",
                ""
            ])
        else:
            lines.extend([
                "## Authentication",
                "**Status:** [-] Not logged in",
                ""
            ])
        
        mcp_status = mcp.get_status()
        lines.extend([
            "## MCP Servers",
            f"**Registered:** {mcp_status['registered_servers']}",
            f"**Connected:** {mcp_status['connected_servers']}",
        ])
        
        all_tools = mcp.get_all_tools()
        total_tools = sum(len(tools) for tools in all_tools.values())
        if total_tools > 0:
            lines.append(f"**Available Tools:** {total_tools}")
        lines.append("")
        
        session = store.current_session
        if session:
            lines.extend([
                "## Current Session",
                f"**Title:** {session.title}",
                f"**Messages:** {session.message_count}",
                f"**Tokens:** {session.total_tokens:,}",
                f"**Cost:** ${session.total_cost:.4f}",
                ""
            ])
        
        lines.extend([
            "## UI Settings",
            f"**Theme:** {config.ui.theme}",
            f"**Streaming:** {'Enabled' if config.ui.streaming else 'Disabled'}",
            f"**Markdown:** {'Enabled' if config.ui.markdown_rendering else 'Disabled'}",
        ])
        
        return CommandResult.success("\n".join(lines))
