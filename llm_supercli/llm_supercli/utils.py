"""
Utility functions for llm_supercli.
"""
import hashlib
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar
from functools import wraps

T = TypeVar('T')


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: The string to truncate
        max_length: Maximum length of the output string
        suffix: Suffix to append when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def count_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    Uses a simple approximation (4 chars per token).
    
    Args:
        text: The text to count tokens for
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def format_timestamp(timestamp: Optional[float] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp to a human-readable string.
    
    Args:
        timestamp: Unix timestamp (uses current time if None)
        fmt: strftime format string
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = time.time()
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes, seconds = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s"


def format_bytes(num_bytes: int) -> str:
    """
    Format byte count to human-readable string.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def format_cost(cost: float) -> str:
    """
    Format a cost value to a currency string.
    
    Args:
        cost: Cost value
        
    Returns:
        Formatted cost string (e.g., "$0.0012")
    """
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


def generate_session_id() -> str:
    """
    Generate a unique session ID.
    
    Returns:
        Unique session ID string
    """
    timestamp = str(time.time()).encode()
    return hashlib.sha256(timestamp).hexdigest()[:16]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = sanitized.strip('. ')
    return sanitized[:255] if sanitized else 'unnamed'


def is_valid_path(path: str) -> bool:
    """
    Check if a path string represents a valid file path.
    
    Args:
        path: Path string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        p = Path(path)
        return p.exists() or p.parent.exists()
    except (OSError, ValueError):
        return False


def expand_path(path: str) -> Path:
    """
    Expand a path string, resolving ~ and environment variables.
    
    Args:
        path: Path string to expand
        
    Returns:
        Expanded Path object
    """
    return Path(path).expanduser().resolve()


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """
    Extract code blocks from markdown text.
    
    Args:
        text: Markdown text containing code blocks
        
    Returns:
        List of (language, code) tuples
    """
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang or 'text', code.strip()) for lang, code in matches]


def wrap_text(text: str, width: int = 80) -> str:
    """
    Wrap text to a specified width.
    
    Args:
        text: Text to wrap
        width: Maximum line width
        
    Returns:
        Wrapped text
    """
    lines = []
    for paragraph in text.split('\n'):
        if len(paragraph) <= width:
            lines.append(paragraph)
        else:
            words = paragraph.split()
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= width:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception  # type: ignore
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            import asyncio
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception  # type: ignore
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == 'win32'


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == 'darwin'


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith('linux')


def get_terminal_size() -> tuple[int, int]:
    """
    Get terminal size (columns, rows).
    
    Returns:
        Tuple of (columns, rows)
    """
    try:
        import shutil
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except Exception:
        return 80, 24


def highlight_matches(text: str, pattern: str, highlight_start: str = "[bold red]", 
                      highlight_end: str = "[/bold red]") -> str:
    """
    Highlight pattern matches in text with Rich markup.
    
    Args:
        text: Text to search in
        pattern: Pattern to highlight
        highlight_start: Rich markup for highlight start
        highlight_end: Rich markup for highlight end
        
    Returns:
        Text with highlighted matches
    """
    if not pattern:
        return text
    
    try:
        compiled = re.compile(f"({re.escape(pattern)})", re.IGNORECASE)
        return compiled.sub(f"{highlight_start}\\1{highlight_end}", text)
    except re.error:
        return text


class Timer:
    """Simple context manager for timing operations."""
    
    def __init__(self) -> None:
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed: float = 0
    
    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
    
    def __str__(self) -> str:
        return format_duration(self.elapsed)
