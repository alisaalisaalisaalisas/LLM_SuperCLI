"""
MCP Server Client for llm_supercli.
Handles communication with MCP servers via stdio or SSE transports.
"""
import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .mcp_registry import MCPServerConfig


class ConnectionState(Enum):
    """MCP connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPPrompt:
    """Represents an MCP prompt template."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MCPConnection:
    """Represents an active MCP connection."""
    server_name: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    prompts: List[MCPPrompt] = field(default_factory=list)
    error: Optional[str] = None
    protocol_version: str = ""
    server_info: Dict[str, Any] = field(default_factory=dict)


class MCPServerClient:
    """
    Client for communicating with MCP servers.
    
    Handles the JSON-RPC protocol over stdio transport.
    """
    
    def __init__(self, config: MCPServerConfig) -> None:
        """
        Initialize MCP server client.
        
        Args:
            config: Server configuration
        """
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._connection = MCPConnection(server_name=config.name)
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._notification_handlers: Dict[str, Callable] = {}
        self._reader_task: Optional[asyncio.Task] = None
    
    @property
    def connection(self) -> MCPConnection:
        """Get the current connection state."""
        return self._connection
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connection.state == ConnectionState.CONNECTED
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            True if connection successful
        """
        if self.is_connected:
            return True
        
        self._connection.state = ConnectionState.CONNECTING
        
        try:
            env = dict(self._config.env)
            
            self._process = subprocess.Popen(
                [self._config.command] + self._config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**dict(subprocess.os.environ), **env},
                bufsize=0
            )
            
            self._reader_task = asyncio.create_task(self._read_messages())
            
            response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "llm_supercli",
                    "version": "1.0.0"
                }
            })
            
            if response:
                self._connection.protocol_version = response.get("protocolVersion", "")
                self._connection.server_info = response.get("serverInfo", {})
                
                await self._send_notification("notifications/initialized", {})
                
                await self._discover_capabilities()
                
                self._connection.state = ConnectionState.CONNECTED
                return True
            else:
                self._connection.state = ConnectionState.ERROR
                self._connection.error = "Failed to initialize"
                return False
                
        except Exception as e:
            self._connection.state = ConnectionState.ERROR
            self._connection.error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        
        self._connection.state = ConnectionState.DISCONNECTED
        self._connection.tools.clear()
        self._connection.resources.clear()
        self._connection.prompts.clear()
    
    async def _discover_capabilities(self) -> None:
        """Discover server capabilities (tools, resources, prompts)."""
        tools_response = await self._send_request("tools/list", {})
        if tools_response and "tools" in tools_response:
            self._connection.tools = [
                MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {})
                )
                for t in tools_response["tools"]
            ]
        
        resources_response = await self._send_request("resources/list", {})
        if resources_response and "resources" in resources_response:
            self._connection.resources = [
                MCPResource(
                    uri=r["uri"],
                    name=r["name"],
                    description=r.get("description", ""),
                    mime_type=r.get("mimeType", "text/plain")
                )
                for r in resources_response["resources"]
            ]
        
        prompts_response = await self._send_request("prompts/list", {})
        if prompts_response and "prompts" in prompts_response:
            self._connection.prompts = [
                MCPPrompt(
                    name=p["name"],
                    description=p.get("description", ""),
                    arguments=p.get("arguments", [])
                )
                for p in prompts_response["prompts"]
            ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to MCP server")
        
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        return response
    
    async def read_resource(self, uri: str) -> Optional[str]:
        """
        Read an MCP resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to MCP server")
        
        response = await self._send_request("resources/read", {"uri": uri})
        
        if response and "contents" in response:
            contents = response["contents"]
            if contents and len(contents) > 0:
                return contents[0].get("text", "")
        
        return None
    
    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, str]] = None
    ) -> Optional[List[Dict[str, str]]]:
        """
        Get a prompt from the server.
        
        Args:
            name: Prompt name
            arguments: Prompt arguments
            
        Returns:
            List of messages
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to MCP server")
        
        response = await self._send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
        
        if response and "messages" in response:
            return response["messages"]
        
        return None
    
    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC request.
        
        Args:
            method: Method name
            params: Method parameters
            timeout: Request timeout
            
        Returns:
            Response result or None
        """
        if not self._process or not self._process.stdin:
            return None
        
        self._request_id += 1
        request_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            message = json.dumps(request) + "\n"
            self._process.stdin.write(message.encode())
            self._process.stdin.flush()
            
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            return None
        except Exception:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]
            return None
    
    async def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._process or not self._process.stdin:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            message = json.dumps(notification) + "\n"
            self._process.stdin.write(message.encode())
            self._process.stdin.flush()
        except Exception:
            pass
    
    async def _read_messages(self) -> None:
        """Read and process messages from server."""
        if not self._process or not self._process.stdout:
            return
        
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                line = await loop.run_in_executor(
                    None,
                    self._process.stdout.readline
                )
                
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode())
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    continue
                    
            except asyncio.CancelledError:
                break
            except Exception:
                break
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle an incoming JSON-RPC message."""
        if "id" in message:
            request_id = message["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if "error" in message:
                    future.set_exception(
                        RuntimeError(message["error"].get("message", "Unknown error"))
                    )
                else:
                    future.set_result(message.get("result"))
        
        elif "method" in message:
            method = message["method"]
            if method in self._notification_handlers:
                try:
                    await self._notification_handlers[method](message.get("params", {}))
                except Exception:
                    pass
    
    def on_notification(self, method: str, handler: Callable) -> None:
        """
        Register a notification handler.
        
        Args:
            method: Notification method name
            handler: Async handler function
        """
        self._notification_handlers[method] = handler
