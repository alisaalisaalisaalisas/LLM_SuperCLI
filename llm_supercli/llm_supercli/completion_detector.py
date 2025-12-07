"""
Completion detection for LLM responses.

Determines if an LLM response represents genuine task completion by detecting
incomplete action phrases and hallucinated completion claims.

Requirements: 1.1, 1.2, 1.3 - Session completion detection
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CompletionResult:
    """Result of completion detection analysis.
    
    Attributes:
        is_complete: Whether the response represents genuine completion.
        reason: The reason for the completion status.
        should_continue: Whether the conversation loop should continue.
        continuation_prompt: Optional prompt to send if continuing.
    """
    is_complete: bool
    reason: str  # "substantive_response", "pending_action", "hallucination", "empty"
    should_continue: bool
    continuation_prompt: Optional[str] = None


class CompletionDetector:
    """Detects whether LLM response indicates task completion.
    
    Analyzes response content to determine if the LLM has genuinely completed
    its task or if it has incomplete actions or is hallucinating completion.
    
    Requirements:
    - 1.1: Detect incomplete action phrases and prompt continuation
    - 1.2: Continue loop after tool execution
    - 1.3: End loop on substantive response without pending actions
    """
    
    # Patterns indicating the model said it would do something but hasn't yet
    # These phrases suggest pending actions that weren't executed
    INCOMPLETE_PATTERNS: list[str] = [
        r"(?i)\blet me\b.*\b(check|look|analyze|examine|read|list|search|find|create|write|make)\b",
        r"(?i)\bi'?ll\b.*\b(check|look|analyze|examine|read|list|search|find|create|write|make)\b",
        r"(?i)\bi will\b.*\b(check|look|analyze|examine|read|list|search|find|create|write|make)\b",
        r"(?i)\bfirst,?\s+i'?ll\b",
        r"(?i)\blet's\b.*\b(check|look|analyze|examine|read|list|search|find|create|write|make)\b",
        r"(?i)\bnow i'?ll\b.*\b(create|write|make|add)\b",
        r"(?i)\bnext,?\s+i'?ll\b",
    ]
    
    # Patterns indicating the model falsely claims it already completed the task
    # These suggest hallucination when the response is too short to contain real analysis
    HALLUCINATION_PATTERNS: list[str] = [
        r"(?i)\bi'?ve (already|just) (completed|provided|given|done|finished)",
        r"(?i)\b(already|just) (completed|provided|given|done|finished).*analysis",
        r"(?i)\bbased on my (previous|earlier) (analysis|exploration|review)",
        r"(?i)\bas (i|I) (mentioned|said|explained|described) (earlier|before|above)",
    ]
    
    # Minimum length for a response to be considered a real analysis
    MIN_ANALYSIS_LENGTH: int = 500
    
    def is_complete(self, response: str, tool_calls_made: bool = False) -> CompletionResult:
        """Check if response represents genuine completion.
        
        Analyzes the response to determine if the LLM has genuinely completed
        its task or if continuation is needed.
        
        Args:
            response: The LLM response content.
            tool_calls_made: Whether tool calls were executed in this iteration.
            
        Returns:
            CompletionResult with completion status and continuation info.
            
        Requirements:
        - 1.1: Return should_continue=True for incomplete phrases
        - 1.2: Return should_continue=True after tool execution
        - 1.3: Return is_complete=True for substantive responses
        """
        # Empty or whitespace-only response
        if not response or not response.strip():
            return CompletionResult(
                is_complete=False,
                reason="empty",
                should_continue=True,
                continuation_prompt="Please provide a substantive response. If you need to analyze something, use the available tools (list_directory, read_file, etc.)."
            )
        
        # If tools were called, continue to let LLM process results
        # Requirements: 1.2 - Continue loop after tool execution
        if tool_calls_made:
            return CompletionResult(
                is_complete=False,
                reason="tool_execution",
                should_continue=True,
                continuation_prompt="Based on these results, provide your analysis now. Do NOT say you already provided an analysis - you have not shown any analysis to the user yet. Present your findings clearly."
            )
        
        # Check for pending actions (incomplete phrases)
        # Requirements: 1.1 - Detect incomplete action phrases
        if self.has_pending_action(response):
            return CompletionResult(
                is_complete=False,
                reason="pending_action",
                should_continue=True,
                continuation_prompt="Please proceed with the action you mentioned. Use the available tools (list_directory, read_file, etc.) to complete the task."
            )
        
        # Check for hallucinated completion claims
        if self.is_hallucinating_completion(response, len(response)):
            return CompletionResult(
                is_complete=False,
                reason="hallucination",
                should_continue=True,
                continuation_prompt="You have NOT provided any analysis yet - the user has not seen any analysis from you. Please provide your actual detailed analysis NOW based on the files you read."
            )
        
        # Substantive response without pending actions
        # Requirements: 1.3 - End loop on substantive response
        return CompletionResult(
            is_complete=True,
            reason="substantive_response",
            should_continue=False,
            continuation_prompt=None
        )
    
    def has_pending_action(self, response: str) -> bool:
        """Check if response indicates pending action without tool call.
        
        Detects phrases like "Let me check...", "I'll analyze..." that suggest
        the model intends to do something but hasn't executed it yet.
        
        Args:
            response: The LLM response content.
            
        Returns:
            True if the response contains incomplete action phrases.
            
        Requirements: 1.1 - Detect incomplete action phrases
        """
        if not response:
            return False
        
        for pattern in self.INCOMPLETE_PATTERNS:
            if re.search(pattern, response):
                return True
        
        return False
    
    def is_hallucinating_completion(self, response: str, response_length: int) -> bool:
        """Check if LLM falsely claims it already completed the task.
        
        Detects when the model claims to have already provided analysis
        but the response is too short to contain meaningful content.
        
        Args:
            response: The LLM response content.
            response_length: Length of the response for threshold checking.
            
        Returns:
            True if the model appears to be hallucinating completion.
        """
        if not response:
            return False
        
        # Only check for hallucination if response is short
        # Real analysis should be longer than MIN_ANALYSIS_LENGTH
        if response_length >= self.MIN_ANALYSIS_LENGTH:
            return False
        
        for pattern in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, response):
                return True
        
        return False
