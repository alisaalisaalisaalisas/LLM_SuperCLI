"""
Response validation for LLM responses.

Validates and classifies LLM responses, handling empty/malformed cases
and determining retry decisions.

Requirements: 3.1, 3.2, 3.3 - Empty response handling and retry logic
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class RetryDecision:
    """Result of retry decision analysis.
    
    Attributes:
        should_retry: Whether the request should be retried.
        reason: The reason for the retry decision.
        user_message: Message to show if not retrying.
    """
    should_retry: bool
    reason: str
    user_message: Optional[str] = None


class ResponseValidator:
    """Validates and classifies LLM responses.
    
    Determines if responses are empty, substantive, or require retry.
    Handles graceful degradation when LLM returns malformed responses.
    
    Requirements:
    - 3.1: Retry empty responses up to MAX_RETRIES times
    - 3.2: Treat whitespace/punctuation-only as empty
    - 3.3: Display helpful message when retries exhausted
    """
    
    MAX_RETRIES: int = 2
    
    # Common punctuation characters to check for empty content
    PUNCTUATION_CHARS: str = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'
    
    # Minimum length for substantive content (after stripping)
    MIN_SUBSTANTIVE_LENGTH: int = 10
    
    def is_empty(self, response: str) -> bool:
        """Check if response is empty or effectively empty.
        
        A response is considered empty if it is:
        - None or empty string
        - Contains only whitespace
        - Contains only punctuation and whitespace
        
        Args:
            response: The LLM response content.
            
        Returns:
            True if the response is empty or effectively empty.
            
        Requirements: 3.1, 3.2 - Detect empty/whitespace-only responses
        """
        if response is None:
            return True
        
        if not response:
            return True
        
        # Strip whitespace and check if anything remains
        stripped = response.strip()
        if not stripped:
            return True
        
        # Check if only punctuation remains
        # Remove all punctuation and whitespace, see if anything is left
        content_only = re.sub(rf'[\s{self.PUNCTUATION_CHARS}]+', '', stripped)
        if not content_only:
            return True
        
        return False
    
    def is_substantive(self, response: str) -> bool:
        """Check if response contains meaningful content.
        
        A substantive response has actual content beyond whitespace
        and punctuation, with a minimum length threshold.
        
        Args:
            response: The LLM response content.
            
        Returns:
            True if the response contains meaningful content.
        """
        if self.is_empty(response):
            return False
        
        # Get content without excessive whitespace
        stripped = response.strip()
        
        # Must meet minimum length for substantive content
        if len(stripped) < self.MIN_SUBSTANTIVE_LENGTH:
            return False
        
        return True
    
    def should_retry(self, response: str, retry_count: int) -> RetryDecision:
        """Determine if request should be retried.
        
        Evaluates the response and current retry count to decide
        whether to retry the request or give up.
        
        Args:
            response: The LLM response content.
            retry_count: Current number of retries attempted.
            
        Returns:
            RetryDecision with retry status and user message.
            
        Requirements:
        - 3.1: Retry empty responses up to MAX_RETRIES times
        - 3.2: Treat whitespace/punctuation-only as empty
        - 3.3: Display helpful message when retries exhausted
        """
        # If response is not empty, no retry needed
        if not self.is_empty(response):
            return RetryDecision(
                should_retry=False,
                reason="response_valid",
                user_message=None
            )
        
        # Check if we can still retry
        if retry_count < self.MAX_RETRIES:
            return RetryDecision(
                should_retry=True,
                reason="empty_response",
                user_message=None
            )
        
        # Retries exhausted
        # Requirements: 3.3 - Display helpful message when retries exhausted
        return RetryDecision(
            should_retry=False,
            reason="retries_exhausted",
            user_message="The model returned an empty response after multiple attempts. Please try rephrasing your request or check your connection."
        )
