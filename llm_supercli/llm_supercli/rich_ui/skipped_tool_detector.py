"""
Skipped tool invocation detector.

This module provides functionality to detect when an LLM describes
an action without actually invoking the appropriate tool.

Requirements: 4.4 - Warn user when tool invocation is skipped or simulated
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class SkippedToolDetection:
    """
    Result of detecting a skipped tool invocation.
    
    Attributes:
        detected: Whether a skipped tool was detected
        action_description: The action the LLM described
        suggested_tool: The tool that should have been invoked
        confidence: Confidence level (0.0 to 1.0)
    """
    detected: bool
    action_description: str = ""
    suggested_tool: str = ""
    confidence: float = 0.0


class SkippedToolDetector:
    """
    Detects when an LLM describes an action without invoking a tool.
    
    This class analyzes LLM responses to identify patterns where the
    model describes performing an action (like reading a file or
    creating a directory) without actually calling the appropriate tool.
    
    Requirements: 4.4 - Detect when LLM describes action without invoking tool
    """
    
    # Patterns that indicate the LLM is describing an action
    # Each tuple: (pattern, suggested_tool, action_description_group)
    ACTION_PATTERNS: List[Tuple[str, str, int]] = [
        # File reading patterns
        (r"(?i)(?:let me |i'?ll |i will |i'm going to )?(?:read|look at|check|examine|view|open) (?:the )?(?:file |contents of )?['\"]?([^\s'\"]+\.\w+)['\"]?", "read_file", 1),
        (r"(?i)(?:reading|looking at|checking|examining|viewing|opening) (?:the )?(?:file |contents of )?['\"]?([^\s'\"]+\.\w+)['\"]?", "read_file", 1),
        
        # File writing patterns
        (r"(?i)(?:let me |i'?ll |i will |i'm going to )?(?:create|write|save|make) (?:a )?(?:new )?(?:file )?(?:called |named )?['\"]?([^\s'\"]+\.\w+)['\"]?", "write_file", 1),
        (r"(?i)(?:creating|writing|saving|making) (?:a )?(?:new )?(?:file )?(?:called |named )?['\"]?([^\s'\"]+\.\w+)['\"]?", "write_file", 1),
        
        # Directory listing patterns
        (r"(?i)(?:let me |i'?ll |i will |i'm going to )?(?:list|scan|explore|browse|check) (?:the )?(?:directory|folder|files in|contents of) ['\"]?([^\s'\"]+)['\"]?", "list_directory", 1),
        (r"(?i)(?:listing|scanning|exploring|browsing|checking) (?:the )?(?:directory|folder|files in|contents of) ['\"]?([^\s'\"]+)['\"]?", "list_directory", 1),
        
        # Directory creation patterns
        (r"(?i)(?:let me |i'?ll |i will |i'm going to )?(?:create|make) (?:a )?(?:new )?(?:directory|folder) (?:called |named )?['\"]?([^\s'\"]+)['\"]?", "create_directory", 1),
        (r"(?i)(?:creating|making) (?:a )?(?:new )?(?:directory|folder) (?:called |named )?['\"]?([^\s'\"]+)['\"]?", "create_directory", 1),
        
        # Command execution patterns
        (r"(?i)(?:let me |i'?ll |i will |i'm going to )?(?:run|execute) (?:the )?(?:command )?['\"`]([^'\"`]+)['\"`]", "run_command", 1),
        (r"(?i)(?:running|executing) (?:the )?(?:command )?['\"`]([^'\"`]+)['\"`]", "run_command", 1),
    ]
    
    # Patterns that indicate the action was actually performed (tool was called)
    TOOL_CALL_PATTERNS: List[str] = [
        r"<read_file\(",
        r"<write_file\(",
        r"<list_directory\(",
        r"<create_directory\(",
        r"<run_command\(",
        r"read_file\s*\(",
        r"write_file\s*\(",
        r"list_directory\s*\(",
        r"create_directory\s*\(",
        r"run_command\s*\(",
    ]
    
    def __init__(self) -> None:
        """Initialize the detector with compiled patterns."""
        self._action_patterns = [
            (re.compile(pattern), tool, group)
            for pattern, tool, group in self.ACTION_PATTERNS
        ]
        self._tool_patterns = [
            re.compile(pattern) for pattern in self.TOOL_CALL_PATTERNS
        ]
    
    def detect(
        self,
        response: str,
        tool_calls_made: Optional[List[str]] = None
    ) -> List[SkippedToolDetection]:
        """
        Detect skipped tool invocations in an LLM response.
        
        Analyzes the response text to find patterns where the LLM
        describes performing an action without actually calling the tool.
        
        Args:
            response: The LLM response text to analyze
            tool_calls_made: Optional list of tool names that were actually called
            
        Returns:
            List of SkippedToolDetection results for each detected skip
            
        Requirements: 4.4 - Detect when LLM describes action without invoking tool
        """
        if not response:
            return []
        
        tool_calls_made = tool_calls_made or []
        detections: List[SkippedToolDetection] = []
        
        # Check if any tool calls were made in the response
        has_tool_calls = self._has_tool_calls(response)
        
        # Look for action patterns
        for pattern, suggested_tool, desc_group in self._action_patterns:
            matches = pattern.finditer(response)
            for match in matches:
                # Skip if the tool was actually called
                if suggested_tool in tool_calls_made:
                    continue
                
                # Skip if there are tool calls in the response
                if has_tool_calls:
                    continue
                
                # Extract the action description
                try:
                    action_desc = match.group(desc_group)
                except IndexError:
                    action_desc = match.group(0)
                
                # Calculate confidence based on pattern strength
                confidence = self._calculate_confidence(match.group(0))
                
                # Only report if confidence is high enough
                if confidence >= 0.5:
                    detections.append(SkippedToolDetection(
                        detected=True,
                        action_description=action_desc,
                        suggested_tool=suggested_tool,
                        confidence=confidence
                    ))
        
        # Deduplicate detections (same tool suggestion)
        seen_tools: set = set()
        unique_detections: List[SkippedToolDetection] = []
        for detection in detections:
            if detection.suggested_tool not in seen_tools:
                seen_tools.add(detection.suggested_tool)
                unique_detections.append(detection)
        
        return unique_detections
    
    def _has_tool_calls(self, response: str) -> bool:
        """
        Check if the response contains actual tool calls.
        
        Args:
            response: The response text to check
            
        Returns:
            True if tool calls are present, False otherwise
        """
        for pattern in self._tool_patterns:
            if pattern.search(response):
                return True
        return False
    
    def _calculate_confidence(self, matched_text: str) -> float:
        """
        Calculate confidence level for a detection.
        
        Higher confidence for more explicit action descriptions.
        
        Args:
            matched_text: The text that matched the pattern
            
        Returns:
            Confidence level between 0.0 and 1.0
        """
        confidence = 0.5
        
        # Higher confidence for explicit future tense
        if re.search(r"(?i)i'?ll |i will |i'm going to ", matched_text):
            confidence += 0.2
        
        # Higher confidence for "let me" patterns
        if re.search(r"(?i)let me ", matched_text):
            confidence += 0.2
        
        # Higher confidence for present progressive
        if re.search(r"(?i)ing ", matched_text):
            confidence += 0.1
        
        return min(confidence, 1.0)


# Module-level singleton
_detector: Optional[SkippedToolDetector] = None


def get_skipped_tool_detector() -> SkippedToolDetector:
    """Get the global SkippedToolDetector instance."""
    global _detector
    if _detector is None:
        _detector = SkippedToolDetector()
    return _detector


def detect_skipped_tools(
    response: str,
    tool_calls_made: Optional[List[str]] = None
) -> List[SkippedToolDetection]:
    """
    Convenience function to detect skipped tool invocations.
    
    Args:
        response: The LLM response text to analyze
        tool_calls_made: Optional list of tool names that were actually called
        
    Returns:
        List of SkippedToolDetection results
        
    Requirements: 4.4 - Detect when LLM describes action without invoking tool
    """
    return get_skipped_tool_detector().detect(response, tool_calls_made)
