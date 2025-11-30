"""
RulesSection - Renders custom rules and instructions.

This section appears in the middle of the prompt (order: 40) and includes
user-defined rules loaded from configuration files.
"""

from .base import PromptSection, SectionContext


class RulesSection(PromptSection):
    """Renders custom rules and instructions.
    
    The RulesSection integrates with the RulesLoader to render custom
    rules from global and local configuration files. Rules are formatted
    with headers indicating their source.
    
    Example output:
        # Custom Rules
        
        ## Rules from global: coding-standards.md
        
        - Always use type hints
        - Follow PEP 8 style guide
        
        ## Rules from local: project-rules.md
        
        - Use pytest for testing
        - Keep functions under 50 lines
    """
    
    @property
    def name(self) -> str:
        """Section identifier."""
        return "rules"
    
    @property
    def order(self) -> int:
        """Sort order - middle of prompt after tools."""
        return 40
    
    def should_include(self, context: SectionContext) -> bool:
        """Include only if there are rules to render.
        
        Args:
            context: The SectionContext containing rules.
            
        Returns:
            True if there are rules to render.
        """
        return bool(context.rules)
    
    def render(self, context: SectionContext) -> str:
        """Render custom rules with source headers.
        
        Args:
            context: The SectionContext containing rules.
            
        Returns:
            Formatted rules section.
        """
        if not context.rules:
            return ""
        
        lines = ["# Custom Rules", ""]
        
        # Rules in context are already formatted strings
        # They may contain headers from the RulesLoader
        for rule in context.rules:
            lines.append(rule)
            lines.append("")
        
        return "\n".join(lines).rstrip()
