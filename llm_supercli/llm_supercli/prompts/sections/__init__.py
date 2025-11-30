"""
Prompt sections module.

Provides the base classes and manager for composable prompt sections.
"""

from .base import PromptSection, SectionContext, ModeConfig, ToolDefinition
from .manager import SectionManager
from .role import RoleSection
from .capabilities import CapabilitiesSection
from .tools import ToolsSection
from .rules import RulesSection
from .environment import EnvironmentSection
from .formatting import FormattingSection

__all__ = [
    "PromptSection",
    "SectionContext",
    "SectionManager",
    "ModeConfig",
    "ToolDefinition",
    "RoleSection",
    "CapabilitiesSection",
    "ToolsSection",
    "RulesSection",
    "EnvironmentSection",
    "FormattingSection",
]
