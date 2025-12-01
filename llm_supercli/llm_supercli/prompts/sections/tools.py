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
        """Render Python-style tool invocation syntax examples.
        
        Args:
            tools: List of tools to generate examples for.
            
        Returns:
            List of lines containing syntax documentation.
        """
        # List available tool names explicitly
        tool_names = [t.name for t in tools]
        tool_list = ", ".join(tool_names) if tool_names else "none"
        
        lines = [
            "",
            "# Tool Invocation Syntax",
            "",
            f"**IMPORTANT: You can ONLY use these tools: {tool_list}**",
            "Do NOT invent or use any other tool names. Only the tools listed above exist.",
            "",
            "To use a tool, write a function call in your response:",
            "",
            "```",
            "tool_name('argument')",
            "tool_name('arg1', 'arg2')",
            "tool_name(param='value')",
            "```",
            "",
        ]
        
        # Add concrete examples using actual tool names
        if tools:
            lines.append("## Tool Examples")
            lines.append("")
            
            for tool in tools:
                lines.extend(self._render_tool_example(tool))
                lines.append("")
        
        return lines
    
    def _render_tool_example(self, tool: ToolDefinition) -> list[str]:
        """Render a Python-style example for a single tool.
        
        Args:
            tool: The tool definition to render an example for.
            
        Returns:
            List of lines for the tool example.
        """
        lines = [f"### {tool.name}"]
        
        props = tool.parameters.get("properties", {})
        required = set(tool.parameters.get("required", []))
        
        if not props:
            # Tool with no parameters
            lines.append("```")
            lines.append(f"{tool.name}()")
            lines.append("```")
            return lines
        
        # Build parameter signature with types
        param_parts = []
        for param_name, param_info in props.items():
            param_type = param_info.get("type", "string")
            is_required = param_name in required
            req_marker = "" if is_required else "?"
            param_parts.append(f"{param_name}: {param_type}{req_marker}")
        
        lines.append(f"Signature: `{tool.name}({', '.join(param_parts)})`")
        lines.append("")
        
        # Build example call with sample values
        example_args = []
        for param_name, param_info in props.items():
            param_type = param_info.get("type", "string")
            sample_value = self._get_sample_value(param_name, param_type)
            example_args.append(f"{param_name}={sample_value}")
        
        lines.append("```")
        lines.append(f"{tool.name}({', '.join(example_args)})")
        lines.append("```")
        
        return lines
    
    def _get_sample_value(self, param_name: str, param_type: str) -> str:
        """Get a sample value for a parameter based on its name and type.
        
        Args:
            param_name: The parameter name.
            param_type: The parameter type.
            
        Returns:
            A sample value string appropriate for the parameter.
        """
        # Common parameter name patterns
        if "path" in param_name.lower():
            return "'./example.txt'"
        if "content" in param_name.lower():
            return "'file content here'"
        if "command" in param_name.lower():
            return "'ls -la'"
        if "directory" in param_name.lower() or "dir" in param_name.lower():
            return "'./src'"
        
        # Type-based defaults
        if param_type == "string":
            return "'example'"
        if param_type == "number" or param_type == "integer":
            return "42"
        if param_type == "boolean":
            return "True"
        if param_type == "array":
            return "['item1', 'item2']"
        if param_type == "object":
            return "{'key': 'value'}"
        
        return "'value'"
