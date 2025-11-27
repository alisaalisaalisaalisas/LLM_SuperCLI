"""
Base classes for the command system in llm_supercli.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class CommandStatus(Enum):
    """Status of command execution."""
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    PENDING = "pending"


@dataclass
class CommandResult:
    """Result of a command execution."""
    status: CommandStatus = CommandStatus.SUCCESS
    message: str = ""
    data: Any = None
    should_exit: bool = False
    should_clear: bool = False
    errors: List[str] = field(default_factory=list)
    
    @property
    def is_success(self) -> bool:
        """Check if command succeeded."""
        return self.status == CommandStatus.SUCCESS
    
    @property
    def is_error(self) -> bool:
        """Check if command failed."""
        return self.status == CommandStatus.ERROR
    
    @classmethod
    def success(cls, message: str = "", data: Any = None) -> 'CommandResult':
        """Create a success result."""
        return cls(status=CommandStatus.SUCCESS, message=message, data=data)
    
    @classmethod
    def error(cls, message: str, errors: Optional[List[str]] = None) -> 'CommandResult':
        """Create an error result."""
        return cls(
            status=CommandStatus.ERROR,
            message=message,
            errors=errors or [message]
        )
    
    @classmethod
    def exit(cls, message: str = "Goodbye!") -> 'CommandResult':
        """Create an exit result."""
        return cls(status=CommandStatus.SUCCESS, message=message, should_exit=True)
    
    @classmethod
    def clear(cls) -> 'CommandResult':
        """Create a clear screen result."""
        return cls(status=CommandStatus.SUCCESS, should_clear=True)


class SlashCommand(ABC):
    """
    Base class for all slash commands.
    
    All commands must inherit from this class and implement the run method.
    Commands are auto-discovered and registered based on their class attributes.
    """
    
    name: str = ""
    description: str = ""
    aliases: List[str] = []
    usage: str = ""
    examples: List[str] = []
    hidden: bool = False
    requires_auth: bool = False
    
    def __init__(self) -> None:
        """Initialize the command."""
        if not self.name:
            self.name = self.__class__.__name__.lower().replace("command", "")
    
    @abstractmethod
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """
        Execute the command.
        
        Args:
            args: Command arguments as a string
            **kwargs: Additional context (session, config, etc.)
            
        Returns:
            CommandResult with execution status
        """
        pass
    
    async def run_async(self, args: str = "", **kwargs: Any) -> CommandResult:
        """
        Execute the command asynchronously.
        
        Default implementation calls the sync run method.
        Override for async operations.
        """
        return self.run(args, **kwargs)
    
    def get_help(self) -> str:
        """Get detailed help text for the command."""
        parts = [
            f"**/{self.name}** - {self.description}",
        ]
        
        if self.usage:
            parts.append(f"\n**Usage:** `/{self.name} {self.usage}`")
        
        if self.aliases:
            parts.append(f"\n**Aliases:** {', '.join(self.aliases)}")
        
        if self.examples:
            parts.append("\n**Examples:**")
            for example in self.examples:
                parts.append(f"  `{example}`")
        
        return "\n".join(parts)
    
    def validate_args(self, args: str) -> Optional[str]:
        """
        Validate command arguments.
        
        Args:
            args: Arguments string
            
        Returns:
            Error message if invalid, None if valid
        """
        return None
    
    def parse_args(self, args: str) -> dict:
        """
        Parse command arguments into a dictionary.
        
        Override for custom argument parsing.
        """
        parts = args.split()
        result = {"_raw": args, "_parts": parts}
        
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                result[key.lstrip("-")] = value
            elif part.startswith("--"):
                result[part[2:]] = True
            elif part.startswith("-"):
                result[part[1:]] = True
        
        return result
    
    def __repr__(self) -> str:
        return f"<SlashCommand /{self.name}>"


class AsyncSlashCommand(SlashCommand):
    """Base class for async-only commands."""
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Sync wrapper - raises error as this command is async-only."""
        import asyncio
        return asyncio.run(self.run_async(args, **kwargs))
    
    @abstractmethod
    async def run_async(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute the command asynchronously."""
        pass


class CommandGroup(SlashCommand):
    """
    A command that groups subcommands.
    
    Used for commands like /mcp that have subcommands (list, connect, etc.)
    """
    
    subcommands: dict = {}
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Route to subcommand or show help."""
        parts = args.split(maxsplit=1)
        subcommand = parts[0] if parts else ""
        subargs = parts[1] if len(parts) > 1 else ""
        
        if not subcommand or subcommand == "help":
            return self._show_help()
        
        if subcommand in self.subcommands:
            handler = self.subcommands[subcommand]
            if callable(handler):
                return handler(subargs, **kwargs)
        
        return CommandResult.error(
            f"Unknown subcommand: {subcommand}. "
            f"Available: {', '.join(self.subcommands.keys())}"
        )
    
    def _show_help(self) -> CommandResult:
        """Show help for this command group."""
        lines = [f"**/{self.name}** - {self.description}", "", "**Subcommands:**"]
        for name, handler in self.subcommands.items():
            doc = handler.__doc__ or "No description"
            lines.append(f"  **{name}** - {doc.split(chr(10))[0]}")
        return CommandResult.success("\n".join(lines))
    
    def register_subcommand(self, name: str, handler: callable) -> None:
        """Register a subcommand handler."""
        self.subcommands[name] = handler
