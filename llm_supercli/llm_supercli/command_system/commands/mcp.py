"""MCP command for llm_supercli."""
from typing import Any

from ..base import AsyncSlashCommand, CommandResult


class MCPCommand(AsyncSlashCommand):
    """Manage MCP server connections."""
    
    name = "mcp"
    description = "Manage MCP (Model Context Protocol) server connections"
    usage = "[list|connect|disconnect|tools|add|remove] [args]"
    examples = [
        "/mcp",
        "/mcp list",
        "/mcp connect filesystem",
        "/mcp disconnect filesystem",
        "/mcp tools",
        "/mcp add myserver --command npx --args @modelcontextprotocol/server-filesystem"
    ]
    
    async def run_async(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute MCP command."""
        from ...mcp import get_mcp_manager, MCPServerConfig
        
        mcp = get_mcp_manager()
        parts = args.strip().split(maxsplit=1)
        subcommand = parts[0].lower() if parts else "list"
        subargs = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "list":
            return self._list_servers(mcp)
        elif subcommand == "connect":
            return await self._connect(mcp, subargs)
        elif subcommand == "disconnect":
            return await self._disconnect(mcp, subargs)
        elif subcommand == "tools":
            return self._list_tools(mcp)
        elif subcommand == "resources":
            return self._list_resources(mcp)
        elif subcommand == "add":
            return self._add_server(mcp, subargs)
        elif subcommand == "remove":
            return self._remove_server(mcp, subargs)
        elif subcommand == "status":
            return self._show_status(mcp)
        else:
            return CommandResult.error(
                f"Unknown subcommand: {subcommand}. "
                "Use: list, connect, disconnect, tools, resources, add, remove, status"
            )
    
    def _list_servers(self, mcp) -> CommandResult:
        """List registered MCP servers."""
        servers = mcp.registry.list_servers()
        
        if not servers:
            return CommandResult.success(
                "No MCP servers registered.\n\n"
                "Use `/mcp add <name> --command <cmd>` to add a server."
            )
        
        lines = ["# MCP Servers", ""]
        
        for server in servers:
            connected = mcp.is_connected(server.name)
            status = "🟢 Connected" if connected else "⚪ Disconnected"
            enabled = "✓" if server.enabled else "✗"
            
            lines.append(f"## {server.name} [{enabled}] {status}")
            lines.append(f"  Command: `{server.command} {' '.join(server.args)}`")
            if server.description:
                lines.append(f"  {server.description}")
            lines.append("")
        
        return CommandResult.success("\n".join(lines))
    
    async def _connect(self, mcp, server_name: str) -> CommandResult:
        """Connect to an MCP server."""
        if not server_name:
            return CommandResult.error("Please specify a server name")
        
        if mcp.is_connected(server_name):
            return CommandResult.success(f"Already connected to **{server_name}**")
        
        success = await mcp.connect(server_name)
        
        if success:
            conn = mcp.get_connection(server_name)
            tools_count = len(conn.tools) if conn else 0
            return CommandResult.success(
                f"✅ Connected to **{server_name}**\n"
                f"Available tools: {tools_count}"
            )
        else:
            return CommandResult.error(f"Failed to connect to {server_name}")
    
    async def _disconnect(self, mcp, server_name: str) -> CommandResult:
        """Disconnect from an MCP server."""
        if not server_name:
            return CommandResult.error("Please specify a server name")
        
        if not mcp.is_connected(server_name):
            return CommandResult.success(f"Not connected to **{server_name}**")
        
        await mcp.disconnect(server_name)
        return CommandResult.success(f"Disconnected from **{server_name}**")
    
    def _list_tools(self, mcp) -> CommandResult:
        """List all available MCP tools."""
        all_tools = mcp.get_all_tools()
        
        if not all_tools:
            return CommandResult.success(
                "No MCP tools available.\n"
                "Connect to an MCP server first with `/mcp connect <server>`"
            )
        
        lines = ["# Available MCP Tools", ""]
        
        for server, tools in all_tools.items():
            lines.append(f"## {server}")
            for tool in tools:
                lines.append(f"  - **{tool['name']}**: {tool['description'][:60]}...")
            lines.append("")
        
        return CommandResult.success("\n".join(lines))
    
    def _list_resources(self, mcp) -> CommandResult:
        """List all available MCP resources."""
        all_resources = mcp.get_all_resources()
        
        if not all_resources:
            return CommandResult.success("No MCP resources available.")
        
        lines = ["# Available MCP Resources", ""]
        
        for server, resources in all_resources.items():
            lines.append(f"## {server}")
            for resource in resources:
                lines.append(f"  - **{resource['name']}**: `{resource['uri']}`")
            lines.append("")
        
        return CommandResult.success("\n".join(lines))
    
    def _add_server(self, mcp, args: str) -> CommandResult:
        """Add an MCP server."""
        from ...mcp import MCPServerConfig
        
        parts = args.split()
        if not parts:
            return CommandResult.error(
                "Usage: /mcp add <name> --command <cmd> [--args <arg1> <arg2>...]"
            )
        
        name = parts[0]
        command = ""
        server_args = []
        description = ""
        
        i = 1
        while i < len(parts):
            if parts[i] == "--command" and i + 1 < len(parts):
                command = parts[i + 1]
                i += 2
            elif parts[i] == "--args":
                i += 1
                while i < len(parts) and not parts[i].startswith("--"):
                    server_args.append(parts[i])
                    i += 1
            elif parts[i] == "--description" and i + 1 < len(parts):
                description = parts[i + 1]
                i += 2
            else:
                i += 1
        
        if not command:
            return CommandResult.error("Please specify --command")
        
        config = MCPServerConfig(
            name=name,
            command=command,
            args=server_args,
            description=description,
            enabled=True
        )
        
        mcp.registry.register(config)
        return CommandResult.success(f"Added MCP server: **{name}**")
    
    def _remove_server(self, mcp, server_name: str) -> CommandResult:
        """Remove an MCP server."""
        if not server_name:
            return CommandResult.error("Please specify a server name")
        
        if mcp.registry.unregister(server_name):
            return CommandResult.success(f"Removed MCP server: **{server_name}**")
        else:
            return CommandResult.error(f"Server not found: {server_name}")
    
    def _show_status(self, mcp) -> CommandResult:
        """Show MCP status."""
        status = mcp.get_status()
        
        lines = [
            "# MCP Status",
            "",
            f"**Registered Servers:** {status['registered_servers']}",
            f"**Connected Servers:** {status['connected_servers']}",
            ""
        ]
        
        for name, info in status['servers'].items():
            status_icon = "🟢" if info['connected'] else "⚪"
            lines.append(
                f"- {status_icon} **{name}**: "
                f"{info['tools']} tools, {info['resources']} resources"
            )
        
        return CommandResult.success("\n".join(lines))
