"""Message state models for the message renderer.

This module defines the core data models for tracking message rendering state,
including the MessagePhase enum for state machine transitions and the
ToolCallRecord dataclass for tracking tool call execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessagePhase(Enum):
    """Tracks the current phase of message rendering.
    
    The message renderer uses a state machine to manage transitions between
    different rendering phases. This enum defines all valid states.
    """
    IDLE = "idle"           # No active message
    THINKING = "thinking"   # Showing spinner
    REASONING = "reasoning" # Streaming reasoning content
    RESPONDING = "responding" # Streaming response content
    TOOL_CALL = "tool_call" # Displaying tool execution
    COMPLETE = "complete"   # Message finalized
    ERROR = "error"         # Error occurred


@dataclass
class ToolCallRecord:
    """Record of a tool call and its result.
    
    Represents a single tool call from the model, tracking its execution
    state and result. Used for deduplication and display management.
    
    Attributes:
        id: Unique identifier (typically hash of name + args)
        name: Tool name (e.g., 'read_file', 'write_file')
        arguments: Tool arguments as a dictionary
        result: Execution result, None if not yet executed
        success: Whether execution succeeded (default True)
        displayed: Whether the tool call header has been rendered
    """
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True
    displayed: bool = False
