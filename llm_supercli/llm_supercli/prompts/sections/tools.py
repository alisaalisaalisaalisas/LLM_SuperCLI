"""
ToolsSection - Renders tool descriptions and invocation syntax.

This section appears in the middle of the prompt (order: 30) and provides
detailed information about available tools and how to invoke them.
"""

from typing import Optional

from .base import PromptSection, SectionContext, ToolDefinition


class ToolsSection(PromptSection):
    """Renders tool descriptions and invocation syntax.
    
    The ToolsSection integrates with the ToolCatalog to render tool
    descriptions. It includes tool invocation syntax based on the
    protocol being used (text or native).
    
    Attributes:
        protocol: The protocol format ("text" or "native").
        
    Example output (text protocol):
        # Available Tools
        
        ## read_file
        Read the contents of a file.
        
        Parameters:
        - path (required): Path to the file to read
        
        # Tool Invocation Syntax
        
        To use a tool, format your request as follows:
        ...
    """
    
    def __init__(self, protocol: str = "text") -> None:
        """Initialize the ToolsSection.
        
        Args:
            protocol: Either "text" for XML-style syntax or "native"
                for native tool calling (no XML examples).
        """
        self._protocol = protocol
    
    @property
    def name(self) -> str:
        """Section identifier."""
        return "tools"
    
    @property
    def order(self) -> int:
        """Sort order - middle of prompt."""
        return 30
    
    @property
    def protocol(self) -> str:
        """Get the current protocol."""
        return self._protocol
    
    @protocol.setter
    def protocol(self, value: str) -> None:
        """Set the protocol.
        
        Args:
            value: Either "text" or "native".
        """
        self._protocol = value
    
    def should_include(self, context: SectionContext) -> bool:
        """Include only if there are tools available.
        
        Args:
            context: The SectionContext containing tools.
            
        Returns:
            True if there are tools to render.
        """
        return bool(context.tools) or bool(context.mcp_tools)
    
    def render(self, context: SectionContext) -> str:
        """Render tool descriptions and invocation syntax.
        
        Args:
            context: The SectionContext containing tools and mode.
            
        Returns:
            Formatted tools section.
        """
        # Filter tools based on mode's tool groups
        filtered_tools = self._filter_tools_for_mode(context)
        
        if not filtered_tools and not context.mcp_tools:
            return ""
        
        lines = ["# Available Tools", ""]
        
        # Render built-in tools
        for tool in filtered_tools:
            lines.extend(self._render_tool(tool))
            lines.append("")
        
        # Render MCP tools if available and allowed
        if context.mcp_tools and "mcp" in context.mode.tool_groups:
            lines.append("## MCP Tools")
            lines.append("")
            for mcp_tool in context.mcp_tools:
                lines.extend(self._render_mcp_tool(mcp_tool))
                lines.append("")
        
        # Add invocation syntax for text protocol only
        if self._protocol == "text":
            lines.extend(self._render_text_syntax(filtered_tools))
        
        return "\n".join(lines).rstrip()
    
    def _filter_tools_for_mode(self, context: SectionContext) -> list[ToolDefinition]:
        """Filter tools based on mode's allowed tool groups.
        
        Args:
            context: The SectionContext containing tools and mode.
            
        Returns:
            List of tools allowed for the current mode.
        """
        allowed_groups = set(context.mode.tool_groups) if context.mode.tool_groups else set()
        
        return [
            tool for tool in context.tools
            if tool.group in allowed_groups
        ]
    
    def _render_tool(self, tool: ToolDefinition) -> list[str]:
        """Render a single tool definition.
        
        Args:
            tool: The tool definition to render.
            
        Returns:
            List of lines for the tool description.
        """
        lines = [
            f"## {tool.name}",
            tool.description,
            "",
        ]
        
        # Add parameter documentation
        if tool.parameters:
            props = tool.parameters.get("properties", {})
            required = set(tool.parameters.get("required", []))
            
            if props:
                lines.append("Parameters:")
                for param_name, param_info in props.items():
                    req_marker = " (required)" if param_name in required else ""
                    param_desc = param_info.get("description", "No description")
                    lines.append(f"- {param_name}{req_marker}: {param_desc}")
        
        return lines
    
    def _render_mcp_tool(self, mcp_tool: dict) -> list[str]:
        """Render an MCP tool definition.
        
        Args:
            mcp_tool: The MCP tool dictionary.
            
        Returns:
            List of lines for the MCP tool description.
        """
        name = mcp_tool.get("name", "unknown")
        description = mcp_tool.get("description", "No description available")
        
        lines = [
            f"### {name}",
            description,
            "",
        ]
        
        # Add parameter documentation from inputSchema
        input_schema = mcp_tool.get("inputSchema", {})
        if input_schema:
            props = input_schema.get("properties", {})
            required = set(input_schema.get("required", []))
            
            if props:
                lines.append("Parameters:")
                for param_name, param_info in props.items():
                    req_marker = " (required)" if param_name in required else ""
                    param_desc = param_info.get("description", "No description")
                    lines.append(f"- {param_name}{req_marker}: {param_desc}")
        
        return lines
    
    def _render_text_syntax(self, tools: list[ToolDefinition]) -> list[str]:
        """Render XML-style tool invocation syntax examples.
        
        Args:
            tools: List of tools to generate examples for.
            
        Returns:
            List of lines containing syntax documentation.
        """
        lines = [
            "",
            "# Tool Invocation Syntax",
            "",
            "To use a tool, format your request as follows:",
            "",
            "```xml",
            "<function_calls>",
            "<invoke name=\"tool_name\">",
            "<parameter name=\"param_name\">value</parameter>",
            "</invoke>",
            "</function_calls>",
            "```",
            "",
        ]
        
        # Add a concrete example using the first tool
        if tools:
            example_tool = tools[0]
            lines.append("Example:")
            lines.append("")
            lines.append("```xml")
            lines.append("<function_calls>")
            lines.append(f"<invoke name=\"{example_tool.name}\">")
            
            props = example_tool.parameters.get("properties", {})
            for param_name in list(props.keys())[:2]:  # Limit to 2 params
                lines.append(f"<parameter name=\"{param_name}\">example_value</parameter>")
            
            lines.append("</invoke>")
            lines.append("</function_calls>")
            lines.append("```")
        
        return lines
