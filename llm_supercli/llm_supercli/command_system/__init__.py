"""Command system for llm_supercli."""
from .base import SlashCommand, CommandResult
from .parser import CommandParser
from .registry import CommandRegistry, get_command_registry

__all__ = [
    'SlashCommand', 'CommandResult',
    'CommandParser',
    'CommandRegistry', 'get_command_registry'
]
