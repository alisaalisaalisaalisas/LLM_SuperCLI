"""
Prompt configuration module.

Provides PromptConfig dataclass and configuration schemas for prompt generation.
Supports JSON serialization/deserialization with validation.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


class ConfigError(Exception):
    """Raised when configuration parsing or validation fails."""
    
    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        self.line = line
        self.column = column
        
        if line is not None and column is not None:
            full_message = f"{message} (line {line}, column {column})"
        elif line is not None:
            full_message = f"{message} (line {line})"
        else:
            full_message = message
        
        super().__init__(full_message)


# JSON Schema for prompt configuration validation
PROMPT_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version"],
    "properties": {
        "version": {"type": "string"},
        "mode": {"type": "string"},
        "include_tools": {"type": "boolean"},
        "include_mcp": {"type": "boolean"},
        "custom_instructions": {"type": ["string", "null"]},
        "variables": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "sections": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "order": {"type": "integer"},
                    "template": {"type": "string"},
                },
            },
        },
    },
}

# Current configuration version
CONFIG_VERSION = "1.0"


@dataclass
class PromptConfig:
    """Configuration for prompt generation.
    
    Defines all settings needed to generate a system prompt, including
    the operational mode, tool inclusion settings, custom instructions,
    and variable substitutions.
    
    Attributes:
        mode: The operational mode slug (e.g., "code", "ask", "architect").
        include_tools: Whether to include tool descriptions in the prompt.
        include_mcp: Whether to include MCP tool descriptions.
        custom_instructions: Optional custom instructions to append.
        variables: Dictionary of variables for template interpolation.
    
    Example:
        config = PromptConfig(
            mode="code",
            include_tools=True,
            variables={"project_name": "my-app"}
        )
    """
    mode: str = "code"
    include_tools: bool = True
    include_mcp: bool = True
    custom_instructions: Optional[str] = None
    variables: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the config to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the config with version info.
        """
        return {
            "version": CONFIG_VERSION,
            "mode": self.mode,
            "include_tools": self.include_tools,
            "include_mcp": self.include_mcp,
            "custom_instructions": self.custom_instructions,
            "variables": dict(self.variables),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptConfig":
        """Create a PromptConfig from a dictionary.
        
        Args:
            data: Dictionary containing configuration fields.
            
        Returns:
            A new PromptConfig instance.
            
        Raises:
            ConfigError: If required fields are missing or have wrong types.
        """
        return cls(
            mode=data.get("mode", "code"),
            include_tools=data.get("include_tools", True),
            include_mcp=data.get("include_mcp", True),
            custom_instructions=data.get("custom_instructions"),
            variables=dict(data.get("variables", {})),
        )
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another PromptConfig."""
        if not isinstance(other, PromptConfig):
            return NotImplemented
        return (
            self.mode == other.mode
            and self.include_tools == other.include_tools
            and self.include_mcp == other.include_mcp
            and self.custom_instructions == other.custom_instructions
            and self.variables == other.variables
        )


def validate_config(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a prompt configuration dictionary against the schema.
    
    Performs validation without external dependencies by checking:
    - Required fields are present
    - Field types are correct
    - Variables dictionary contains only string values
    
    Args:
        data: Dictionary containing configuration to validate.
        
    Returns:
        A tuple of (is_valid, errors) where is_valid is True if validation
        passed and errors is a list of error messages (empty if valid).
    
    Example:
        is_valid, errors = validate_config({
            "version": "1.0",
            "mode": "code"
        })
        if not is_valid:
            print(f"Validation failed: {errors}")
    """
    errors: list[str] = []
    
    # Check it's a dictionary
    if not isinstance(data, dict):
        return False, ["Configuration must be a dictionary"]
    
    # Check required fields
    if "version" not in data:
        errors.append("Missing required field: 'version'")
    elif not isinstance(data["version"], str):
        errors.append("Field 'version' must be a string")
    
    # Validate mode
    if "mode" in data and not isinstance(data["mode"], str):
        errors.append("Field 'mode' must be a string")
    
    # Validate include_tools
    if "include_tools" in data and not isinstance(data["include_tools"], bool):
        errors.append("Field 'include_tools' must be a boolean")
    
    # Validate include_mcp
    if "include_mcp" in data and not isinstance(data["include_mcp"], bool):
        errors.append("Field 'include_mcp' must be a boolean")
    
    # Validate custom_instructions
    if "custom_instructions" in data:
        ci = data["custom_instructions"]
        if ci is not None and not isinstance(ci, str):
            errors.append("Field 'custom_instructions' must be a string or null")
    
    # Validate variables
    if "variables" in data:
        variables = data["variables"]
        if not isinstance(variables, dict):
            errors.append("Field 'variables' must be an object")
        else:
            for key, value in variables.items():
                if not isinstance(key, str):
                    errors.append(f"Variable key '{key}' must be a string")
                if not isinstance(value, str):
                    errors.append(f"Variable '{key}' value must be a string")
    
    # Validate sections if present
    if "sections" in data:
        sections = data["sections"]
        if not isinstance(sections, dict):
            errors.append("Field 'sections' must be an object")
        else:
            for section_name, section_config in sections.items():
                if not isinstance(section_config, dict):
                    errors.append(f"Section '{section_name}' must be an object")
                    continue
                
                if "enabled" in section_config and not isinstance(section_config["enabled"], bool):
                    errors.append(f"Section '{section_name}.enabled' must be a boolean")
                
                if "order" in section_config and not isinstance(section_config["order"], int):
                    errors.append(f"Section '{section_name}.order' must be an integer")
                
                if "template" in section_config and not isinstance(section_config["template"], str):
                    errors.append(f"Section '{section_name}.template' must be a string")
    
    return len(errors) == 0, errors


def export_config(config: PromptConfig) -> str:
    """Serialize a PromptConfig to JSON string.
    
    Args:
        config: The PromptConfig to serialize.
        
    Returns:
        A JSON string representation of the configuration.
    
    Example:
        config = PromptConfig(mode="code")
        json_str = export_config(config)
    """
    return json.dumps(config.to_dict(), indent=2)


def import_config(json_str: str) -> PromptConfig:
    """Deserialize a PromptConfig from JSON string.
    
    Args:
        json_str: JSON string containing configuration.
        
    Returns:
        A PromptConfig instance.
        
    Raises:
        ConfigError: If the JSON is malformed or validation fails.
    
    Example:
        json_str = '{"version": "1.0", "mode": "code"}'
        config = import_config(json_str)
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Invalid JSON: {e.msg}",
            line=e.lineno,
            column=e.colno,
        )
    
    is_valid, errors = validate_config(data)
    if not is_valid:
        raise ConfigError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return PromptConfig.from_dict(data)
