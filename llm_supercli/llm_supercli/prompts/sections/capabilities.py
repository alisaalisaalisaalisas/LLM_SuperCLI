"""
CapabilitiesSection - Lists available capabilities based on mode and tools.

This section appears early in the prompt (order: 20) and describes
what the agent can do based on the current mode and available tools.
"""

from .base import PromptSection, SectionContext


# Capability descriptions for each tool group
TOOL_GROUP_CAPABILITIES = {
    "read": [
        "Read and analyze files in the workspace",
        "List directory contents and explore project structure",
        "Search for patterns in code and text files",
    ],
    "edit": [
        "Create, modify, and delete files",
        "Refactor code and apply changes",
        "Generate new code based on requirements",
    ],
    "execute": [
        "Run shell commands and scripts",
        "Execute build and test commands",
        "Manage development processes",
    ],
    "mcp": [
        "Use Model Context Protocol (MCP) tools",
        "Access external services and APIs through MCP servers",
    ],
}


class CapabilitiesSection(PromptSection):
    """Lists available capabilities based on mode and tools.
    
    The CapabilitiesSection describes what the agent can do in the current
    context, including environment-aware descriptions based on the OS
    and available tool groups.
    
    Example output:
        # Capabilities
        
        In this session, you can:
        - Read and analyze files in the workspace
        - Create, modify, and delete files
        - Run shell commands and scripts
        
        Environment: Windows (cmd shell)
        Working directory: C:\\Users\\dev\\project
    """
    
    @property
    def name(self) -> str:
        """Section identifier."""
        return "capabilities"
    
    @property
    def order(self) -> int:
        """Sort order - early in prompt after role."""
        return 20
    
    def render(self, context: SectionContext) -> str:
        """Render capabilities based on mode and environment.
        
        Args:
            context: The SectionContext containing mode and environment info.
            
        Returns:
            Formatted capabilities section.
        """
        lines = ["# Capabilities", ""]
        
        # Gather capabilities from tool groups
        capabilities = self._get_capabilities_for_mode(context)
        
        if capabilities:
            lines.append("In this session, you can:")
            for cap in capabilities:
                lines.append(f"- {cap}")
            lines.append("")
        
        # Add environment information
        lines.append(self._render_environment_info(context))
        
        return "\n".join(lines)
    
    def _get_capabilities_for_mode(self, context: SectionContext) -> list[str]:
        """Get capability descriptions for the current mode's tool groups.
        
        Args:
            context: The SectionContext containing mode configuration.
            
        Returns:
            List of capability description strings.
        """
        capabilities: list[str] = []
        
        for group in context.mode.tool_groups:
            group_caps = TOOL_GROUP_CAPABILITIES.get(group, [])
            capabilities.extend(group_caps)
        
        # Add MCP-specific capabilities if MCP tools are available
        if context.mcp_tools and "mcp" in context.mode.tool_groups:
            mcp_tool_names = [t.get("name", "unknown") for t in context.mcp_tools[:5]]
            if len(context.mcp_tools) > 5:
                mcp_tool_names.append(f"and {len(context.mcp_tools) - 5} more")
            capabilities.append(
                f"Access MCP tools: {', '.join(mcp_tool_names)}"
            )
        
        return capabilities
    
    def _render_environment_info(self, context: SectionContext) -> str:
        """Render environment information.
        
        Args:
            context: The SectionContext containing environment info.
            
        Returns:
            Formatted environment information string.
        """
        os_name = self._get_os_display_name(context.os_type)
        shell_name = self._get_shell_display_name(context.shell)
        
        lines = [
            f"Environment: {os_name} ({shell_name})",
            f"Working directory: {context.cwd}",
        ]
        
        return "\n".join(lines)
    
    def _get_os_display_name(self, os_type: str) -> str:
        """Get a human-readable OS name.
        
        Args:
            os_type: The os.name value (nt, posix, etc.)
            
        Returns:
            Human-readable OS name.
        """
        os_names = {
            "nt": "Windows",
            "posix": "Unix/Linux/macOS",
            "darwin": "macOS",
        }
        return os_names.get(os_type, os_type)
    
    def _get_shell_display_name(self, shell: str) -> str:
        """Get a human-readable shell name.
        
        Args:
            shell: The shell path or name.
            
        Returns:
            Human-readable shell name.
        """
        if not shell or shell == "unknown":
            return "default shell"
        
        # Extract shell name from path
        shell_lower = shell.lower()
        if "bash" in shell_lower:
            return "bash"
        elif "zsh" in shell_lower:
            return "zsh"
        elif "fish" in shell_lower:
            return "fish"
        elif "powershell" in shell_lower or "pwsh" in shell_lower:
            return "PowerShell"
        elif "cmd" in shell_lower:
            return "cmd"
        
        # Return the last component of the path
        return shell.split("/")[-1].split("\\")[-1]
