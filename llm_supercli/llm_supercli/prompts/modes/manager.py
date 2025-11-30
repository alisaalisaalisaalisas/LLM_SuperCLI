"""
Mode manager for handling operational modes.

Provides the ModeManager class for registering, retrieving, and managing
different operational modes for the CLI agent.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .schema import ModeConfig, validate_mode_config, ModeValidationError


logger = logging.getLogger(__name__)


class ModeManager:
    """Manages operational modes for the CLI agent.
    
    The ModeManager handles registration and retrieval of modes, including
    built-in modes and custom user-defined modes. It provides a default
    fallback to the "code" mode when a requested mode is not found.
    
    Attributes:
        DEFAULT_MODE: The default mode slug to use when no mode is specified
            or when a requested mode is not found.
    
    Example:
        manager = ModeManager()
        
        # Get a mode (falls back to default if not found)
        mode = manager.get("code")
        
        # Register a custom mode
        custom_mode = ModeConfig(
            slug="review",
            name="Code Review",
            role_definition="You are a code reviewer...",
            tool_groups=["read"]
        )
        manager.register(custom_mode)
        
        # List all available modes
        for mode in manager.list_modes():
            print(f"{mode.icon} {mode.name}")
    """
    
    DEFAULT_MODE = "code"
    
    def __init__(self, load_builtin: bool = True) -> None:
        """Initialize the ModeManager.
        
        Args:
            load_builtin: If True, automatically load built-in modes.
                Defaults to True.
        """
        self._modes: dict[str, ModeConfig] = {}
        self._default_mode = self.DEFAULT_MODE
        
        if load_builtin:
            self._load_builtin_modes()
    
    def _load_builtin_modes(self) -> None:
        """Load the built-in modes (code, ask, architect)."""
        from .builtin import get_builtin_modes
        
        for mode in get_builtin_modes():
            self._modes[mode.slug] = mode
            logger.debug(f"Loaded built-in mode: {mode.slug}")
    
    def register(self, mode: ModeConfig) -> None:
        """Register a mode configuration.
        
        If a mode with the same slug already exists, it will be overwritten.
        
        Args:
            mode: The ModeConfig to register.
        
        Raises:
            ValueError: If the mode configuration is invalid.
        """
        # Validate the mode before registering
        is_valid, errors = validate_mode_config(mode.to_dict())
        if not is_valid:
            raise ValueError(f"Invalid mode configuration: {'; '.join(errors)}")
        
        self._modes[mode.slug] = mode
        logger.debug(f"Registered mode: {mode.slug}")
    
    def unregister(self, slug: str) -> bool:
        """Unregister a mode by its slug.
        
        Args:
            slug: The slug of the mode to unregister.
            
        Returns:
            True if the mode was unregistered, False if it wasn't found.
        """
        if slug in self._modes:
            del self._modes[slug]
            logger.debug(f"Unregistered mode: {slug}")
            return True
        return False
    
    def get(self, slug: str) -> ModeConfig:
        """Get a mode by its slug.
        
        If the requested mode is not found, falls back to the default mode.
        If the default mode is also not found, raises a KeyError.
        
        Args:
            slug: The slug of the mode to retrieve.
            
        Returns:
            The ModeConfig for the requested mode, or the default mode
            if the requested mode is not found.
            
        Raises:
            KeyError: If neither the requested mode nor the default mode
                is registered.
        """
        if slug in self._modes:
            return self._modes[slug]
        
        # Fall back to default mode
        logger.warning(f"Mode '{slug}' not found, falling back to '{self._default_mode}'")
        
        if self._default_mode in self._modes:
            return self._modes[self._default_mode]
        
        raise KeyError(
            f"Mode '{slug}' not found and default mode '{self._default_mode}' "
            "is not registered. Register at least the default mode."
        )
    
    def has_mode(self, slug: str) -> bool:
        """Check if a mode is registered.
        
        Args:
            slug: The slug of the mode to check.
            
        Returns:
            True if the mode is registered, False otherwise.
        """
        return slug in self._modes
    
    def list_modes(self) -> list[ModeConfig]:
        """List all registered modes.
        
        Returns:
            A list of all registered ModeConfig objects, sorted by slug.
        """
        return sorted(self._modes.values(), key=lambda m: m.slug)
    
    def load_custom_modes(self, path: Path) -> int:
        """Load custom modes from a JSON file.
        
        The JSON file should contain either a single mode object or an
        array of mode objects.
        
        Args:
            path: Path to the JSON file containing mode definitions.
            
        Returns:
            The number of modes successfully loaded.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            ModeValidationError: If any mode configuration is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Mode file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle both single mode and array of modes
        if isinstance(data, dict):
            modes_data = [data]
        elif isinstance(data, list):
            modes_data = data
        else:
            raise ModeValidationError(
                f"Invalid mode file format: expected object or array, got {type(data).__name__}"
            )
        
        loaded_count = 0
        errors: list[str] = []
        
        for i, mode_data in enumerate(modes_data):
            is_valid, validation_errors = validate_mode_config(mode_data)
            if not is_valid:
                errors.append(f"Mode {i}: {'; '.join(validation_errors)}")
                continue
            
            try:
                mode = ModeConfig.from_dict(mode_data)
                self.register(mode)
                loaded_count += 1
            except Exception as e:
                errors.append(f"Mode {i}: {str(e)}")
        
        if errors:
            logger.warning(f"Some modes failed to load from {path}: {errors}")
        
        logger.info(f"Loaded {loaded_count} custom modes from {path}")
        return loaded_count
    
    def set_default_mode(self, slug: str) -> None:
        """Set the default mode slug.
        
        Args:
            slug: The slug of the mode to use as default.
        """
        self._default_mode = slug
    
    @property
    def default_mode(self) -> str:
        """Get the current default mode slug."""
        return self._default_mode
