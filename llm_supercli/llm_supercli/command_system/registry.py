"""
Command registry for llm_supercli.
Handles command registration, discovery, and lookup.
"""
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import SlashCommand, CommandResult


class CommandRegistry:
    """
    Registry for slash commands.
    
    Supports auto-discovery of commands from the commands package
    and dynamic registration of custom commands.
    """
    
    _instance: Optional['CommandRegistry'] = None
    
    def __new__(cls) -> 'CommandRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._commands: Dict[str, SlashCommand] = {}
        self._aliases: Dict[str, str] = {}
        self._discover_commands()
    
    def _discover_commands(self) -> None:
        """Auto-discover and register commands from the commands package."""
        try:
            from . import commands as commands_package
            
            package_path = Path(commands_package.__file__).parent
            
            for module_info in pkgutil.iter_modules([str(package_path)]):
                if module_info.name.startswith('_'):
                    continue
                
                try:
                    module = importlib.import_module(
                        f".commands.{module_info.name}",
                        package="llm_supercli.command_system"
                    )
                    
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type) and
                            issubclass(attr, SlashCommand) and
                            attr is not SlashCommand and
                            not attr_name.startswith('_')
                        ):
                            try:
                                instance = attr()
                                self.register(instance)
                            except Exception:
                                pass
                except Exception as e:
                    print(f"Warning: Failed to load command module {module_info.name}: {e}")
        except ImportError:
            pass
    
    def register(self, command: SlashCommand) -> None:
        """
        Register a command.
        
        Args:
            command: Command instance to register
        """
        self._commands[command.name] = command
        
        for alias in command.aliases:
            self._aliases[alias] = command.name
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a command.
        
        Args:
            name: Command name
            
        Returns:
            True if command was unregistered
        """
        if name in self._commands:
            command = self._commands[name]
            for alias in command.aliases:
                if alias in self._aliases:
                    del self._aliases[alias]
            del self._commands[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[SlashCommand]:
        """
        Get a command by name or alias.
        
        Args:
            name: Command name or alias
            
        Returns:
            Command instance or None
        """
        name = name.lower()
        
        if name in self._commands:
            return self._commands[name]
        
        if name in self._aliases:
            return self._commands[self._aliases[name]]
        
        return None
    
    def execute(self, name: str, args: str = "", **kwargs) -> CommandResult:
        """
        Execute a command by name.
        
        Args:
            name: Command name
            args: Command arguments
            **kwargs: Additional context
            
        Returns:
            CommandResult from execution
        """
        command = self.get(name)
        
        if command is None:
            return CommandResult.error(
                f"Unknown command: /{name}. Type /help for available commands."
            )
        
        validation_error = command.validate_args(args)
        if validation_error:
            return CommandResult.error(validation_error)
        
        try:
            return command.run(args, **kwargs)
        except Exception as e:
            return CommandResult.error(f"Command error: {e}")
    
    async def execute_async(self, name: str, args: str = "", **kwargs) -> CommandResult:
        """
        Execute a command asynchronously.
        
        Args:
            name: Command name
            args: Command arguments
            **kwargs: Additional context
            
        Returns:
            CommandResult from execution
        """
        command = self.get(name)
        
        if command is None:
            return CommandResult.error(
                f"Unknown command: /{name}. Type /help for available commands."
            )
        
        validation_error = command.validate_args(args)
        if validation_error:
            return CommandResult.error(validation_error)
        
        try:
            return await command.run_async(args, **kwargs)
        except Exception as e:
            return CommandResult.error(f"Command error: {e}")
    
    def list_commands(self, include_hidden: bool = False) -> List[dict]:
        """
        List all registered commands.
        
        Args:
            include_hidden: Whether to include hidden commands
            
        Returns:
            List of command info dicts
        """
        commands = []
        for name, command in sorted(self._commands.items()):
            if command.hidden and not include_hidden:
                continue
            commands.append({
                "name": name,
                "description": command.description,
                "aliases": command.aliases,
                "usage": command.usage,
                "requires_auth": command.requires_auth
            })
        return commands
    
    def list_command_names(self) -> List[str]:
        """List all command names (including aliases)."""
        names = list(self._commands.keys())
        names.extend(self._aliases.keys())
        return sorted(set(names))
    
    def search(self, query: str) -> List[SlashCommand]:
        """
        Search commands by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching commands
        """
        query = query.lower()
        results = []
        
        for command in self._commands.values():
            if (
                query in command.name.lower() or
                query in command.description.lower() or
                any(query in alias.lower() for alias in command.aliases)
            ):
                results.append(command)
        
        return results
    
    def get_help(self, name: str) -> Optional[str]:
        """
        Get help text for a command.
        
        Args:
            name: Command name
            
        Returns:
            Help text or None
        """
        command = self.get(name)
        if command:
            return command.get_help()
        return None
    
    def has_command(self, name: str) -> bool:
        """Check if a command exists."""
        return name.lower() in self._commands or name.lower() in self._aliases
    
    @property
    def command_count(self) -> int:
        """Get number of registered commands."""
        return len(self._commands)


_registry: Optional[CommandRegistry] = None


def get_command_registry() -> CommandRegistry:
    """Get the global command registry instance."""
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry
