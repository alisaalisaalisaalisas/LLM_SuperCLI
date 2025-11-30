"""
FormattingSection - Renders markdown formatting and response guidelines.

This section appears last in the prompt (order: 60) and provides
instructions for how responses should be formatted.
"""

from .base import PromptSection, SectionContext


class FormattingSection(PromptSection):
    """Renders markdown formatting and response guidelines.
    
    The FormattingSection provides instructions for how the LLM should
    format its responses, including markdown guidelines and response
    structure recommendations.
    
    Example output:
        # Response Formatting
        
        ## Markdown Guidelines
        
        - Use code blocks with language specifiers for code
        - Use headers to organize long responses
        - Use bullet points for lists
        
        ## Response Structure
        
        - Be concise and direct
        - Explain your reasoning when making changes
        - Provide complete, working code examples
    """
    
    @property
    def name(self) -> str:
        """Section identifier."""
        return "formatting"
    
    @property
    def order(self) -> int:
        """Sort order - last section in prompt."""
        return 60
    
    def render(self, context: SectionContext) -> str:
        """Render formatting guidelines.
        
        Args:
            context: The SectionContext (used for mode-specific formatting).
            
        Returns:
            Formatted guidelines section.
        """
        lines = [
            "# Response Formatting",
            "",
            "## Markdown Guidelines",
            "",
            "- Use fenced code blocks with language specifiers for all code",
            "  Example: ```python, ```javascript, ```bash",
            "- Use headers (##, ###) to organize long responses",
            "- Use bullet points or numbered lists for sequential steps",
            "- Use inline code (`backticks`) for file names, commands, and short code references",
            "- Use bold (**text**) sparingly for emphasis on key points",
            "",
            "## Response Structure",
            "",
            "- Be concise and direct in explanations",
            "- Lead with the most important information",
            "- Explain your reasoning when making significant changes",
            "- Provide complete, working code examples when possible",
            "- Include relevant error handling in code samples",
            "- Note any assumptions or prerequisites",
        ]
        
        # Add mode-specific formatting guidelines
        mode_guidelines = self._get_mode_specific_guidelines(context)
        if mode_guidelines:
            lines.append("")
            lines.append("## Mode-Specific Guidelines")
            lines.append("")
            lines.extend(mode_guidelines)
        
        return "\n".join(lines)
    
    def _get_mode_specific_guidelines(self, context: SectionContext) -> list[str]:
        """Get formatting guidelines specific to the current mode.
        
        Args:
            context: The SectionContext containing mode configuration.
            
        Returns:
            List of mode-specific guideline strings.
        """
        mode_slug = context.mode.slug
        
        guidelines: dict[str, list[str]] = {
            "code": [
                "- Focus on practical, implementable solutions",
                "- Include type hints in Python code",
                "- Add brief comments for complex logic",
                "- Consider edge cases and error handling",
            ],
            "ask": [
                "- Provide clear, educational explanations",
                "- Use examples to illustrate concepts",
                "- Reference documentation when helpful",
                "- Avoid making changes unless explicitly requested",
            ],
            "architect": [
                "- Focus on high-level design and structure",
                "- Use diagrams (Mermaid) when helpful",
                "- Consider scalability and maintainability",
                "- Discuss trade-offs between approaches",
            ],
        }
        
        return guidelines.get(mode_slug, [])
