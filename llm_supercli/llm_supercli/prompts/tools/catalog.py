"""
Tool catalog for generating tool descriptions in prompts.

Provides the ToolCatalog class for rendering tool descriptions based on
mode configuration and protocol format.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


# Tool group assignments for built-in tools
TOOL_GROUPS = {
    "get_current_directory": "read",
    "list_directory": "read",
    "read_file": "read",
    "write_file": "edit",
    "create_directory": "edit",
    "run_command": "execute",
}

# Built-in tool definitions in OpenAI format
BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_directory",
            "description": "Get the current working directory path",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list. Use '.' for current directory"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the directory to create"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return the output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
]


def get_builtin_tools() -> list["ToolDefinition"]:
    """Get all built-in tool definitions.
    
    Returns:
        List of ToolDefinition objects for all built-in tools.
    """
    return [ToolDefinition.from_openai_format(tool) for tool in BUILTIN_TOOLS]


@dataclass
class ToolDefinition:
    """Definition of a tool available to the LLM.
    
    Attributes:
        name: Unique identifier for the tool.
        description: Human-readable description of what the tool does.
        parameters: JSON schema for the tool's parameters.
        group: Tool group for filtering (read, edit, execute, mcp).
        enabled: Whether the tool is currently enabled.
    """
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    group: str = "read"
    enabled: bool = True
    
    @classmethod
    def from_openai_format(cls, tool_dict: dict[str, Any]) -> "ToolDefinition":
        """Create a ToolDefinition from OpenAI-style tool format.
        
        Args:
            tool_dict: Tool definition in OpenAI format with 'type' and 'function' keys.
            
        Returns:
            A new ToolDefinition instance.
        """
        func = tool_dict.get("function", {})
        name = func.get("name", "")
        return cls(
            name=name,
            description=func.get("description", ""),
            parameters=func.get("parameters", {}),
            group=TOOL_GROUPS.get(name, "read"),
            enabled=True,
        )
    
    def to_openai_format(self) -> dict[str, Any]:
        """Convert this ToolDefinition to OpenAI-style tool format.
        
        Returns:
            Tool definition in OpenAI format with 'type' and 'function' keys.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class ToolCatalog:
    """Generates tool descriptions for prompts.
    
    The ToolCatalog manages a collection of tools and renders their descriptions
    in different formats based on the protocol being used (text or native).
    
    Attributes:
        tools: List of tool definitions managed by this catalog.
        disabled_tools: Set of tool names that are disabled.
    
    Example:
        from llm_supercli.tools.definitions import TOOLS
        
        catalog = ToolCatalog()
        for tool in TOOLS:
            catalog.add_tool(ToolDefinition.from_openai_format(tool))
        
        # Render for text-based protocol
        text_output = catalog.render(mode, protocol="text")
        
        # Render for native tool calling
        native_output = catalog.render(mode, protocol="native")
    """
    
    def __init__(self, tools: Optional[list[ToolDefinition]] = None) -> None:
        """Initialize the ToolCatalog.
        
        Args:
            tools: Optional list of initial tool definitions.
        """
        self._tools: list[ToolDefinition] = list(tools) if tools else []
        self._disabled_tools: set[str] = set()
    
    def add_tool(self, tool: ToolDefinition) -> None:
        """Add a tool to the catalog.
        
        Args:
            tool: The tool definition to add.
        """
        self._tools.append(tool)
    
    def add_mcp_tool(self, mcp_tool: dict[str, Any]) -> None:
        """Add an MCP tool to the catalog.
        
        Args:
            mcp_tool: MCP tool definition dictionary.
        """
        tool = ToolDefinition(
            name=mcp_tool.get("name", ""),
            description=mcp_tool.get("description", ""),
            parameters=mcp_tool.get("inputSchema", {}),
            group="mcp",
            enabled=True,
        )
        self._tools.append(tool)
    
    def disable_tool(self, name: str) -> None:
        """Disable a tool by name.
        
        Args:
            name: The name of the tool to disable.
        """
        self._disabled_tools.add(name)
    
    def enable_tool(self, name: str) -> None:
        """Enable a previously disabled tool.
        
        Args:
            name: The name of the tool to enable.
        """
        self._disabled_tools.discard(name)
    
    def is_tool_disabled(self, name: str) -> bool:
        """Check if a tool is disabled.
        
        Args:
            name: The name of the tool to check.
            
        Returns:
            True if the tool is disabled, False otherwise.
        """
        return name in self._disabled_tools
    
    @property
    def tools(self) -> list[ToolDefinition]:
        """Get all tools in the catalog."""
        return list(self._tools)
    
    @property
    def disabled_tools(self) -> set[str]:
        """Get the set of disabled tool names."""
        return set(self._disabled_tools)


    def filter_for_mode(
        self,
        mode: Any,  # ModeConfig, using Any to avoid circular import
    ) -> list[ToolDefinition]:
        """Filter tools based on mode's allowed tool groups.
        
        Returns tools whose group is in the mode's tool_groups list,
        excluding any disabled tools.
        
        Args:
            mode: The ModeConfig specifying allowed tool_groups.
            
        Returns:
            List of ToolDefinition objects that are allowed for this mode.
        """
        allowed_groups = set(mode.tool_groups) if mode.tool_groups else set()
        
        return [
            tool for tool in self._tools
            if tool.group in allowed_groups
            and tool.name not in self._disabled_tools
            and tool.enabled
        ]
    
    def render(
        self,
        mode: Any,  # ModeConfig
        protocol: str = "text",
    ) -> str:
        """Render tool descriptions for the given mode.
        
        Args:
            mode: The ModeConfig specifying allowed tool_groups.
            protocol: Either "text" for XML-style syntax or "native" for
                native tool calling (no XML examples).
                
        Returns:
            Formatted string containing tool descriptions.
        """
        filtered_tools = self.filter_for_mode(mode)
        
        if not filtered_tools:
            return ""
        
        lines = ["# Available Tools", ""]
        
        for tool in filtered_tools:
            lines.append(f"## {tool.name}")
            lines.append(f"{tool.description}")
            lines.append("")
            
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
                    lines.append("")
        
        # Add invocation syntax for text protocol only
        if protocol == "text":
            lines.extend(self._render_text_syntax(filtered_tools))
        
        return "\n".join(lines)
    
    def _render_text_syntax(self, tools: list[ToolDefinition]) -> list[str]:
        """Render Python-style tool invocation syntax examples.
        
        Args:
            tools: List of tools to generate examples for.
            
        Returns:
            List of lines containing syntax documentation.
        """
        lines = [
            "# Tool Invocation Syntax",
            "",
            "To use a tool, write a function call using this format:",
            "",
            "```python",
            "tool_name(param='value')",
            "```",
            "",
            "When telling users about available tools, describe them in plain language.",
            "Do NOT show raw XML tags or code syntax to users.",
            "Instead, explain what each tool does conversationally.",
            "",
        ]
        
        # Add workflow examples showing common tool sequences
        lines.extend(self._render_workflow_examples(tools))
        
        # Add concrete examples using actual tool names
        if tools:
            lines.append("## Individual Tool Examples")
            lines.append("")
            
            for tool in tools:
                lines.extend(self._render_tool_example(tool))
                lines.append("")
        
        return lines
    
    def _render_workflow_examples(self, tools: list[ToolDefinition]) -> list[str]:
        """Render workflow examples showing common tool sequences.
        
        Args:
            tools: List of available tools.
            
        Returns:
            List of lines containing workflow examples.
        """
        tool_names = {t.name for t in tools}
        lines = ["## Common Workflow Examples", ""]
        
        # Project Analysis Workflow
        if "list_directory" in tool_names and "read_file" in tool_names:
            lines.extend([
                "### Analyzing a Project",
                "When asked to analyze a project, ALWAYS follow this sequence:",
                "",
                "```python",
                "# Step 1: First, scan the directory structure",
                "list_directory(path='.')",
                "",
                "# Step 2: Read key files (README, config, main entry points)",
                "read_file(path='README.md')",
                "read_file(path='package.json')  # or pyproject.toml, Cargo.toml, etc.",
                "read_file(path='src/main.py')   # or index.js, main.rs, etc.",
                "",
                "# Step 3: Only AFTER reading files, provide your analysis",
                "```",
                "",
            ])
        
        # File Creation Workflow
        if "write_file" in tool_names:
            lines.extend([
                "### Creating Files or Projects",
                "When asked to create files, you MUST invoke write_file for EACH file:",
                "",
                "```python",
                "# Example: Creating a simple Python project",
                "",
                "# Step 1: Create the main file",
                "write_file(path='main.py', content='#!/usr/bin/env python3\\n\\ndef main():\\n    print(\"Hello, World!\")\\n\\nif __name__ == \"__main__\":\\n    main()\\n')",
                "",
                "# Step 2: Create additional files as needed",
                "write_file(path='requirements.txt', content='requests>=2.28.0\\npython-dotenv>=1.0.0\\n')",
                "",
                "# Step 3: Create a README",
                "write_file(path='README.md', content='# My Project\\n\\nA simple Python project.\\n')",
                "```",
                "",
                "**IMPORTANT**: Never just describe or explain code - you MUST use write_file to actually create it!",
                "",
            ])
        
        # Directory + File Creation Workflow
        if "create_directory" in tool_names and "write_file" in tool_names:
            lines.extend([
                "### Creating Nested Project Structures",
                "When creating files in subdirectories, create directories first:",
                "",
                "```python",
                "# Step 1: Create directory structure",
                "create_directory(path='src')",
                "create_directory(path='tests')",
                "",
                "# Step 2: Create files in those directories",
                "write_file(path='src/app.py', content='class App:\\n    def run(self):\\n        pass\\n')",
                "write_file(path='tests/test_app.py', content='import pytest\\nfrom src.app import App\\n\\ndef test_app():\\n    app = App()\\n    assert app is not None\\n')",
                "```",
                "",
            ])
        
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
            sample_value = self._get_sample_value(param_name, param_type, tool.name)
            example_args.append(f"{param_name}={sample_value}")
        
        lines.append("```")
        lines.append(f"{tool.name}({', '.join(example_args)})")
        lines.append("```")
        
        return lines
    
    def _get_sample_value(self, param_name: str, param_type: str, tool_name: str = "") -> str:
        """Get a sample value for a parameter based on its name, type, and tool context.
        
        Args:
            param_name: The parameter name.
            param_type: The parameter type.
            tool_name: The name of the tool (for context-specific values).
            
        Returns:
            A sample value string appropriate for the parameter.
        """
        # Tool-specific realistic values
        if tool_name == "list_directory":
            if param_name == "path":
                return "'.'"  # Current directory is the most common use case
        
        if tool_name == "read_file":
            if param_name == "path":
                return "'src/main.py'"  # Realistic file path
        
        if tool_name == "write_file":
            if param_name == "path":
                return "'src/app.py'"
            if param_name == "content":
                return "'#!/usr/bin/env python3\\n\\ndef main():\\n    print(\"Hello, World!\")\\n'"
        
        if tool_name == "create_directory":
            if param_name == "path":
                return "'src/components'"
        
        if tool_name == "run_command":
            if param_name == "command":
                return "'python --version'"
        
        # Common parameter name patterns (fallback)
        if "path" in param_name.lower():
            return "'./example.txt'"
        if "content" in param_name.lower():
            return "'# File content\\nprint(\"Hello\")\\n'"
        if "command" in param_name.lower():
            return "'echo \"Hello World\"'"
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
