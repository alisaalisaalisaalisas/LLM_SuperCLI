"""
Command parser for llm_supercli.
Parses user input into commands, shell commands, and messages.
"""
import re
import shlex
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..constants import SLASH_PREFIX, SHELL_PREFIX, FILE_PREFIX


@dataclass
class ParsedInput:
    """Result of parsing user input."""
    type: str  # 'command', 'shell', 'message', 'empty'
    command: str = ""
    args: str = ""
    raw: str = ""
    files: List[str] = field(default_factory=list)
    shell_command: str = ""
    message: str = ""


class CommandParser:
    """
    Parser for user input in the CLI.
    
    Handles parsing of:
    - Slash commands (/command args)
    - Shell commands (!command args)
    - File references (@file)
    - Regular chat messages
    """
    
    def __init__(self) -> None:
        """Initialize the parser."""
        # Match @file or file:path
        self._file_pattern = re.compile(r'(?:@|file:)(\S+)')
    
    def parse(self, input_text: str) -> ParsedInput:
        """
        Parse user input into a structured result.
        
        Args:
            input_text: Raw user input
            
        Returns:
            ParsedInput with parsed components
        """
        text = input_text.strip()
        
        if not text:
            return ParsedInput(type="empty", raw=input_text)
        
        if text.startswith(SLASH_PREFIX):
            return self._parse_command(text)
        
        if text.startswith(SHELL_PREFIX):
            return self._parse_shell(text)
        
        return self._parse_message(text)
    
    def _parse_command(self, text: str) -> ParsedInput:
        """Parse a slash command."""
        without_prefix = text[len(SLASH_PREFIX):]
        
        parts = without_prefix.split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        
        return ParsedInput(
            type="command",
            command=command,
            args=args,
            raw=text
        )
    
    def _parse_shell(self, text: str) -> ParsedInput:
        """Parse a shell command."""
        shell_command = text[len(SHELL_PREFIX):].strip()
        
        return ParsedInput(
            type="shell",
            shell_command=shell_command,
            raw=text
        )
    
    def _parse_message(self, text: str) -> ParsedInput:
        """Parse a chat message, extracting file references."""
        files = self._extract_files(text)
        
        message = text
        for file_ref in files:
            # Remove both @file and file:path patterns
            message = message.replace(f"@{file_ref}", "")
            message = message.replace(f"file:{file_ref}", "")
        message = message.strip()
        message = " ".join(message.split())
        
        return ParsedInput(
            type="message",
            message=message if message else text,
            files=files,
            raw=text
        )
    
    def _extract_files(self, text: str) -> List[str]:
        """Extract file references from text."""
        matches = self._file_pattern.findall(text)
        return matches
    
    def parse_args(self, args: str) -> Tuple[List[str], dict]:
        """
        Parse command arguments into positional and keyword args.
        
        Args:
            args: Arguments string
            
        Returns:
            Tuple of (positional_args, keyword_args)
        """
        if not args:
            return [], {}
        
        try:
            tokens = shlex.split(args)
        except ValueError:
            tokens = args.split()
        
        positional = []
        keyword = {}
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token.startswith("--"):
                key = token[2:]
                if "=" in key:
                    k, v = key.split("=", 1)
                    keyword[k] = v
                elif i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    keyword[key] = tokens[i + 1]
                    i += 1
                else:
                    keyword[key] = True
            elif token.startswith("-") and len(token) == 2:
                key = token[1]
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    keyword[key] = tokens[i + 1]
                    i += 1
                else:
                    keyword[key] = True
            else:
                positional.append(token)
            
            i += 1
        
        return positional, keyword
    
    def split_command_chain(self, text: str) -> List[str]:
        """
        Split a command chain (commands separated by &&).
        
        Args:
            text: Input text potentially containing multiple commands
            
        Returns:
            List of individual commands
        """
        commands = []
        current = []
        depth = 0
        
        for char in text:
            if char == '(' or char == '[' or char == '{':
                depth += 1
                current.append(char)
            elif char == ')' or char == ']' or char == '}':
                depth -= 1
                current.append(char)
            elif char == '&' and depth == 0:
                if current and current[-1] == '&':
                    current.pop()
                    if current:
                        commands.append(''.join(current).strip())
                    current = []
                else:
                    current.append(char)
            else:
                current.append(char)
        
        if current:
            commands.append(''.join(current).strip())
        
        return [cmd for cmd in commands if cmd]
    
    def is_multiline_start(self, text: str) -> bool:
        """Check if input starts a multiline block."""
        return text.rstrip().endswith(('\\', '{', '[', '(', '"""', "'''"))
    
    def validate_brackets(self, text: str) -> Optional[str]:
        """
        Validate bracket matching.
        
        Args:
            text: Text to validate
            
        Returns:
            Error message if unbalanced, None if valid
        """
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        
        for char in text:
            if char in '([{':
                stack.append(char)
            elif char in ')]}':
                if not stack or stack[-1] != pairs[char]:
                    return f"Unmatched '{char}'"
                stack.pop()
        
        if stack:
            return f"Unclosed '{stack[-1]}'"
        
        return None
