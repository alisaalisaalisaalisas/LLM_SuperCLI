"""
Mode configuration schema and validation.

Provides the ModeConfig dataclass and JSON schema validation for mode definitions.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# Valid tool groups that modes can reference
VALID_TOOL_GROUPS = frozenset({"read", "edit", "execute", "mcp"})


@dataclass
class ModeConfig:
    """Configuration for an operational mode.
    
    Modes define different behavioral configurations that modify the agent's
    role and available capabilities (e.g., "code", "ask", "architect").
    
    Attributes:
        slug: Unique identifier for the mode (lowercase, alphanumeric with hyphens).
        name: Human-readable display name for the mode.
        role_definition: Description of the agent's role in this mode.
        base_instructions: Additional instructions specific to this mode.
        tool_groups: List of tool group names available in this mode.
        icon: Emoji or short string icon for the mode.
    
    Example:
        code_mode = ModeConfig(
            slug="code",
            name="Code Mode",
            role_definition="You are an expert software developer...",
            base_instructions="Focus on writing clean, maintainable code.",
            tool_groups=["read", "edit", "execute"],
            icon="💻"
        )
    """
    slug: str
    name: str
    role_definition: str
    base_instructions: str = ""
    tool_groups: list[str] = field(default_factory=list)
    icon: str = "🤖"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the mode config to a dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModeConfig":
        """Create a ModeConfig from a dictionary.
        
        Args:
            data: Dictionary containing mode configuration fields.
            
        Returns:
            A new ModeConfig instance.
            
        Raises:
            TypeError: If required fields are missing or have wrong types.
        """
        return cls(
            slug=data["slug"],
            name=data["name"],
            role_definition=data["role_definition"],
            base_instructions=data.get("base_instructions", ""),
            tool_groups=data.get("tool_groups", []),
            icon=data.get("icon", "🤖"),
        )


# JSON Schema for mode configuration validation
MODE_SCHEMA = {
    "type": "object",
    "required": ["slug", "name", "role_definition"],
    "properties": {
        "slug": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9-]*$",
            "minLength": 1,
            "maxLength": 50,
        },
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
        },
        "role_definition": {
            "type": "string",
            "minLength": 10,
        },
        "base_instructions": {
            "type": "string",
        },
        "tool_groups": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": list(VALID_TOOL_GROUPS),
            },
        },
        "icon": {
            "type": "string",
            "maxLength": 4,
        },
    },
    "additionalProperties": False,
}


class ModeValidationError(Exception):
    """Raised when mode configuration validation fails."""
    
    def __init__(self, message: str, errors: Optional[list[str]] = None):
        super().__init__(message)
        self.errors = errors or []


def validate_mode_config(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a mode configuration dictionary against the schema.
    
    Performs validation without external dependencies by checking:
    - Required fields are present
    - Field types are correct
    - String patterns and lengths are valid
    - Tool groups contain only valid values
    
    Args:
        data: Dictionary containing mode configuration to validate.
        
    Returns:
        A tuple of (is_valid, errors) where is_valid is True if validation
        passed and errors is a list of error messages (empty if valid).
    
    Example:
        is_valid, errors = validate_mode_config({
            "slug": "code",
            "name": "Code Mode",
            "role_definition": "You are an expert developer..."
        })
        if not is_valid:
            print(f"Validation failed: {errors}")
    """
    errors: list[str] = []
    
    # Check it's a dictionary
    if not isinstance(data, dict):
        return False, ["Configuration must be a dictionary"]
    
    # Check required fields
    required_fields = ["slug", "name", "role_definition"]
    for field_name in required_fields:
        if field_name not in data:
            errors.append(f"Missing required field: '{field_name}'")
    
    # If required fields are missing, return early
    if errors:
        return False, errors
    
    # Validate slug
    slug = data.get("slug")
    if not isinstance(slug, str):
        errors.append("Field 'slug' must be a string")
    elif len(slug) < 1:
        errors.append("Field 'slug' must not be empty")
    elif len(slug) > 50:
        errors.append("Field 'slug' must be at most 50 characters")
    elif not _is_valid_slug(slug):
        errors.append(
            "Field 'slug' must start with a lowercase letter and contain "
            "only lowercase letters, numbers, and hyphens"
        )
    
    # Validate name
    name = data.get("name")
    if not isinstance(name, str):
        errors.append("Field 'name' must be a string")
    elif len(name) < 1:
        errors.append("Field 'name' must not be empty")
    elif len(name) > 100:
        errors.append("Field 'name' must be at most 100 characters")
    
    # Validate role_definition
    role_def = data.get("role_definition")
    if not isinstance(role_def, str):
        errors.append("Field 'role_definition' must be a string")
    elif len(role_def) < 10:
        errors.append("Field 'role_definition' must be at least 10 characters")
    
    # Validate optional base_instructions
    if "base_instructions" in data:
        base_inst = data["base_instructions"]
        if not isinstance(base_inst, str):
            errors.append("Field 'base_instructions' must be a string")
    
    # Validate optional tool_groups
    if "tool_groups" in data:
        tool_groups = data["tool_groups"]
        if not isinstance(tool_groups, list):
            errors.append("Field 'tool_groups' must be an array")
        else:
            for i, group in enumerate(tool_groups):
                if not isinstance(group, str):
                    errors.append(f"Field 'tool_groups[{i}]' must be a string")
                elif group not in VALID_TOOL_GROUPS:
                    errors.append(
                        f"Field 'tool_groups[{i}]' has invalid value '{group}'. "
                        f"Valid values are: {', '.join(sorted(VALID_TOOL_GROUPS))}"
                    )
    
    # Validate optional icon
    if "icon" in data:
        icon = data["icon"]
        if not isinstance(icon, str):
            errors.append("Field 'icon' must be a string")
        elif len(icon) > 4:
            errors.append("Field 'icon' must be at most 4 characters")
    
    # Check for unknown fields
    known_fields = {"slug", "name", "role_definition", "base_instructions", "tool_groups", "icon"}
    unknown_fields = set(data.keys()) - known_fields
    if unknown_fields:
        errors.append(f"Unknown fields: {', '.join(sorted(unknown_fields))}")
    
    return len(errors) == 0, errors


def _is_valid_slug(slug: str) -> bool:
    """Check if a slug matches the required pattern.
    
    Pattern: starts with lowercase letter, followed by lowercase letters,
    numbers, or hyphens.
    """
    if not slug:
        return False
    
    # Must start with lowercase letter
    if not slug[0].islower() or not slug[0].isalpha():
        return False
    
    # Rest must be lowercase letters, numbers, or hyphens
    for char in slug[1:]:
        if not (char.islower() or char.isdigit() or char == '-'):
            return False
    
    return True
