"""
Context window calculation for LLM sessions.

Calculates and tracks context window usage percentage based on
token estimation from message content.

Requirements: 2.1, 2.2, 2.3, 2.4 - Context percentage calculation
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextMetrics:
    """Metrics for context window usage.
    
    Attributes:
        total_tokens: Estimated total tokens in the context.
        percentage: Context usage as percentage (0-100).
        message_count: Number of messages in the context.
    """
    total_tokens: int
    percentage: int
    message_count: int


class ContextCalculator:
    """Calculates context window usage percentage.
    
    Provides consistent token estimation and context percentage
    calculation for session tracking and status display.
    
    Requirements:
    - 2.1: Recalculate context percentage when messages are added
    - 2.2: Display percentage between 0% and 100%
    - 2.3: Display 0% for empty/new sessions
    - 2.4: Use consistent estimation method (chars / 4)
    """
    
    # Consistent estimation ratio: approximately 4 characters per token
    # This is a common heuristic for English text
    CHARS_PER_TOKEN: int = 4
    
    def estimate_tokens(self, content: str) -> int:
        """Estimate token count from content string.
        
        Uses a consistent character-to-token ratio for estimation.
        This provides a reasonable approximation without requiring
        actual tokenization.
        
        Args:
            content: The text content to estimate tokens for.
            
        Returns:
            Estimated token count (always >= 0).
            
        Requirements: 2.4 - Use consistent estimation method
        """
        if not content:
            return 0
        
        # Use integer division for consistent results
        return len(content) // self.CHARS_PER_TOKEN
    
    def get_total_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Get total estimated tokens across all messages.
        
        Iterates through all messages and sums their estimated
        token counts based on content.
        
        Args:
            messages: List of message dictionaries with 'content' key.
            
        Returns:
            Total estimated tokens across all messages.
            
        Requirements: 2.1 - Calculate based on total token count
        """
        if not messages:
            return 0
        
        total = 0
        for message in messages:
            content = message.get("content", "")
            if content:
                # Handle both string content and structured content
                if isinstance(content, str):
                    total += self.estimate_tokens(content)
                elif isinstance(content, list):
                    # Handle multi-part content (e.g., text + images)
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            total += self.estimate_tokens(part["text"])
                        elif isinstance(part, str):
                            total += self.estimate_tokens(part)
        
        return total
    
    def calculate_percentage(self, messages: list[dict[str, Any]], max_tokens: int) -> int:
        """Calculate context usage as percentage (0-100).
        
        Computes the percentage of the context window that is
        currently being used based on estimated token count.
        
        Args:
            messages: List of message dictionaries with 'content' key.
            max_tokens: Maximum tokens allowed in the context window.
            
        Returns:
            Context usage percentage as integer in range [0, 100].
            
        Requirements:
        - 2.2: Return value between 0% and 100%
        - 2.3: Return 0% for empty sessions
        """
        # Handle empty sessions
        # Requirements: 2.3 - Display 0% for empty/new sessions
        if not messages:
            return 0
        
        # Handle invalid max_tokens
        if max_tokens <= 0:
            return 0
        
        total_tokens = self.get_total_tokens(messages)
        
        # Calculate percentage
        percentage = (total_tokens * 100) // max_tokens
        
        # Clamp to [0, 100] range
        # Requirements: 2.2 - Display percentage between 0% and 100%
        return max(0, min(100, percentage))
    
    def get_metrics(self, messages: list[dict[str, Any]], max_tokens: int) -> ContextMetrics:
        """Get comprehensive context metrics.
        
        Convenience method to get all context metrics at once.
        
        Args:
            messages: List of message dictionaries with 'content' key.
            max_tokens: Maximum tokens allowed in the context window.
            
        Returns:
            ContextMetrics with total tokens, percentage, and message count.
        """
        total_tokens = self.get_total_tokens(messages)
        percentage = self.calculate_percentage(messages, max_tokens)
        message_count = len(messages) if messages else 0
        
        return ContextMetrics(
            total_tokens=total_tokens,
            percentage=percentage,
            message_count=message_count
        )
