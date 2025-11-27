"""
Configuration management for llm_supercli.
Handles loading, saving, and accessing configuration from JSON files and environment variables.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_THEME,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
)


@dataclass
class LLMConfig:
    """LLM-specific configuration."""
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    system_prompt: Optional[str] = None


@dataclass
class UIConfig:
    """UI-specific configuration."""
    theme: str = DEFAULT_THEME
    show_token_count: bool = True
    show_cost: bool = True
    markdown_rendering: bool = True
    syntax_highlighting: bool = True
    streaming: bool = True


@dataclass
class AuthConfig:
    """Authentication configuration."""
    google_token: Optional[str] = None
    github_token: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None


@dataclass
class MCPConfig:
    """MCP configuration."""
    enabled: bool = True
    auto_connect: bool = False
    servers: list = field(default_factory=list)


@dataclass
class AppConfig:
    """Main application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    api_keys: dict = field(default_factory=dict)


class ConfigManager:
    """
    Manages application configuration with support for JSON files and environment variables.
    
    Environment variables take precedence over config file values for API keys.
    """
    
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._config: AppConfig = AppConfig()
        self._ensure_config_dir()
        self._load_config()
        self._load_env_vars()
    
    def _ensure_config_dir(self) -> None:
        """Create configuration directory if it doesn't exist."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if not CONFIG_FILE.exists():
            self._save_config()
            return
        
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'llm' in data:
                self._config.llm = LLMConfig(**data['llm'])
            if 'ui' in data:
                self._config.ui = UIConfig(**data['ui'])
            if 'auth' in data:
                self._config.auth = AuthConfig(**data['auth'])
            if 'mcp' in data:
                self._config.mcp = MCPConfig(**data['mcp'])
            if 'api_keys' in data:
                self._config.api_keys = data['api_keys']
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Failed to load config file: {e}")
            self._config = AppConfig()
    
    def _load_env_vars(self) -> None:
        """Load API keys from environment variables."""
        env_keys = [
            'GROQ_API_KEY',
            'OPENROUTER_API_KEY',
            'TOGETHER_API_KEY',
            'HF_API_KEY',
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY',
        ]
        
        for key in env_keys:
            value = os.environ.get(key)
            if value:
                self._config.api_keys[key] = value
    
    def _save_config(self) -> None:
        """Save current configuration to JSON file."""
        data = {
            'llm': asdict(self._config.llm),
            'ui': asdict(self._config.ui),
            'auth': asdict(self._config.auth),
            'mcp': asdict(self._config.mcp),
            'api_keys': {k: v for k, v in self._config.api_keys.items() 
                        if not k.endswith('_KEY')},  # Don't save env-loaded keys
        }
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config
    
    @property
    def llm(self) -> LLMConfig:
        """Get LLM configuration."""
        return self._config.llm
    
    @property
    def ui(self) -> UIConfig:
        """Get UI configuration."""
        return self._config.ui
    
    @property
    def auth(self) -> AuthConfig:
        """Get authentication configuration."""
        return self._config.auth
    
    @property
    def mcp(self) -> MCPConfig:
        """Get MCP configuration."""
        return self._config.mcp
    
    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get an API key by name.
        
        Args:
            key_name: The name of the API key (e.g., 'GROQ_API_KEY')
            
        Returns:
            The API key value or None if not found
        """
        return self._config.api_keys.get(key_name) or os.environ.get(key_name)
    
    def set_api_key(self, key_name: str, value: str, persist: bool = False) -> None:
        """
        Set an API key.
        
        Args:
            key_name: The name of the API key
            value: The API key value
            persist: Whether to save to config file
        """
        self._config.api_keys[key_name] = value
        if persist:
            self._save_config()
    
    def update_llm(self, **kwargs: Any) -> None:
        """Update LLM configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config.llm, key):
                setattr(self._config.llm, key, value)
        self._save_config()
    
    def update_ui(self, **kwargs: Any) -> None:
        """Update UI configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config.ui, key):
                setattr(self._config.ui, key, value)
        self._save_config()
    
    def update_auth(self, **kwargs: Any) -> None:
        """Update authentication configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config.auth, key):
                setattr(self._config.auth, key, value)
        self._save_config()
    
    def save(self) -> None:
        """Explicitly save configuration."""
        self._save_config()
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
        self._load_env_vars()
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = AppConfig()
        self._save_config()


def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    return ConfigManager()
