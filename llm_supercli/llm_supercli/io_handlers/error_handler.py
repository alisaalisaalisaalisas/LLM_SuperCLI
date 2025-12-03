"""
Error handling module for llm_supercli.

This module provides centralized error handling for tool execution,
including:
- Empty directory handling (Requirement 1.4)
- Write file failure handling with remediation (Requirement 2.5)
- Corrupted output recovery (Requirement 6.5)

Requirements:
- 1.4: Report empty directory rather than assuming files exist
- 2.5: Report write_file errors and suggest remediation steps
- 6.5: Detect and recover from corrupted/garbled output
"""
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class ErrorType(Enum):
    """Types of errors that can occur during tool execution."""
    EMPTY_DIRECTORY = "empty_directory"
    WRITE_FAILURE = "write_failure"
    PERMISSION_DENIED = "permission_denied"
    DISK_FULL = "disk_full"
    PATH_NOT_FOUND = "path_not_found"
    ENCODING_ERROR = "encoding_error"
    CORRUPTED_OUTPUT = "corrupted_output"
    UNKNOWN = "unknown"


@dataclass
class ErrorResult:
    """
    Result of error analysis with remediation suggestions.
    
    Attributes:
        error_type: The type of error detected
        message: Human-readable error message
        remediation_steps: List of suggested remediation steps
        raw_error: The original error message/exception
        recoverable: Whether the error can be recovered from
    """
    error_type: ErrorType
    message: str
    remediation_steps: List[str]
    raw_error: str = ""
    recoverable: bool = True


class EmptyDirectoryHandler:
    """
    Handles empty directory cases with informative messages.
    
    Requirements: 1.4 - Report empty directory rather than assuming files exist
    """
    
    @staticmethod
    def format_empty_directory_message(path: str) -> str:
        """
        Format an informative message for an empty directory.
        
        Args:
            path: The path to the empty directory
            
        Returns:
            Formatted message explaining the directory is empty
        """
        abs_path = os.path.abspath(path)
        
        message_parts = [
            f"Directory '{path}' is empty.",
            "",
            "This directory contains no files or subdirectories.",
        ]
        
        # Add context about what this means
        if path == "." or path == "./":
            message_parts.extend([
                "",
                "The current working directory has no files.",
                "You may want to:",
                "  • Create new files using write_file",
                "  • Navigate to a different directory",
                "  • Check if you're in the correct location",
            ])
        else:
            message_parts.extend([
                "",
                "You may want to:",
                "  • Create files in this directory using write_file",
                "  • Check if the path is correct",
            ])
        
        return "\n".join(message_parts)
    
    @staticmethod
    def is_empty_directory_result(result: str) -> bool:
        """
        Check if a result indicates an empty directory.
        
        Args:
            result: The result string from list_directory
            
        Returns:
            True if the result indicates an empty directory
        """
        return "is empty" in result.lower() or "no files" in result.lower()


class WriteFailureHandler:
    """
    Handles write_file failures with remediation suggestions.
    
    Requirements: 2.5 - Report write_file errors and suggest remediation steps
    """
    
    # Common error patterns and their remediation
    ERROR_PATTERNS = [
        (
            r"permission denied",
            ErrorType.PERMISSION_DENIED,
            [
                "Check file/directory permissions",
                "Try running with elevated privileges (sudo on Unix, Admin on Windows)",
                "Ensure the target directory is not read-only",
                "Check if the file is locked by another process",
            ]
        ),
        (
            r"no space left|disk full|not enough space",
            ErrorType.DISK_FULL,
            [
                "Free up disk space by removing unnecessary files",
                "Check available disk space with 'df -h' (Unix) or 'dir' (Windows)",
                "Consider writing to a different drive/partition",
                "Empty the recycle bin/trash",
            ]
        ),
        (
            r"no such file or directory|path not found|cannot find",
            ErrorType.PATH_NOT_FOUND,
            [
                "Verify the directory path exists",
                "Create parent directories first using create_directory",
                "Check for typos in the file path",
                "Use absolute paths to avoid confusion",
            ]
        ),
        (
            r"encoding|codec|decode|encode|unicode",
            ErrorType.ENCODING_ERROR,
            [
                "Ensure content uses valid UTF-8 encoding",
                "Remove or replace invalid characters",
                "Check for binary content being written as text",
                "Try specifying a different encoding",
            ]
        ),
    ]
    
    @classmethod
    def analyze_write_error(cls, error_message: str, file_path: str = "") -> ErrorResult:
        """
        Analyze a write error and provide remediation suggestions.
        
        Args:
            error_message: The error message from the write operation
            file_path: The file path that failed to write
            
        Returns:
            ErrorResult with analysis and remediation steps
        """
        error_lower = error_message.lower()
        
        # Check against known patterns
        for pattern, error_type, remediation in cls.ERROR_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return ErrorResult(
                    error_type=error_type,
                    message=cls._format_error_message(error_type, file_path, error_message),
                    remediation_steps=remediation,
                    raw_error=error_message,
                    recoverable=error_type != ErrorType.DISK_FULL
                )
        
        # Unknown error - provide generic remediation
        return ErrorResult(
            error_type=ErrorType.UNKNOWN,
            message=f"Failed to write file '{file_path}': {error_message}",
            remediation_steps=[
                "Check that the file path is valid",
                "Verify you have write permissions",
                "Ensure the parent directory exists",
                "Check available disk space",
            ],
            raw_error=error_message,
            recoverable=True
        )
    
    @staticmethod
    def _format_error_message(error_type: ErrorType, file_path: str, raw_error: str) -> str:
        """Format a user-friendly error message."""
        type_messages = {
            ErrorType.PERMISSION_DENIED: f"Permission denied when writing to '{file_path}'",
            ErrorType.DISK_FULL: f"Insufficient disk space to write '{file_path}'",
            ErrorType.PATH_NOT_FOUND: f"Path not found for '{file_path}'",
            ErrorType.ENCODING_ERROR: f"Encoding error when writing '{file_path}'",
        }
        return type_messages.get(error_type, f"Error writing '{file_path}': {raw_error}")
    
    @staticmethod
    def format_error_with_remediation(error_result: ErrorResult) -> str:
        """
        Format an error result with remediation steps for display.
        
        Args:
            error_result: The analyzed error result
            
        Returns:
            Formatted string with error and remediation steps
        """
        lines = [
            f"Error: {error_result.message}",
            "",
            "Suggested remediation steps:",
        ]
        
        for i, step in enumerate(error_result.remediation_steps, 1):
            lines.append(f"  {i}. {step}")
        
        return "\n".join(lines)


class CorruptedOutputHandler:
    """
    Handles corrupted/garbled output recovery.
    
    Requirements: 6.5 - Detect and recover from corrupted/garbled output
    """
    
    # Patterns that indicate corrupted output
    CORRUPTION_PATTERNS = [
        # Unbalanced XML-like tags
        (r'<[^>]*$', "Unclosed XML tag"),
        (r'^[^<]*>', "Orphaned closing tag"),
        # Unbalanced code blocks
        (r'```[^`]*$', "Unclosed code block"),
        # Encoding artifacts
        (r'[\x00-\x08\x0b\x0c\x0e-\x1f]', "Control characters detected"),
        # Repeated garbage patterns
        (r'(.{10,})\1{3,}', "Repeated content pattern"),
        # Broken escape sequences
        (r'\\x[0-9a-fA-F]{0,1}(?![0-9a-fA-F])', "Malformed escape sequence"),
    ]
    
    @classmethod
    def detect_corruption(cls, content: str) -> Tuple[bool, List[str]]:
        """
        Detect if content appears to be corrupted.
        
        Args:
            content: The content to check
            
        Returns:
            Tuple of (is_corrupted, list_of_issues)
        """
        if not content:
            return False, []
        
        issues = []
        
        for pattern, description in cls.CORRUPTION_PATTERNS:
            if re.search(pattern, content):
                issues.append(description)
        
        # Check for unbalanced brackets/braces
        bracket_issues = cls._check_balanced_brackets(content)
        issues.extend(bracket_issues)
        
        return len(issues) > 0, issues
    
    @staticmethod
    def _check_balanced_brackets(content: str) -> List[str]:
        """Check for unbalanced brackets and braces."""
        issues = []
        
        # Check code blocks
        code_block_count = content.count('```')
        if code_block_count % 2 != 0:
            issues.append("Unbalanced code block markers (```)")
        
        # Check think tags
        think_open = content.count('<think>')
        think_close = content.count('</think>')
        if think_open != think_close:
            issues.append(f"Unbalanced <think> tags (open: {think_open}, close: {think_close})")
        
        return issues
    
    @classmethod
    def attempt_recovery(cls, content: str) -> Tuple[str, bool, str]:
        """
        Attempt to recover from corrupted content.
        
        Args:
            content: The potentially corrupted content
            
        Returns:
            Tuple of (recovered_content, was_modified, warning_message)
        """
        if not content:
            return content, False, ""
        
        original = content
        recovered = content
        modifications = []
        
        # Remove control characters
        recovered = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', recovered)
        if recovered != original:
            modifications.append("Removed control characters")
        
        # Close unclosed code blocks
        code_block_count = recovered.count('```')
        if code_block_count % 2 != 0:
            recovered += '\n```'
            modifications.append("Closed unclosed code block")
        
        # Close unclosed think tags
        think_open = recovered.count('<think>')
        think_close = recovered.count('</think>')
        if think_open > think_close:
            recovered += '</think>' * (think_open - think_close)
            modifications.append("Closed unclosed <think> tags")
        
        # Remove orphaned closing tags at the start
        recovered = re.sub(r'^(\s*</[^>]+>\s*)+', '', recovered)
        
        # Remove unclosed tags at the end (but preserve content)
        recovered = re.sub(r'<[^/>][^>]*$', '', recovered)
        
        was_modified = recovered != original
        warning = ""
        
        if was_modified:
            warning = "Content was automatically recovered. Modifications: " + "; ".join(modifications)
        
        return recovered, was_modified, warning
    
    @classmethod
    def format_with_warning(cls, content: str, warning: str) -> str:
        """
        Format content with a corruption warning.
        
        Args:
            content: The content to display
            warning: The warning message
            
        Returns:
            Formatted content with warning
        """
        if not warning:
            return content
        
        return f"⚠️ {warning}\n\n{content}"


class ToolErrorHandler:
    """
    Centralized error handler for all tool operations.
    
    Combines empty directory, write failure, and corruption handling.
    """
    
    def __init__(self):
        self._empty_handler = EmptyDirectoryHandler()
        self._write_handler = WriteFailureHandler()
        self._corruption_handler = CorruptedOutputHandler()
    
    def handle_list_directory_result(self, result: str, path: str) -> str:
        """
        Process list_directory result, enhancing empty directory messages.
        
        Args:
            result: The raw result from list_directory
            path: The directory path that was listed
            
        Returns:
            Enhanced result message
        """
        if self._empty_handler.is_empty_directory_result(result):
            return self._empty_handler.format_empty_directory_message(path)
        return result
    
    def handle_write_file_error(self, error_message: str, file_path: str) -> str:
        """
        Process write_file error with remediation suggestions.
        
        Args:
            error_message: The error message from write_file
            file_path: The file path that failed
            
        Returns:
            Formatted error with remediation steps
        """
        error_result = self._write_handler.analyze_write_error(error_message, file_path)
        return self._write_handler.format_error_with_remediation(error_result)
    
    def handle_output_corruption(self, content: str) -> Tuple[str, str]:
        """
        Check for and recover from corrupted output.
        
        Args:
            content: The content to check and potentially recover
            
        Returns:
            Tuple of (processed_content, warning_message)
        """
        is_corrupted, issues = self._corruption_handler.detect_corruption(content)
        
        if not is_corrupted:
            return content, ""
        
        recovered, was_modified, warning = self._corruption_handler.attempt_recovery(content)
        
        if was_modified:
            return recovered, warning
        
        # Could not recover - return with warning about issues
        issue_list = ", ".join(issues)
        return content, f"Output may be corrupted: {issue_list}"


# Module-level singleton
_error_handler: Optional[ToolErrorHandler] = None


def get_error_handler() -> ToolErrorHandler:
    """Get the global ToolErrorHandler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ToolErrorHandler()
    return _error_handler


def handle_empty_directory(path: str) -> str:
    """
    Convenience function to format empty directory message.
    
    Args:
        path: The empty directory path
        
    Returns:
        Formatted message
    """
    return EmptyDirectoryHandler.format_empty_directory_message(path)


def handle_write_error(error_message: str, file_path: str) -> str:
    """
    Convenience function to handle write errors.
    
    Args:
        error_message: The error message
        file_path: The file path that failed
        
    Returns:
        Formatted error with remediation
    """
    return get_error_handler().handle_write_file_error(error_message, file_path)


def recover_corrupted_output(content: str) -> Tuple[str, str]:
    """
    Convenience function to recover corrupted output.
    
    Args:
        content: The potentially corrupted content
        
    Returns:
        Tuple of (recovered_content, warning_message)
    """
    return get_error_handler().handle_output_corruption(content)
