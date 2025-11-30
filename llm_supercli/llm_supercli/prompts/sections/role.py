"""
RoleSection - Renders the mode's role definition.

This section appears first in the prompt (order: 10) and establishes
the agent's identity and primary role based on the current mode.
"""

from .base import PromptSection, SectionContext


class RoleSection(PromptSection):
    """Renders the mode's role definition.
    
    The RoleSection is the first section in the prompt and establishes
    the agent's identity based on the current mode configuration.
    
    Example output:
        # Role
        
        You are an expert software developer who helps users write,
        debug, and improve code...
    """
    
    @property
    def name(self) -> str:
        """Section identifier."""
        return "role"
    
    @property
    def order(self) -> int:
        """Sort order - first section in prompt."""
        return 10
    
    def render(self, context: SectionContext) -> str:
        """Render the role definition from the current mode.
        
        Args:
            context: The SectionContext containing mode configuration.
            
        Returns:
            Formatted role section with the mode's role_definition.
        """
        role_definition = context.mode.role_definition
        
        lines = [
            "# Role",
            "",
            role_definition,
        ]
        
        # Include base instructions if present
        if context.mode.base_instructions:
            lines.append("")
            lines.append(context.mode.base_instructions)
        
        # Add current context prominently
        lines.append("")
        lines.append(f"You are currently working in: {context.cwd}")
        lines.append("When the user asks about 'this project' or 'current project', they mean the files in this directory.")
        
        return "\n".join(lines)
