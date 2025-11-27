"""
MCP Server Registry for llm_supercli.
Manages registration and configuration of MCP servers.
"""
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..constants import MCP_CONFIG_FILE, CONFIG_DIR


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_connect: bool = False
    description: str = ""
    version: str = ""
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerConfig':
        """Create from dictionary."""
        return cls(**data)


class MCPRegistry:
    """
    Registry for MCP server configurations.
    
    Manages persistent storage of server configurations and provides
    methods for registration and discovery of MCP servers.
    """
    
    _instance: Optional['MCPRegistry'] = None
    
    def __new__(cls) -> 'MCPRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._servers: Dict[str, MCPServerConfig] = {}
        self._config_file = MCP_CONFIG_FILE
        self._ensure_config_dir()
        self._load_config()
    
    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> None:
        """Load server configurations from file."""
        if not self._config_file.exists():
            self._save_config()
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for name, server_data in data.get("servers", {}).items():
                self._servers[name] = MCPServerConfig.from_dict(server_data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to load MCP config: {e}")
    
    def _save_config(self) -> None:
        """Save server configurations to file."""
        data = {
            "servers": {
                name: server.to_dict()
                for name, server in self._servers.items()
            }
        }
        
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def register(self, config: MCPServerConfig) -> None:
        """
        Register an MCP server.
        
        Args:
            config: Server configuration
        """
        self._servers[config.name] = config
        self._save_config()
    
    def unregister(self, name: str) -> bool:
        """
        Unregister an MCP server.
        
        Args:
            name: Server name
            
        Returns:
            True if server was unregistered
        """
        if name in self._servers:
            del self._servers[name]
            self._save_config()
            return True
        return False
    
    def get(self, name: str) -> Optional[MCPServerConfig]:
        """
        Get a server configuration.
        
        Args:
            name: Server name
            
        Returns:
            Server configuration or None
        """
        return self._servers.get(name)
    
    def list_servers(self, enabled_only: bool = False) -> List[MCPServerConfig]:
        """
        List all registered servers.
        
        Args:
            enabled_only: Only return enabled servers
            
        Returns:
            List of server configurations
        """
        servers = list(self._servers.values())
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return servers
    
    def list_server_names(self) -> List[str]:
        """List all registered server names."""
        return list(self._servers.keys())
    
    def is_registered(self, name: str) -> bool:
        """Check if a server is registered."""
        return name in self._servers
    
    def enable(self, name: str) -> bool:
        """
        Enable a server.
        
        Args:
            name: Server name
            
        Returns:
            True if enabled
        """
        if name in self._servers:
            self._servers[name].enabled = True
            self._save_config()
            return True
        return False
    
    def disable(self, name: str) -> bool:
        """
        Disable a server.
        
        Args:
            name: Server name
            
        Returns:
            True if disabled
        """
        if name in self._servers:
            self._servers[name].enabled = False
            self._save_config()
            return True
        return False
    
    def update(self, name: str, **kwargs: Any) -> Optional[MCPServerConfig]:
        """
        Update a server configuration.
        
        Args:
            name: Server name
            **kwargs: Fields to update
            
        Returns:
            Updated configuration or None
        """
        if name not in self._servers:
            return None
        
        server = self._servers[name]
        for key, value in kwargs.items():
            if hasattr(server, key):
                setattr(server, key, value)
        
        self._save_config()
        return server
    
    def get_auto_connect_servers(self) -> List[MCPServerConfig]:
        """Get servers configured for auto-connect."""
        return [s for s in self._servers.values() if s.auto_connect and s.enabled]
    
    def import_from_file(self, filepath: Path) -> int:
        """
        Import server configurations from a file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Number of servers imported
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            servers = data if isinstance(data, list) else data.get("servers", [])
            
            for server_data in servers:
                if isinstance(server_data, dict):
                    config = MCPServerConfig.from_dict(server_data)
                    self._servers[config.name] = config
                    count += 1
            
            self._save_config()
            return count
        except (json.JSONDecodeError, KeyError, TypeError):
            return 0
    
    def export_to_file(self, filepath: Path) -> bool:
        """
        Export server configurations to a file.
        
        Args:
            filepath: Path to save to
            
        Returns:
            True if exported successfully
        """
        try:
            data = {
                "servers": [s.to_dict() for s in self._servers.values()]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except (IOError, TypeError):
            return False
    
    def clear(self) -> None:
        """Remove all registered servers."""
        self._servers.clear()
        self._save_config()


def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance."""
    return MCPRegistry()
