"""
Base classes for prompt sections.

Provides the PromptSection abstract base class and SectionContext dataclass
for building modular, composable prompt sections.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ModeConfig:
    """Configuration for an operational mode.
    
    This is a forward reference - the full implementation is in modes/schema.py.
    """
    slug: str
    name: str
    role_definition: str
    base_instructions: str = ""
    tool_groups: list[str] = field(default_factory=list)
    icon: str = "🤖"


@dataclass
class ToolDefinition:
    """Definition of a tool available to the LLM.
    
    This is a forward reference for type hints.
    """
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    group: str = "general"


@dataclass
class SectionContext:
    """Context passed to sections during rendering.
    
    Contains all the information a section might need to render itself,
    including mode configuration, environment details, and available tools.
    """
    mode: ModeConfig
    cwd: str
    os_type: str
    shell: str
    variables: dict[str, str] = field(default_factory=dict)
    tools: list[ToolDefinition] = field(default_factory=list)
    mcp_tools: list[dict] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)


class PromptSection(ABC):
    """Abstract base class for prompt sections.
    
    Each section represents a discrete, reusable component of a system prompt.
    Sections are rendered in order by their `order` property and can be
    independently modified, tested, and extended.
    
    Example:
        class RoleSection(PromptSection):
            @property
            def name(self) -> str:
                return "role"
            
            @property
            def order(self) -> int:
                return 10
            
            def render(self, context: SectionContext) -> str:
                return f"You are {context.mode.role_definition}"
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Section identifier.
        
        Returns:
            A unique string identifier for this section.
        """
        ...
    
    @property
    def order(self) -> int:
        """Sort order (lower = earlier in prompt).
        
        Sections are rendered in ascending order by this value.
        Default is 50, which places sections in the middle.
        
        Returns:
            An integer representing the sort order.
        """
        return 50
    
    @abstractmethod
    def render(self, context: SectionContext) -> str:
        """Render this section to text.
        
        Args:
            context: The SectionContext containing mode, environment,
                    and other information needed for rendering.
        
        Returns:
            The rendered section content as a string.
        """
        ...
    
    def should_include(self, context: SectionContext) -> bool:
        """Whether to include this section in the final prompt.
        
        Override this method to conditionally include/exclude sections
        based on the context (e.g., mode, available tools, etc.).
        
        Args:
            context: The SectionContext for the current render.
        
        Returns:
            True if the section should be included, False otherwise.
        """
        return True
