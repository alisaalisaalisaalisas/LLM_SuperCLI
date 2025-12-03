"""
File creation enforcement module.

This module provides functionality to detect file creation requests,
enforce write_file tool usage, and track created files for confirmation.

Requirements:
- 2.1: Invoke write_file with appropriate path and content for each file
- 2.2: Create each file sequentially using separate write_file calls
- 2.3: Create directory structure before writing nested files
- 2.4: Confirm which files were created and their locations
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple


@dataclass
class FileCreationRequest:
    """
    Represents a detected file creation request.
    
    Attributes:
        detected: Whether a file creation request was detected
        request_type: Type of creation (e.g., "create_file", "create_project", "build")
        confidence: Confidence level (0.0 to 1.0)
        original_text: The original text that triggered detection
    """
    detected: bool
    request_type: str = ""
    confidence: float = 0.0
    original_text: str = ""


@dataclass
class CreatedFileRecord:
    """
    Record of a file that was created.
    
    Attributes:
        path: The file path that was created
        success: Whether the creation was successful
        is_directory: Whether this is a directory
        error: Error message if creation failed
    """
    path: str
    success: bool = True
    is_directory: bool = False
    error: str = ""


@dataclass
class FileCreationSession:
    """
    Tracks files created during a session.
    
    Attributes:
        files: List of files created
        directories: List of directories created
        failed: List of files that failed to create
    """
    files: List[CreatedFileRecord] = field(default_factory=list)
    directories: List[CreatedFileRecord] = field(default_factory=list)
    failed: List[CreatedFileRecord] = field(default_factory=list)
    
    def add_file(self, path: str, success: bool = True, error: str = "") -> None:
        """Add a file creation record."""
        record = CreatedFileRecord(path=path, success=success, error=error)
        if success:
            self.files.append(record)
        else:
            self.failed.append(record)

    def add_directory(self, path: str, success: bool = True, error: str = "") -> None:
        """Add a directory creation record."""
        record = CreatedFileRecord(path=path, success=success, is_directory=True, error=error)
        if success:
            self.directories.append(record)
        else:
            self.failed.append(record)
    
    @property
    def total_created(self) -> int:
        """Get total number of successfully created items."""
        return len(self.files) + len(self.directories)
    
    @property
    def total_failed(self) -> int:
        """Get total number of failed items."""
        return len(self.failed)
    
    def get_summary(self) -> str:
        """Get a summary of created files."""
        parts = []
        if self.files:
            parts.append(f"{len(self.files)} file(s)")
        if self.directories:
            parts.append(f"{len(self.directories)} directory(ies)")
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        return ", ".join(parts) if parts else "No files created"
    
    def clear(self) -> None:
        """Clear all records."""
        self.files.clear()
        self.directories.clear()
        self.failed.clear()


class FileCreationDetector:
    """
    Detects file creation requests in user input.
    
    This class analyzes user messages to identify when they're asking
    for file creation, project scaffolding, or code generation.
    
    Requirements: 2.1 - Detect "create file/project" type requests
    """
    
    # Patterns that indicate a file creation request
    # Each tuple: (pattern, request_type, confidence_boost)
    CREATION_PATTERNS: List[Tuple[str, str, float]] = [
        # Direct file creation requests
        (r"(?i)\b(create|make|write|generate|build)\s+(a\s+)?(new\s+)?(file|script|program)\b", "create_file", 0.3),
        (r"(?i)\b(create|make|write|generate|build)\s+(a\s+)?(new\s+)?(\w+\.\w+)\b", "create_file", 0.3),
        (r"(?i)\b(create|make|write|generate|build)\s+(me\s+)?(a\s+)?(file|script|program)\b", "create_file", 0.3),
        
        # Project creation requests
        (r"(?i)\b(create|make|build|scaffold|generate)\s+(a\s+)?(new\s+)?(project|app|application)\b", "create_project", 0.4),
        (r"(?i)\b(set\s+up|setup|initialize|init)\s+(a\s+)?(new\s+)?(project|app|application)\b", "create_project", 0.4),
        (r"(?i)\b(start|begin)\s+(a\s+)?(new\s+)?(project|app|application)\b", "create_project", 0.3),
        
        # Game/application creation
        (r"(?i)\b(create|make|build|write)\s+(a\s+)?(simple\s+)?(game|app|tool|utility)\b", "create_project", 0.4),
        (r"(?i)\b(create|make|build|write)\s+(me\s+)?(a\s+)?(game|app|tool|utility)\b", "create_project", 0.4),
        # More flexible patterns with language in between
        (r"(?i)\b(create|make|build|write)\s+(a\s+)?(simple\s+)?[\w\+]+\s+(game|app|tool|utility)\b", "create_project", 0.4),
        (r"(?i)\b(create|make|build|write)\s+(me\s+)?(a\s+)?[\w\+]+\s+(game|app|tool|utility)\b", "create_project", 0.4),
        
        # Code generation requests
        (r"(?i)\b(write|generate|create)\s+(the\s+)?(code|implementation)\s+(for|to)\b", "create_file", 0.3),
        (r"(?i)\b(implement|code)\s+(a\s+)?(new\s+)?(\w+)\s+(class|function|module)\b", "create_file", 0.3),
        
        # Specific file type creation
        (r"(?i)\b(create|make|write)\s+(a\s+)?(python|javascript|typescript|c\+\+|rust|go)\s+(file|script|program)\b", "create_file", 0.4),
        (r"(?i)\b(create|make|write)\s+(a\s+)?\.?(py|js|ts|cpp|rs|go|java|rb)\s+file\b", "create_file", 0.4),
        
        # Save/output to file
        (r"(?i)\b(save|output|write)\s+(this|it|that)\s+(to|as)\s+(a\s+)?file\b", "create_file", 0.3),
        (r"(?i)\b(save|output|write)\s+(to|as)\s+['\"]?[\w\-\_\.\/]+\.\w+['\"]?\b", "create_file", 0.4),
    ]
    
    def __init__(self) -> None:
        """Initialize the detector with compiled patterns."""
        self._patterns = [
            (re.compile(pattern), req_type, boost)
            for pattern, req_type, boost in self.CREATION_PATTERNS
        ]
    
    def detect(self, user_input: str) -> FileCreationRequest:
        """
        Detect if user input is requesting file creation.
        
        Args:
            user_input: The user's message text
            
        Returns:
            FileCreationRequest with detection results
            
        Requirements: 2.1 - Detect "create file/project" type requests
        """
        if not user_input:
            return FileCreationRequest(detected=False)
        
        best_match: Optional[FileCreationRequest] = None
        best_confidence = 0.0
        
        for pattern, req_type, boost in self._patterns:
            match = pattern.search(user_input)
            if match:
                # Base confidence + pattern-specific boost
                confidence = 0.5 + boost
                
                # Additional confidence boosts
                if "create" in user_input.lower():
                    confidence += 0.1
                if "file" in user_input.lower():
                    confidence += 0.1
                if "project" in user_input.lower():
                    confidence += 0.1
                if "game" in user_input.lower():
                    confidence += 0.1
                
                confidence = min(confidence, 1.0)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = FileCreationRequest(
                        detected=True,
                        request_type=req_type,
                        confidence=confidence,
                        original_text=match.group(0)
                    )
        
        return best_match or FileCreationRequest(detected=False)


class DirectoryCreationChecker:
    """
    Checks if directories need to be created before file writes.
    
    Requirements: 2.3 - Create directory structure before writing nested files
    """
    
    def __init__(self, working_dir: Optional[str] = None) -> None:
        """
        Initialize the checker.
        
        Args:
            working_dir: Working directory for resolving paths
        """
        self._working_dir = working_dir or os.getcwd()
    
    @property
    def working_dir(self) -> str:
        """Get the working directory."""
        return self._working_dir
    
    @working_dir.setter
    def working_dir(self, value: str) -> None:
        """Set the working directory."""
        self._working_dir = value
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory."""
        p = Path(path)
        if not p.is_absolute():
            p = Path(self._working_dir) / p
        return p.resolve()
    
    def needs_directory_creation(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Check if a file path requires directory creation.
        
        Args:
            file_path: The file path to check
            
        Returns:
            Tuple of (needs_creation, list_of_directories_to_create)
            
        Requirements: 2.3 - Detect when file path contains non-existent directories
        """
        resolved = self._resolve_path(file_path)
        parent = resolved.parent
        
        # If parent exists, no directories needed
        if parent.exists():
            return (False, [])
        
        # Find all directories that need to be created
        dirs_to_create: List[str] = []
        current = parent
        
        while not current.exists() and current != current.parent:
            # Get path relative to working dir for display
            try:
                rel_path = current.relative_to(self._working_dir)
                dirs_to_create.insert(0, str(rel_path))
            except ValueError:
                dirs_to_create.insert(0, str(current))
            current = current.parent
        
        return (len(dirs_to_create) > 0, dirs_to_create)
    
    def get_directories_for_files(self, file_paths: List[str]) -> List[str]:
        """
        Get all directories that need to be created for a list of files.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Deduplicated list of directories to create (in order)
            
        Requirements: 2.3 - Create directory structure before writing nested files
        """
        all_dirs: Set[str] = set()
        ordered_dirs: List[str] = []
        
        for file_path in file_paths:
            needs, dirs = self.needs_directory_creation(file_path)
            if needs:
                for d in dirs:
                    if d not in all_dirs:
                        all_dirs.add(d)
                        ordered_dirs.append(d)
        
        return ordered_dirs


class FileCreationEnforcer:
    """
    Enforces proper tool usage for file creation requests.
    
    This class coordinates detection of creation requests, directory
    checking, and tracking of created files.
    
    Requirements:
    - 2.1: Detect creation requests and verify write_file was invoked
    - 2.2: Track that each file is created with separate write_file calls
    - 2.3: Ensure directories are created before nested file writes
    - 2.4: Track created files for confirmation display
    """
    
    def __init__(self, working_dir: Optional[str] = None) -> None:
        """Initialize the enforcer with all component detectors."""
        self._creation_detector = FileCreationDetector()
        self._directory_checker = DirectoryCreationChecker(working_dir)
        self._session = FileCreationSession()
    
    @property
    def working_dir(self) -> str:
        """Get the working directory."""
        return self._directory_checker.working_dir
    
    @working_dir.setter
    def working_dir(self, value: str) -> None:
        """Set the working directory."""
        self._directory_checker.working_dir = value
    
    @property
    def session(self) -> FileCreationSession:
        """Get the current file creation session."""
        return self._session
    
    def is_creation_request(self, user_input: str) -> FileCreationRequest:
        """
        Check if user input is a file creation request.
        
        Args:
            user_input: The user's message
            
        Returns:
            FileCreationRequest with detection results
        """
        return self._creation_detector.detect(user_input)
    
    def needs_directory_creation(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Check if a file path requires directory creation.
        
        Args:
            file_path: The file path to check
            
        Returns:
            Tuple of (needs_creation, list_of_directories_to_create)
        """
        return self._directory_checker.needs_directory_creation(file_path)
    
    def get_directories_for_files(self, file_paths: List[str]) -> List[str]:
        """
        Get all directories that need to be created for a list of files.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Deduplicated list of directories to create
        """
        return self._directory_checker.get_directories_for_files(file_paths)
    
    def start_session(self) -> None:
        """Start a new file creation tracking session."""
        self._session.clear()
    
    def record_file_created(self, path: str, success: bool = True, error: str = "") -> None:
        """
        Record that a file was created.
        
        Args:
            path: The file path that was created
            success: Whether creation was successful
            error: Error message if failed
            
        Requirements: 2.4 - Track created files for confirmation
        """
        self._session.add_file(path, success, error)
    
    def record_directory_created(self, path: str, success: bool = True, error: str = "") -> None:
        """
        Record that a directory was created.
        
        Args:
            path: The directory path that was created
            success: Whether creation was successful
            error: Error message if failed
        """
        self._session.add_directory(path, success, error)
    
    def verify_write_file_called(
        self,
        tool_calls: List[str],
        user_input: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that write_file was called for a creation request.
        
        Args:
            tool_calls: List of tool names that were called
            user_input: The original user input
            
        Returns:
            Tuple of (is_valid, warning_message)
            - is_valid: True if write_file was called or not needed
            - warning_message: Warning if write_file should have been called
            
        Requirements: 2.1 - Verify write_file was invoked for file creation
        """
        creation_request = self.is_creation_request(user_input)
        
        if not creation_request.detected:
            return (True, None)
        
        if creation_request.confidence < 0.6:
            return (True, None)
        
        if "write_file" in tool_calls:
            return (True, None)
        
        return (
            False,
            f"File creation was requested but write_file was not called. "
            f"The assistant should create files using the write_file tool."
        )
    
    def get_created_files_summary(self) -> List[str]:
        """
        Get a list of created file paths for confirmation display.
        
        Returns:
            List of file paths that were created
            
        Requirements: 2.4 - Confirm which files were created
        """
        return [record.path for record in self._session.files]
    
    def get_created_directories_summary(self) -> List[str]:
        """
        Get a list of created directory paths.
        
        Returns:
            List of directory paths that were created
        """
        return [record.path for record in self._session.directories]
    
    def get_failed_summary(self) -> List[Tuple[str, str]]:
        """
        Get a list of failed creations with error messages.
        
        Returns:
            List of (path, error) tuples for failed creations
        """
        return [(record.path, record.error) for record in self._session.failed]


# Module-level singleton
_enforcer: Optional[FileCreationEnforcer] = None


def get_file_creation_enforcer() -> FileCreationEnforcer:
    """Get the global FileCreationEnforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = FileCreationEnforcer()
    return _enforcer


def is_file_creation_request(user_input: str) -> FileCreationRequest:
    """
    Convenience function to check if input is a file creation request.
    
    Args:
        user_input: The user's message
        
    Returns:
        FileCreationRequest with detection results
    """
    return get_file_creation_enforcer().is_creation_request(user_input)


def needs_directory_creation(file_path: str) -> Tuple[bool, List[str]]:
    """
    Convenience function to check if directories need to be created.
    
    Args:
        file_path: The file path to check
        
    Returns:
        Tuple of (needs_creation, list_of_directories_to_create)
    """
    return get_file_creation_enforcer().needs_directory_creation(file_path)
