"""
MCP Manager for llm_supercli.
High-level management of MCP server connections.
"""
import asyncio
from typing import Any, Dict, List, Optional

from .mcp_registry import MCPRegistry, MCPServerConfig, get_mcp_registry
from .mcp_server_client import MCPServerClient, MCPConnection, ConnectionState


class MCPManager:
    """
    High-level manager for MCP server connections.
    
    Provides a unified interface for managing multiple MCP server connections,
    discovering tools, and executing tool calls.
    """
    
    _instance: Optional['MCPManager'] = None
    
    def __new__(cls) -> 'MCPManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._registry = get_mcp_registry()
        self._clients: Dict[str, MCPServerClient] = {}
    
    @property
    def registry(self) -> MCPRegistry:
        """Get the MCP registry."""
        return self._registry
    
    async def connect(self, server_name: str) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            True if connection successful
        """
        config = self._registry.get(server_name)
        if not config:
            return False
        
        if server_name in self._clients:
            if self._clients[server_name].is_connected:
                return True
        
        client = MCPServerClient(config)
        success = await client.connect()
        
        if success:
            self._clients[server_name] = client
        
        return success
    
    async def disconnect(self, server_name: str) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            True if disconnected
        """
        if server_name not in self._clients:
            return False
        
        client = self._clients[server_name]
        await client.disconnect()
        del self._clients[server_name]
        return True
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self._clients.keys()):
            await self.disconnect(name)
    
    async def connect_auto_connect_servers(self) -> Dict[str, bool]:
        """
        Connect to all servers configured for auto-connect.
        
        Returns:
            Dict mapping server names to connection success
        """
        results = {}
        for config in self._registry.get_auto_connect_servers():
            results[config.name] = await self.connect(config.name)
        return results
    
    def get_connection(self, server_name: str) -> Optional[MCPConnection]:
        """
        Get connection state for a server.
        
        Args:
            server_name: Server name
            
        Returns:
            Connection state or None
        """
        if server_name in self._clients:
            return self._clients[server_name].connection
        return None
    
    def list_connections(self) -> List[MCPConnection]:
        """List all active connections."""
        return [client.connection for client in self._clients.values()]
    
    def is_connected(self, server_name: str) -> bool:
        """Check if connected to a server."""
        return (
            server_name in self._clients and 
            self._clients[server_name].is_connected
        )
    
    def get_all_tools(self) -> Dict[str, List[dict]]:
        """
        Get all available tools from connected servers.
        
        Returns:
            Dict mapping server names to tool lists
        """
        result = {}
        for name, client in self._clients.items():
            if client.is_connected:
                result[name] = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema
                    }
                    for tool in client.connection.tools
                ]
        return result
    
    def get_all_resources(self) -> Dict[str, List[dict]]:
        """
        Get all available resources from connected servers.
        
        Returns:
            Dict mapping server names to resource lists
        """
        result = {}
        for name, client in self._clients.items():
            if client.is_connected:
                result[name] = [
                    {
                        "uri": r.uri,
                        "name": r.name,
                        "description": r.description,
                        "mime_type": r.mime_type
                    }
                    for r in client.connection.resources
                ]
        return result
    
    def find_tool(self, tool_name: str) -> Optional[tuple[str, dict]]:
        """
        Find a tool by name across all connected servers.
        
        Args:
            tool_name: Tool name to find
            
        Returns:
            Tuple of (server_name, tool_info) or None
        """
        for name, client in self._clients.items():
            if client.is_connected:
                for tool in client.connection.tools:
                    if tool.name == tool_name:
                        return name, {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.input_schema
                        }
        return None
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None
    ) -> Any:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            server_name: Optional server to use (auto-discovers if not provided)
            
        Returns:
            Tool result
            
        Raises:
            ValueError: If tool not found
            RuntimeError: If not connected
        """
        if server_name:
            if server_name not in self._clients:
                raise ValueError(f"Not connected to server: {server_name}")
            client = self._clients[server_name]
        else:
            tool_info = self.find_tool(tool_name)
            if not tool_info:
                raise ValueError(f"Tool not found: {tool_name}")
            server_name, _ = tool_info
            client = self._clients[server_name]
        
        return await client.call_tool(tool_name, arguments)
    
    async def read_resource(
        self,
        uri: str,
        server_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Read an MCP resource.
        
        Args:
            uri: Resource URI
            server_name: Optional server to use
            
        Returns:
            Resource content
        """
        if server_name:
            if server_name not in self._clients:
                return None
            return await self._clients[server_name].read_resource(uri)
        
        for client in self._clients.values():
            if client.is_connected:
                for resource in client.connection.resources:
                    if resource.uri == uri:
                        return await client.read_resource(uri)
        
        return None
    
    def get_tools_for_llm(self) -> List[dict]:
        """
        Get all tools formatted for LLM function calling.
        
        Returns:
            List of tool definitions in OpenAI function format
        """
        tools = []
        for name, client in self._clients.items():
            if client.is_connected:
                for tool in client.connection.tools:
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": f"{name}__{tool.name}",
                            "description": tool.description,
                            "parameters": tool.input_schema
                        }
                    })
        return tools
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Handle a tool call from LLM (with namespaced tool names).
        
        Args:
            tool_name: Namespaced tool name (server__tool)
            arguments: Tool arguments
            
        Returns:
            Tool result as string
        """
        if "__" in tool_name:
            server_name, actual_tool = tool_name.split("__", 1)
        else:
            result = self.find_tool(tool_name)
            if not result:
                return f"Error: Tool '{tool_name}' not found"
            server_name, _ = result
            actual_tool = tool_name
        
        try:
            result = await self.call_tool(actual_tool, arguments, server_name)
            if isinstance(result, dict):
                content = result.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", str(result))
            return str(result)
        except Exception as e:
            return f"Error calling tool: {e}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get overall MCP status.
        
        Returns:
            Status information dict
        """
        registered = self._registry.list_server_names()
        connected = [
            name for name, client in self._clients.items()
            if client.is_connected
        ]
        
        return {
            "registered_servers": len(registered),
            "connected_servers": len(connected),
            "servers": {
                name: {
                    "registered": True,
                    "connected": name in connected,
                    "tools": len(self._clients[name].connection.tools) if name in connected else 0,
                    "resources": len(self._clients[name].connection.resources) if name in connected else 0,
                }
                for name in registered
            }
        }


_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
