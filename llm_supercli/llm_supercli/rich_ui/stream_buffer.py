"""Stream buffer for content accumulation with deduplication.

This module provides the StreamBuffer class that manages content accumulation
during message streaming. It handles deduplication of reasoning content and
tracks which tool calls have been displayed to prevent duplicates.

Requirements addressed:
- 1.1: Append new content without clearing previous content
- 1.4: Deduplicate reasoning content
- 2.1: Display tool calls exactly once
"""

from dataclasses import dataclass, field
from typing import Optional

from llm_supercli.rich_ui.message_state import ToolCallRecord


@dataclass
class StreamBuffer:
    """Manages content accumulation with deduplication for streaming messages.
    
    The StreamBuffer accumulates streamed content (reasoning and response)
    and tracks tool calls. It provides deduplication to ensure content is
    only displayed once, even if received multiple times.
    
    Key behaviors:
    - append_reasoning() returns only NEW content not previously seen
    - append_response() returns only NEW content not previously seen
    - add_tool_call() returns True only if the tool call is new
    
    Attributes:
        reasoning: Accumulated reasoning content
        response: Accumulated response content
        tool_calls: List of tool call records
        displayed_tool_ids: Set of tool IDs that have been displayed
    """
    reasoning: str = ""
    response: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    displayed_tool_ids: set[str] = field(default_factory=set)
    
    # Track what has been displayed to enable deduplication
    _displayed_reasoning_len: int = field(default=0, repr=False)
    _displayed_response_len: int = field(default=0, repr=False)
    
    def append_reasoning(self, chunk: str) -> str:
        """Append to reasoning buffer and return only new content.
        
        This method handles deduplication by tracking what has already been
        displayed. If the incoming chunk contains content that was already
        in the buffer, only the new portion is returned.
        
        Args:
            chunk: New reasoning content to append
            
        Returns:
            The portion of content that is new (not previously displayed)
        """
        if not chunk:
            return ""
        
        # Check if this chunk is a continuation or contains duplicate content
        old_len = len(self.reasoning)
        
        # If the chunk starts with content we already have, find the new part
        if self.reasoning and chunk.startswith(self.reasoning):
            # The chunk contains all previous content plus new content
            new_content = chunk[old_len:]
            self.reasoning = chunk
        elif self.reasoning and self.reasoning.endswith(chunk[:min(len(chunk), len(self.reasoning))]):
            # Partial overlap at the end - find where new content starts
            overlap_len = self._find_overlap(self.reasoning, chunk)
            new_content = chunk[overlap_len:]
            self.reasoning += new_content
        else:
            # No overlap, just append
            new_content = chunk
            self.reasoning += chunk
        
        return new_content
    
    def append_response(self, chunk: str) -> str:
        """Append to response buffer and return only new content.
        
        Similar to append_reasoning(), this handles deduplication by tracking
        what has already been displayed.
        
        Args:
            chunk: New response content to append
            
        Returns:
            The portion of content that is new (not previously displayed)
        """
        if not chunk:
            return ""
        
        old_len = len(self.response)
        
        # If the chunk starts with content we already have, find the new part
        if self.response and chunk.startswith(self.response):
            new_content = chunk[old_len:]
            self.response = chunk
        elif self.response and self.response.endswith(chunk[:min(len(chunk), len(self.response))]):
            overlap_len = self._find_overlap(self.response, chunk)
            new_content = chunk[overlap_len:]
            self.response += new_content
        else:
            new_content = chunk
            self.response += chunk
        
        return new_content
    
    def add_tool_call(self, call: ToolCallRecord) -> bool:
        """Add a tool call if not already displayed.
        
        Checks the displayed_tool_ids set to prevent duplicate tool calls
        from being displayed. If the tool call is new, it's added to the
        list and its ID is recorded.
        
        Args:
            call: The tool call record to add
            
        Returns:
            True if the tool call was added (new), False if duplicate
        """
        if call.id in self.displayed_tool_ids:
            return False
        
        self.displayed_tool_ids.add(call.id)
        self.tool_calls.append(call)
        return True
    
    def get_tool_call(self, tool_id: str) -> Optional[ToolCallRecord]:
        """Get a tool call by its ID.
        
        Args:
            tool_id: The unique identifier of the tool call
            
        Returns:
            The ToolCallRecord if found, None otherwise
        """
        for call in self.tool_calls:
            if call.id == tool_id:
                return call
        return None
    
    def clear(self) -> None:
        """Reset all buffers for a new message.
        
        Clears all accumulated content and resets tracking state.
        Should be called when starting a new message.
        """
        self.reasoning = ""
        self.response = ""
        self.tool_calls = []
        self.displayed_tool_ids = set()
        self._displayed_reasoning_len = 0
        self._displayed_response_len = 0
    
    def _find_overlap(self, existing: str, new: str) -> int:
        """Find the length of overlap between end of existing and start of new.
        
        Args:
            existing: The existing content
            new: The new content to check for overlap
            
        Returns:
            The length of the overlapping portion
        """
        max_overlap = min(len(existing), len(new))
        for i in range(max_overlap, 0, -1):
            if existing[-i:] == new[:i]:
                return i
        return 0
