"""
SectionManager - Manages prompt section registration and rendering.

Provides functionality to register, unregister, retrieve, and render
prompt sections in a deterministic order.
"""

from typing import Optional

from .base import PromptSection, SectionContext


class SectionManager:
    """Manages prompt section registration and rendering.
    
    The SectionManager maintains a registry of PromptSection instances
    and provides methods to render them all in order.
    
    Example:
        manager = SectionManager()
        manager.register(RoleSection())
        manager.register(ToolsSection())
        
        output = manager.render_all(context)
    """
    
    def __init__(self) -> None:
        """Initialize an empty SectionManager."""
        self._sections: dict[str, PromptSection] = {}
    
    def register(self, section: PromptSection) -> None:
        """Register a prompt section.
        
        Args:
            section: The PromptSection instance to register.
        
        Raises:
            ValueError: If a section with the same name is already registered.
        """
        if section.name in self._sections:
            raise ValueError(f"Section '{section.name}' is already registered")
        self._sections[section.name] = section
    
    def unregister(self, name: str) -> None:
        """Unregister a prompt section by name.
        
        Args:
            name: The name of the section to unregister.
        
        Raises:
            KeyError: If no section with the given name is registered.
        """
        if name not in self._sections:
            raise KeyError(f"Section '{name}' is not registered")
        del self._sections[name]
    
    def get(self, name: str) -> Optional[PromptSection]:
        """Get a registered section by name.
        
        Args:
            name: The name of the section to retrieve.
        
        Returns:
            The PromptSection instance, or None if not found.
        """
        return self._sections.get(name)
    
    def render_all(self, context: SectionContext) -> str:
        """Render all registered sections in order.
        
        Sections are rendered in ascending order by their `order` property.
        Sections that return False from `should_include()` are skipped.
        
        Args:
            context: The SectionContext to pass to each section.
        
        Returns:
            The concatenated output of all rendered sections,
            separated by double newlines.
        """
        # Sort sections by order, then by name for deterministic ordering
        sorted_sections = sorted(
            self._sections.values(),
            key=lambda s: (s.order, s.name)
        )
        
        rendered_parts = []
        for section in sorted_sections:
            if section.should_include(context):
                content = section.render(context)
                if content:  # Skip empty sections
                    rendered_parts.append(content)
        
        return "\n\n".join(rendered_parts)
    
    def list_sections(self) -> list[str]:
        """List all registered section names.
        
        Returns:
            A list of section names in registration order.
        """
        return list(self._sections.keys())
    
    def __len__(self) -> int:
        """Return the number of registered sections."""
        return len(self._sections)
    
    def __contains__(self, name: str) -> bool:
        """Check if a section is registered."""
        return name in self._sections
