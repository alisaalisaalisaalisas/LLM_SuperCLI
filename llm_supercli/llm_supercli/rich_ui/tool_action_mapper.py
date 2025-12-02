"""
Tool to action card mapper for CLI integration.

This module provides the mapping between tool calls and action card rendering,
enabling automatic generation of action cards for tool executions.

Requirements: 8.1, 8.2 - Automatically generate appropriate action cards for tool execution
"""
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .action_renderer import ActionRenderer
from .action_models import ActionType


class ToolActionMapper:
    """
    Maps tool calls to action card rendering methods.
    
    This class intercepts tool calls and generates appropriate action cards
    based on the tool name and arguments. It handles:
    - File read operations -> Read files card
    - Search operations -> Search card  
    - File write operations -> Create/Update file card (based on existence)
    - Directory operations -> Appropriate cards
    
    Requirements: 8.1 - Automatically generate appropriate action cards
    Requirements: 8.2 - Intercept tool calls and render them as cards
    """
    
    # Tool name to action type mapping
    TOOL_ACTION_MAP = {
        "read_file": ActionType.READ_FILES,
        "read_multiple_files": ActionType.READ_FILES,
        "search": ActionType.SEARCH,
        "grep_search": ActionType.SEARCH,
        "write_file": None,  # Determined dynamically (CREATE or UPDATE)
        "list_directory": ActionType.READ_FILES,  # Treat as file read
        "create_directory": ActionType.CREATE_FILE,
        "run_command": None,  # No specific card
        "get_current_directory": None,  # No specific card
    }
    
    def __init__(
        self,
        action_renderer: ActionRenderer,
        working_dir: Optional[str] = None
    ) -> None:
        """
        Initialize the ToolActionMapper.
        
        Args:
            action_renderer: ActionRenderer instance for rendering cards
            working_dir: Working directory for resolving file paths
        """
        self._renderer = action_renderer
        self._working_dir = working_dir or os.getcwd()
        self._start_time: Optional[float] = None
        self._total_tokens: Tuple[int, int] = (0, 0)
        self._total_cost: float = 0.0
    
    @property
    def working_dir(self) -> str:
        """Get the current working directory."""
        return self._working_dir
    
    @working_dir.setter
    def working_dir(self, value: str) -> None:
        """Set the working directory."""
        self._working_dir = value
    
    def start_session(self) -> None:
        """
        Start tracking a new response session.
        
        Call this at the beginning of processing a user message to
        track elapsed time for the status footer.
        """
        self._start_time = time.time()
        self._total_tokens = (0, 0)
        self._total_cost = 0.0
    
    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """
        Add token counts to the session total.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
        """
        current_in, current_out = self._total_tokens
        self._total_tokens = (current_in + input_tokens, current_out + output_tokens)
    
    def add_cost(self, cost: float) -> None:
        """
        Add cost to the session total.
        
        Args:
            cost: Cost in dollars
        """
        self._total_cost += cost
    
    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to working directory.
        
        Args:
            path: File or directory path
            
        Returns:
            Resolved absolute Path
        """
        p = Path(path)
        if not p.is_absolute():
            p = Path(self._working_dir) / p
        return p.resolve()
    
    def _file_exists(self, path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            path: File path to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            return self._resolve_path(path).exists()
        except Exception:
            return False
    
    def render_tool_action(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True
    ) -> None:
        """
        Render an action card for a tool call.
        
        This method maps the tool call to the appropriate action card
        rendering method based on the tool name and arguments.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments dictionary
            result: Optional result string from tool execution
            success: Whether the tool call succeeded
            
        Requirements: 8.1 - Automatically generate appropriate action cards
        """
        # Skip tools that don't have action cards
        if tool_name not in self.TOOL_ACTION_MAP:
            return
        
        action_type = self.TOOL_ACTION_MAP.get(tool_name)
        
        # Handle file read operations
        if tool_name == "read_file":
            path = arguments.get("path", "")
            failed = [] if success else [path]
            files = [path] if success else []
            self._renderer.render_read_files(files=files, failed=failed)
        
        elif tool_name == "read_multiple_files":
            paths = arguments.get("paths", [])
            if isinstance(paths, str):
                paths = [paths]
            failed = [] if success else paths
            files = paths if success else []
            self._renderer.render_read_files(files=files, failed=failed)
        
        # Handle search operations
        elif tool_name in ("search", "grep_search"):
            query = arguments.get("query", arguments.get("pattern", ""))
            # Try to extract results count from result string
            results_count = self._extract_results_count(result) if result else 0
            self._renderer.render_search(query=query, results_count=results_count)
        
        # Handle file write operations - detect create vs update
        elif tool_name == "write_file":
            path = arguments.get("path", "")
            content = arguments.get("content", "")
            
            # Check if file existed before write (for create vs update)
            # Note: This check happens BEFORE the tool executes, so we need
            # to track this state. For now, we'll check current state.
            file_existed = self._file_exists(path)
            
            if file_existed:
                # File update
                summary = self._generate_change_summary(content)
                self._renderer.render_file_updated(filename=path, summary=summary)
            else:
                # File creation
                preview = self._generate_content_preview(content)
                self._renderer.render_file_created(filename=path, preview=preview)
        
        # Handle directory listing (treat as file read)
        elif tool_name == "list_directory":
            path = arguments.get("path", ".")
            self._renderer.render_read_files(files=[f"📁 {path}"], failed=[])
        
        # Handle directory creation
        elif tool_name == "create_directory":
            path = arguments.get("path", "")
            self._renderer.render_file_created(filename=f"📁 {path}")
    
    def render_tool_action_before(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Capture state before tool execution for accurate create/update detection.
        
        Call this BEFORE executing the tool to capture file existence state.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments dictionary
            
        Returns:
            State dictionary to pass to render_tool_action_after
        """
        state = {"tool_name": tool_name, "arguments": arguments}
        
        # For write_file, capture whether file exists before write
        if tool_name == "write_file":
            path = arguments.get("path", "")
            state["file_existed"] = self._file_exists(path)
        
        return state
    
    def render_tool_action_after(
        self,
        state: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True
    ) -> None:
        """
        Render action card after tool execution with captured state.
        
        Call this AFTER executing the tool with the state from render_tool_action_before.
        
        Args:
            state: State dictionary from render_tool_action_before
            result: Result string from tool execution
            success: Whether the tool call succeeded
            
        Requirements: 8.1 - Automatically generate appropriate action cards
        """
        tool_name = state.get("tool_name", "")
        arguments = state.get("arguments", {})
        
        # Skip tools that don't have action cards
        if tool_name not in self.TOOL_ACTION_MAP:
            return
        
        # Handle file read operations
        if tool_name == "read_file":
            path = arguments.get("path", "")
            failed = [] if success else [path]
            files = [path] if success else []
            self._renderer.render_read_files(files=files, failed=failed)
        
        elif tool_name == "read_multiple_files":
            paths = arguments.get("paths", [])
            if isinstance(paths, str):
                paths = [paths]
            failed = [] if success else paths
            files = paths if success else []
            self._renderer.render_read_files(files=files, failed=failed)
        
        # Handle search operations
        elif tool_name in ("search", "grep_search"):
            query = arguments.get("query", arguments.get("pattern", ""))
            results_count = self._extract_results_count(result) if result else 0
            self._renderer.render_search(query=query, results_count=results_count)
        
        # Handle file write operations - use captured state for create vs update
        elif tool_name == "write_file":
            path = arguments.get("path", "")
            content = arguments.get("content", "")
            file_existed = state.get("file_existed", False)
            
            if file_existed:
                summary = self._generate_change_summary(content)
                self._renderer.render_file_updated(filename=path, summary=summary)
            else:
                preview = self._generate_content_preview(content)
                self._renderer.render_file_created(filename=path, preview=preview)
        
        # Handle directory listing
        elif tool_name == "list_directory":
            path = arguments.get("path", ".")
            self._renderer.render_read_files(files=[f"📁 {path}"], failed=[])
        
        # Handle directory creation
        elif tool_name == "create_directory":
            path = arguments.get("path", "")
            self._renderer.render_file_created(filename=f"📁 {path}")
    
    def render_status_footer(
        self,
        is_free_tier: bool = False,
        tokens: Optional[Tuple[int, int]] = None,
        cost: Optional[float] = None
    ) -> None:
        """
        Render the status footer after response completion.
        
        Args:
            is_free_tier: Whether the provider is free-tier
            tokens: Optional (input, output) token tuple to override session total
            cost: Optional cost to override session total
            
        Requirements: 6.1, 6.2, 6.3, 6.4 - Status footer rendering
        """
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        
        # Use provided values or session totals
        final_tokens = tokens if tokens else self._total_tokens
        final_cost = cost if cost is not None else self._total_cost
        
        self._renderer.render_status(
            elapsed_time=elapsed,
            tokens=final_tokens if any(final_tokens) else None,
            credits=final_cost if final_cost > 0 else None,
            is_free=is_free_tier
        )
    
    def _extract_results_count(self, result: str) -> int:
        """
        Extract results count from a search result string.
        
        Args:
            result: Search result string
            
        Returns:
            Number of results found, or 0 if not determinable
        """
        if not result:
            return 0
        
        # Try to find patterns like "Found X matches" or "X results"
        import re
        patterns = [
            r'Found (\d+) match',
            r'(\d+) results?',
            r'(\d+) files?',
            r'Matches: (\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Count lines as a fallback (each line might be a result)
        lines = [l for l in result.strip().split('\n') if l.strip()]
        return len(lines) if lines else 0
    
    def _generate_content_preview(self, content: str, max_lines: int = 3) -> Optional[str]:
        """
        Generate a preview of file content.
        
        Args:
            content: Full file content
            max_lines: Maximum lines to include in preview
            
        Returns:
            Preview string or None if content is empty
        """
        if not content:
            return None
        
        lines = content.split('\n')[:max_lines]
        return '\n'.join(lines)
    
    def _generate_change_summary(self, content: str) -> Optional[str]:
        """
        Generate a summary of file changes.
        
        Args:
            content: New file content
            
        Returns:
            Summary string or None
        """
        if not content:
            return None
        
        lines = content.count('\n') + 1
        chars = len(content)
        return f"{lines} lines, {chars} characters"
