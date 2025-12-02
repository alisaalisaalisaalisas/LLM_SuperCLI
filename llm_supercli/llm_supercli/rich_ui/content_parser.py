"""Content parser for extracting reasoning and filtering tool syntax.

This module provides utilities for parsing streamed content from LLM responses,
specifically handling:
- Extraction of reasoning content from <think> tags
- Filtering of tool call syntax from display text

Requirements addressed:
- 1.1: Append new content without clearing previous content (via think tag parsing)
- 2.4: Filter tool call syntax from displayed response text
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedContent:
    """Result of parsing content for think tags.
    
    Attributes:
        reasoning: Content extracted from <think> tags
        response: Content outside of <think> tags
        in_thinking: Whether the content ends inside an unclosed <think> tag
    """
    reasoning: str
    response: str
    in_thinking: bool = False


# Common tool names used in the CLI
DEFAULT_TOOL_NAMES = [
    'read_file',
    'write_file', 
    'list_directory',
    'create_directory',
    'run_command',
    'get_current_directory',
]


def parse_think_tags(content: str, in_thinking: bool = False) -> ParsedContent:
    """Extract reasoning content from <think> tags.
    
    Parses content to separate reasoning (inside <think> tags) from
    response content (outside <think> tags). Handles partial/streaming
    content where tags may be incomplete.
    
    Args:
        content: The content string to parse
        in_thinking: Whether we're currently inside an unclosed <think> tag
                    from previous content (for streaming scenarios)
    
    Returns:
        ParsedContent with separated reasoning and response, plus state
        indicating if we ended inside a think tag
    
    Examples:
        >>> result = parse_think_tags("<think>reasoning</think>response")
        >>> result.reasoning
        'reasoning'
        >>> result.response
        'response'
        
        >>> result = parse_think_tags("partial <think>thinking...")
        >>> result.in_thinking
        True
    """
    if not content:
        return ParsedContent(reasoning="", response="", in_thinking=in_thinking)
    
    reasoning_parts = []
    response_parts = []
    currently_in_thinking = in_thinking
    
    # Process character by character to handle streaming/partial tags
    i = 0
    buffer = ""
    
    while i < len(content):
        char = content[i]
        
        # Check for potential tag start
        if char == '<':
            # Look ahead for <think> or </think>
            remaining = content[i:]
            
            if remaining.startswith('<think>'):
                # Flush buffer to appropriate destination
                if buffer:
                    if currently_in_thinking:
                        reasoning_parts.append(buffer)
                    else:
                        response_parts.append(buffer)
                    buffer = ""
                
                currently_in_thinking = True
                i += len('<think>')
                continue
            
            elif remaining.startswith('</think>'):
                # Flush buffer to reasoning
                if buffer:
                    if currently_in_thinking:
                        reasoning_parts.append(buffer)
                    else:
                        response_parts.append(buffer)
                    buffer = ""
                
                currently_in_thinking = False
                i += len('</think>')
                continue
            
            # Check for partial tag at end of content
            elif i == len(content) - 1 or _is_partial_think_tag(remaining):
                # Could be start of a tag, keep in buffer for next chunk
                buffer += char
                i += 1
                continue
        
        # Regular character
        buffer += char
        i += 1
    
    # Flush remaining buffer
    if buffer:
        if currently_in_thinking:
            reasoning_parts.append(buffer)
        else:
            response_parts.append(buffer)
    
    return ParsedContent(
        reasoning="".join(reasoning_parts),
        response="".join(response_parts),
        in_thinking=currently_in_thinking
    )


def _is_partial_think_tag(text: str) -> bool:
    """Check if text could be the start of a <think> or </think> tag.
    
    Used to detect partial tags at the end of streaming content.
    """
    think_open = '<think>'
    think_close = '</think>'
    
    # Check if text is a prefix of either tag
    for tag in [think_open, think_close]:
        for length in range(1, len(tag)):
            if text.startswith(tag[:length]) and len(text) <= length:
                return True
    
    return False


def filter_tool_syntax(
    content: str,
    tool_names: Optional[list[str]] = None
) -> str:
    """Remove tool call patterns from display text.
    
    Filters out both Python-style (tool_name(args)) and XML-style 
    (<tool_name(args)>) tool call patterns from content to produce
    clean display text.
    
    Args:
        content: The content string to filter
        tool_names: List of tool names to filter. If None, uses DEFAULT_TOOL_NAMES
    
    Returns:
        Content with tool call syntax removed
    
    Examples:
        >>> filter_tool_syntax("Hello read_file('test.py') world")
        'Hello  world'
        
        >>> filter_tool_syntax("Check <read_file('test.py')> this")
        'Check  this'
    """
    if not content:
        return ""
    
    if tool_names is None:
        tool_names = DEFAULT_TOOL_NAMES
    
    if not tool_names:
        return content
    
    result = content
    
    # Build pattern for tool names
    tool_pattern = '|'.join(re.escape(name) for name in tool_names)
    
    # Pattern 1: XML-style tool calls with closing tags
    # e.g., <read_file(...)>content</read_file>
    xml_with_close_pattern = rf'<({tool_pattern})\([^)]*\)>[^<]*</\1>'
    result = re.sub(xml_with_close_pattern, '', result)
    
    # Pattern 2: XML-style tool calls without closing tags
    # e.g., <read_file(...)>
    xml_open_pattern = rf'<({tool_pattern})\([^)]*\)>'
    result = re.sub(xml_open_pattern, '', result)
    
    # Pattern 3: Python-style tool calls with balanced parentheses
    # e.g., read_file('path/to/file')
    # This handles nested parentheses by using a non-greedy match
    python_pattern = rf'({tool_pattern})\s*\([^)]*\)'
    result = re.sub(python_pattern, '', result, flags=re.DOTALL)
    
    # Pattern 4: Handle multiline Python-style calls
    # For cases where arguments span multiple lines
    python_multiline_pattern = rf'({tool_pattern})\s*\(.*?\)'
    result = re.sub(python_multiline_pattern, '', result, flags=re.DOTALL)
    
    # Pattern 5: Malformed XML closing tags (Qwen sometimes outputs these)
    # e.g., < </list_directory> or </ list_directory>
    malformed_close_pattern = rf'<\s*/\s*({tool_pattern})\s*>'
    result = re.sub(malformed_close_pattern, '', result)
    
    # Pattern 6: Standalone closing tags
    # e.g., </read_file> or </list_directory>
    standalone_close_pattern = rf'</({tool_pattern})>'
    result = re.sub(standalone_close_pattern, '', result)
    
    # Pattern 7: Opening tags without parentheses
    # e.g., <read_file> or <list_directory>
    standalone_open_pattern = rf'<({tool_pattern})>'
    result = re.sub(standalone_open_pattern, '', result)
    
    # Clean up artifacts
    # Remove empty code blocks that might remain
    result = re.sub(r'```\s*```', '', result)
    result = re.sub(r'```\s*\n?\s*```', '', result)
    
    # Remove lines that are just "< " or similar artifacts
    result = re.sub(r'^\s*<\s*$', '', result, flags=re.MULTILINE)
    
    # Normalize multiple newlines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Clean up multiple spaces (but preserve single spaces)
    result = re.sub(r'  +', ' ', result)
    
    return result.strip()


def extract_tool_calls_from_content(
    content: str,
    tool_names: Optional[list[str]] = None
) -> list[str]:
    """Extract tool call strings from content.
    
    Finds all tool call patterns in content and returns them as a list.
    Useful for identifying what tool calls are present before filtering.
    
    Args:
        content: The content string to search
        tool_names: List of tool names to look for. If None, uses DEFAULT_TOOL_NAMES
    
    Returns:
        List of tool call strings found in content
    
    Examples:
        >>> extract_tool_calls_from_content("read_file('a.py') and write_file('b.py')")
        ["read_file('a.py')", "write_file('b.py')"]
    """
    if not content:
        return []
    
    if tool_names is None:
        tool_names = DEFAULT_TOOL_NAMES
    
    if not tool_names:
        return []
    
    tool_pattern = '|'.join(re.escape(name) for name in tool_names)
    
    # Find Python-style calls
    python_pattern = rf'({tool_pattern})\s*\([^)]*\)'
    matches = re.findall(python_pattern, content, flags=re.DOTALL)
    
    # Get full matches (findall returns groups, we need full match)
    full_matches = re.finditer(python_pattern, content, flags=re.DOTALL)
    results = [m.group(0) for m in full_matches]
    
    return results
