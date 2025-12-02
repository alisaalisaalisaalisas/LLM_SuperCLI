"""
Action models for the action cards system.

This module defines the data structures that represent CLI operations
before they are rendered as visual cards.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionType(Enum):
    """Types of actions that can be rendered as cards."""
    READ_FILES = "read_files"
    SEARCH = "search"
    CREATE_FILE = "create_file"
    UPDATE_FILE = "update_file"
    THINKING = "thinking"
    DONE = "done"
    STATUS = "status"
    ERROR = "error"


@dataclass
class Action:
    """
    Base model for all actions.
    
    Attributes:
        type: The type of action being represented
        timestamp: Unix timestamp when the action occurred
        metadata: Additional key-value data for the action
    """
    type: ActionType
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadFilesAction(Action):
    """
    Action representing file read operations.
    
    Attributes:
        files: List of successfully read file paths
        failed_files: List of file paths that failed to read
    """
    files: List[str] = field(default_factory=list)
    failed_files: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        if not hasattr(self, 'type') or self.type != ActionType.READ_FILES:
            object.__setattr__(self, 'type', ActionType.READ_FILES)


@dataclass
class SearchAction(Action):
    """
    Action representing workspace search operations.
    
    Attributes:
        query: The search query or pattern used
        results_count: Number of matches found
        results_preview: Preview of matching results
    """
    query: str = ""
    results_count: int = 0
    results_preview: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        if not hasattr(self, 'type') or self.type != ActionType.SEARCH:
            object.__setattr__(self, 'type', ActionType.SEARCH)


@dataclass
class FileAction(Action):
    """
    Action representing file creation or update operations.
    
    Attributes:
        filename: Path to the file being created or updated
        content_preview: Optional preview of file content (for creation)
        change_summary: Optional summary of changes made (for updates)
    """
    filename: str = ""
    content_preview: Optional[str] = None
    change_summary: Optional[str] = None
    
    def __post_init__(self) -> None:
        # Don't override type if it's already set to CREATE_FILE or UPDATE_FILE
        if not hasattr(self, 'type') or self.type not in (ActionType.CREATE_FILE, ActionType.UPDATE_FILE):
            object.__setattr__(self, 'type', ActionType.CREATE_FILE)


@dataclass
class StatusAction(Action):
    """
    Action representing status footer with session statistics.
    
    Attributes:
        elapsed_time: Time taken for the operation in seconds
        credits_used: Optional credits consumed (None if not applicable)
        input_tokens: Optional count of input tokens
        output_tokens: Optional count of output tokens
        is_free_tier: Whether the provider is free-tier
    """
    elapsed_time: float = 0.0
    credits_used: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    is_free_tier: bool = False
    
    def __post_init__(self) -> None:
        if not hasattr(self, 'type') or self.type != ActionType.STATUS:
            object.__setattr__(self, 'type', ActionType.STATUS)


@dataclass
class ThinkingAction(Action):
    """
    Action representing the thinking/processing state.
    
    Attributes:
        message: Optional message to display during thinking
    """
    message: str = "Thinking..."
    
    def __post_init__(self) -> None:
        if not hasattr(self, 'type') or self.type != ActionType.THINKING:
            object.__setattr__(self, 'type', ActionType.THINKING)


@dataclass
class DoneAction(Action):
    """
    Action representing completion of processing.
    
    Attributes:
        message: Optional completion message
    """
    message: str = "Done!"
    
    def __post_init__(self) -> None:
        if not hasattr(self, 'type') or self.type != ActionType.DONE:
            object.__setattr__(self, 'type', ActionType.DONE)


@dataclass
class ErrorAction(Action):
    """
    Action representing an error state.
    
    Attributes:
        message: Error message to display
        details: Optional additional error details
    """
    message: str = "Error"
    details: Optional[str] = None
    
    def __post_init__(self) -> None:
        if not hasattr(self, 'type') or self.type != ActionType.ERROR:
            object.__setattr__(self, 'type', ActionType.ERROR)
