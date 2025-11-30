"""
Mode management module.

Provides mode definitions and management for different operational behaviors.
"""

from .schema import (
    ModeConfig,
    ModeValidationError,
    MODE_SCHEMA,
    VALID_TOOL_GROUPS,
    validate_mode_config,
)
from .manager import ModeManager
from .builtin import (
    CODE_MODE,
    ASK_MODE,
    ARCHITECT_MODE,
    BUILTIN_MODES,
    get_builtin_modes,
    get_builtin_mode,
)

__all__ = [
    # Schema
    "ModeConfig",
    "ModeValidationError",
    "MODE_SCHEMA",
    "VALID_TOOL_GROUPS",
    "validate_mode_config",
    # Manager
    "ModeManager",
    # Built-in modes
    "CODE_MODE",
    "ASK_MODE",
    "ARCHITECT_MODE",
    "BUILTIN_MODES",
    "get_builtin_modes",
    "get_builtin_mode",
]
