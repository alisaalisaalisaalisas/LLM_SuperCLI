"""
ContextBuilder - Builds environment and project context for prompt generation.

This module provides the ContextBuilder class which assembles environment
information and project structure summaries for use in prompt sections.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class VariableError(Exception):
    """Raised when a required variable is missing during interpolation."""
    
    def __init__(self, variable_name: str, template_location: Optional[str] = None):
        self.variable_name = variable_name
        self.template_location = template_location
        message = f"Missing required variable: '{variable_name}'"
        if template_location:
            message += f" in template at {template_location}"
        super().__init__(message)


class ContextBuilder:
    """Builds context for prompt generation.
    
    The ContextBuilder is responsible for gathering environment information
    and building project structure summaries that can be used by prompt
    sections during rendering.
    
    Example:
        builder = ContextBuilder()
        env = builder.build_environment()
        # {'cwd': '/home/user/project', 'os_type': 'posix', 'shell': '/bin/bash', 'home': '/home/user'}
        
        summary = builder.build_project_summary(Path('/home/user/project'))
        # 'project/\\n├── src/\\n│   └── main.py\\n└── README.md'
    """
    
    # Default directories and files to exclude from project summary
    DEFAULT_EXCLUDES = {
        # Version control
        '.git', '.svn', '.hg',
        # Dependencies
        'node_modules', 'venv', '.venv', 'env', '.env',
        '__pycache__', '.pytest_cache', '.mypy_cache',
        '.tox', '.nox', 'eggs', '*.egg-info',
        # Build outputs
        'dist', 'build', 'target', 'out', 'bin', 'obj',
        # IDE
        '.idea', '.vscode', '.vs',
        # OS
        '.DS_Store', 'Thumbs.db',
    }
    
    # Maximum depth for project structure
    DEFAULT_MAX_DEPTH = 3
    
    # Maximum number of items to show per directory
    DEFAULT_MAX_ITEMS = 15
    
    def __init__(
        self,
        excludes: Optional[set[str]] = None,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_items: int = DEFAULT_MAX_ITEMS,
    ) -> None:
        """Initialize the ContextBuilder.
        
        Args:
            excludes: Set of directory/file names to exclude from project summary.
                     Defaults to DEFAULT_EXCLUDES if not provided.
            max_depth: Maximum depth to traverse for project structure.
            max_items: Maximum number of items to show per directory level.
        """
        self._excludes = excludes if excludes is not None else self.DEFAULT_EXCLUDES.copy()
        self._max_depth = max_depth
        self._max_items = max_items

    def build_environment(self) -> dict[str, str]:
        """Build environment context.
        
        Gathers information about the current working environment including
        the working directory, operating system type, shell, and home directory.
        
        This method always returns fresh values reflecting the current state
        of the environment at the time of the call.
        
        Returns:
            A dictionary containing environment information:
            - cwd: Current working directory path
            - os_type: Operating system type (e.g., 'nt', 'posix')
            - shell: Shell path or name
            - home: User's home directory path
            
        Example:
            >>> builder = ContextBuilder()
            >>> env = builder.build_environment()
            >>> env['os_type']
            'posix'
        """
        return {
            "cwd": os.getcwd(),
            "os_type": os.name,
            "shell": os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown")),
            "home": str(Path.home()),
        }
    
    def build_project_summary(self, cwd: Path) -> Optional[str]:
        """Build a summary of the project structure.
        
        Creates a tree-like representation of the project directory structure,
        excluding common non-essential directories like node_modules, .git, etc.
        
        Args:
            cwd: The root directory to summarize.
            
        Returns:
            A string containing the project structure in tree format,
            or None if the directory doesn't exist or is empty.
            
        Example:
            >>> builder = ContextBuilder()
            >>> summary = builder.build_project_summary(Path('/home/user/project'))
            >>> print(summary)
            project/
            ├── src/
            │   ├── main.py
            │   └── utils.py
            ├── tests/
            └── README.md
        """
        if not cwd.exists() or not cwd.is_dir():
            return None
        
        lines = [f"{cwd.name}/"]
        self._build_tree(cwd, lines, "", 0)
        
        if len(lines) <= 1:
            return None
        
        return "\n".join(lines)
    
    def _build_tree(
        self,
        directory: Path,
        lines: list[str],
        prefix: str,
        depth: int,
    ) -> None:
        """Recursively build the tree structure.
        
        Args:
            directory: Current directory to process.
            lines: List to append tree lines to.
            prefix: Current line prefix for tree formatting.
            depth: Current depth in the tree.
        """
        if depth >= self._max_depth:
            return
        
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return
        
        # Filter out excluded entries
        entries = [e for e in entries if not self._should_exclude(e)]
        
        # Limit number of entries
        truncated = len(entries) > self._max_items
        if truncated:
            entries = entries[:self._max_items]
        
        for i, entry in enumerate(entries):
            is_last = (i == len(entries) - 1) and not truncated
            connector = "└── " if is_last else "├── "
            
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if is_last else "│   "
                self._build_tree(entry, lines, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")
        
        if truncated:
            lines.append(f"{prefix}└── ... ({len(list(directory.iterdir())) - self._max_items} more)")
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from the summary.
        
        Args:
            path: The path to check.
            
        Returns:
            True if the path should be excluded, False otherwise.
        """
        name = path.name
        
        # Check exact matches
        if name in self._excludes:
            return True
        
        # Check pattern matches (e.g., *.egg-info)
        for pattern in self._excludes:
            if '*' in pattern:
                # Simple glob pattern matching
                regex = pattern.replace('.', r'\.').replace('*', '.*')
                if re.match(f"^{regex}$", name):
                    return True
        
        # Exclude hidden files/directories (starting with .)
        if name.startswith('.'):
            return True
        
        return False


def interpolate(
    template: str,
    variables: dict[str, str],
    required_vars: Optional[set[str]] = None,
    template_location: Optional[str] = None,
) -> str:
    """Interpolate variables into a template string.
    
    Replaces {{variable}} placeholders in the template with corresponding
    values from the variables dictionary.
    
    Args:
        template: The template string containing {{variable}} placeholders.
        variables: Dictionary mapping variable names to their values.
        required_vars: Set of variable names that must be present.
                      If a required variable is missing, raises VariableError.
                      If None, all variables in the template are considered optional.
        template_location: Optional location string for error messages.
        
    Returns:
        The template with all placeholders replaced.
        
    Raises:
        VariableError: If a required variable is missing from the variables dict.
        
    Example:
        >>> interpolate("Hello, {{name}}!", {"name": "World"})
        'Hello, World!'
        
        >>> interpolate("Hello, {{name}}!", {})  # Optional by default
        'Hello, !'
        
        >>> interpolate("Hello, {{name}}!", {}, required_vars={"name"})
        VariableError: Missing required variable: 'name'
    """
    required_vars = required_vars or set()
    
    # Find all placeholders in the template
    pattern = r'\{\{(\w+)\}\}'
    
    def replace_var(match: re.Match) -> str:
        var_name = match.group(1)
        
        if var_name in variables:
            return variables[var_name]
        elif var_name in required_vars:
            raise VariableError(var_name, template_location)
        else:
            # Optional variable - replace with empty string
            return ""
    
    return re.sub(pattern, replace_var, template)
