"""
Project analysis enforcement module.

This module provides functionality to detect project analysis requests,
enforce directory scanning, and identify key files for reading.

Requirements:
- 1.1: Invoke list_directory with path "." for project analysis
- 1.2: Recursively scan subdirectories to build complete file tree
- 1.3: Read key files (README, config files, main entry points) before analysis
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple


@dataclass
class ProjectAnalysisRequest:
    """
    Represents a detected project analysis request.
    
    Attributes:
        detected: Whether a project analysis request was detected
        request_type: Type of analysis (e.g., "analyze", "explore", "understand")
        confidence: Confidence level (0.0 to 1.0)
        original_text: The original text that triggered detection
    """
    detected: bool
    request_type: str = ""
    confidence: float = 0.0
    original_text: str = ""


@dataclass
class DirectoryTree:
    """
    Represents a directory tree structure.
    
    Attributes:
        path: The root path of the tree
        files: List of file paths relative to root
        directories: List of directory paths relative to root
        total_files: Total number of files in the tree
        total_directories: Total number of directories in the tree
    """
    path: str
    files: List[str] = field(default_factory=list)
    directories: List[str] = field(default_factory=list)
    total_files: int = 0
    total_directories: int = 0


@dataclass
class KeyFileDetection:
    """
    Represents detected key files in a project.
    
    Attributes:
        readme_files: List of README files found
        config_files: List of configuration files found
        entry_points: List of main entry point files found
        all_key_files: Combined list of all key files
    """
    readme_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    
    @property
    def all_key_files(self) -> List[str]:
        """Get all key files combined."""
        return self.readme_files + self.config_files + self.entry_points


class ProjectAnalysisDetector:
    """
    Detects project analysis requests in user input.
    
    This class analyzes user messages to identify when they're asking
    for project analysis, exploration, or understanding.
    
    Requirements: 1.1 - Detect "analyze project" type requests
    """
    
    # Patterns that indicate a project analysis request
    # Each tuple: (pattern, request_type, confidence_boost)
    ANALYSIS_PATTERNS: List[Tuple[str, str, float]] = [
        # Direct analysis requests
        (r"(?i)\b(analyze|analyse)\s+(this\s+)?(project|codebase|code|repo|repository)\b", "analyze", 0.3),
        (r"(?i)\bwhat('s| is)\s+(in\s+)?(this\s+)?(project|codebase|directory|folder)\b", "explore", 0.2),
        (r"(?i)\b(explore|examine|inspect|review)\s+(this\s+)?(project|codebase|code|repo)\b", "explore", 0.3),
        (r"(?i)\b(understand|explain)\s+(this\s+)?(project|codebase|code)\b", "understand", 0.2),
        
        # Directory/file exploration requests
        (r"(?i)\bwhat\s+files?\s+(are|do)\s+(here|exist|we have)\b", "explore", 0.2),
        (r"(?i)\bshow\s+me\s+(the\s+)?(files?|structure|layout)\b", "explore", 0.2),
        (r"(?i)\blist\s+(the\s+)?(files?|contents?|structure)\b", "explore", 0.2),
        (r"(?i)\b(scan|check)\s+(this\s+)?(directory|folder|project)\b", "explore", 0.2),
        
        # Project overview requests
        (r"(?i)\bgive\s+me\s+(an?\s+)?(overview|summary)\s+(of\s+)?(this\s+)?(project|codebase)?\b", "overview", 0.3),
        (r"(?i)\b(project|codebase)\s+(overview|summary|structure)\b", "overview", 0.2),
        (r"(?i)\bhow\s+(is|does)\s+(this\s+)?(project|codebase)\s+(structured|organized|work)\b", "understand", 0.2),
        
        # Code understanding requests
        (r"(?i)\bwhat\s+(does|is)\s+(this\s+)?(project|code|codebase)\s+(do|about|for)\b", "understand", 0.2),
        (r"(?i)\b(tell|explain)\s+(me\s+)?(about\s+)?(this\s+)?(project|codebase)\b", "understand", 0.2),
    ]
    
    def __init__(self) -> None:
        """Initialize the detector with compiled patterns."""
        self._patterns = [
            (re.compile(pattern), req_type, boost)
            for pattern, req_type, boost in self.ANALYSIS_PATTERNS
        ]
    
    def detect(self, user_input: str) -> ProjectAnalysisRequest:
        """
        Detect if user input is requesting project analysis.
        
        Args:
            user_input: The user's message text
            
        Returns:
            ProjectAnalysisRequest with detection results
            
        Requirements: 1.1 - Detect "analyze project" type requests
        """
        if not user_input:
            return ProjectAnalysisRequest(detected=False)
        
        best_match: Optional[ProjectAnalysisRequest] = None
        best_confidence = 0.0
        
        for pattern, req_type, boost in self._patterns:
            match = pattern.search(user_input)
            if match:
                # Base confidence + pattern-specific boost
                confidence = 0.5 + boost
                
                # Additional confidence boosts
                if "project" in user_input.lower():
                    confidence += 0.1
                if "codebase" in user_input.lower():
                    confidence += 0.1
                if "analyze" in user_input.lower() or "analyse" in user_input.lower():
                    confidence += 0.1
                
                confidence = min(confidence, 1.0)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = ProjectAnalysisRequest(
                        detected=True,
                        request_type=req_type,
                        confidence=confidence,
                        original_text=match.group(0)
                    )
        
        return best_match or ProjectAnalysisRequest(detected=False)


class RecursiveDirectoryScanner:
    """
    Scans directories recursively to build a complete file tree.
    
    Requirements: 1.2 - Recursively scan subdirectories to build complete file tree
    """
    
    # Directories to skip during scanning
    SKIP_DIRECTORIES: Set[str] = {
        ".git", ".svn", ".hg",  # Version control
        "node_modules", "venv", ".venv", "env", ".env",  # Dependencies
        "__pycache__", ".pytest_cache", ".mypy_cache",  # Python caches
        ".idea", ".vscode",  # IDE directories
        "dist", "build", "target", "out",  # Build outputs
        ".next", ".nuxt",  # Framework caches
        "coverage", ".coverage",  # Test coverage
    }
    
    # Maximum depth to prevent infinite recursion
    MAX_DEPTH: int = 10
    
    # Maximum files to scan to prevent memory issues
    MAX_FILES: int = 1000
    
    def __init__(
        self,
        skip_directories: Optional[Set[str]] = None,
        max_depth: int = MAX_DEPTH,
        max_files: int = MAX_FILES
    ) -> None:
        """
        Initialize the scanner.
        
        Args:
            skip_directories: Set of directory names to skip
            max_depth: Maximum recursion depth
            max_files: Maximum number of files to scan
        """
        self._skip_dirs = skip_directories or self.SKIP_DIRECTORIES
        self._max_depth = max_depth
        self._max_files = max_files
    
    def scan(self, root_path: str) -> DirectoryTree:
        """
        Recursively scan a directory and build a file tree.
        
        Args:
            root_path: The root directory path to scan
            
        Returns:
            DirectoryTree containing all files and directories
            
        Requirements: 1.2 - Recursively scan subdirectories
        """
        root = Path(root_path).resolve()
        
        if not root.exists():
            return DirectoryTree(path=root_path)
        
        if not root.is_dir():
            return DirectoryTree(path=root_path)
        
        files: List[str] = []
        directories: List[str] = []
        
        self._scan_recursive(root, root, files, directories, 0)
        
        return DirectoryTree(
            path=root_path,
            files=files,
            directories=directories,
            total_files=len(files),
            total_directories=len(directories)
        )
    
    def _scan_recursive(
        self,
        root: Path,
        current: Path,
        files: List[str],
        directories: List[str],
        depth: int
    ) -> None:
        """
        Recursively scan a directory.
        
        Args:
            root: The root path for relative path calculation
            current: The current directory being scanned
            files: List to append file paths to
            directories: List to append directory paths to
            depth: Current recursion depth
        """
        if depth > self._max_depth:
            return
        
        if len(files) >= self._max_files:
            return
        
        try:
            for item in sorted(current.iterdir()):
                if len(files) >= self._max_files:
                    break
                
                try:
                    relative_path = str(item.relative_to(root))
                    
                    if item.is_dir():
                        # Skip certain directories
                        if item.name in self._skip_dirs:
                            continue
                        if item.name.startswith('.') and item.name not in {'.github', '.kiro'}:
                            continue
                        
                        directories.append(relative_path)
                        self._scan_recursive(root, item, files, directories, depth + 1)
                    
                    elif item.is_file():
                        files.append(relative_path)
                
                except (PermissionError, OSError):
                    # Skip files/directories we can't access
                    continue
        
        except (PermissionError, OSError):
            # Skip directories we can't access
            pass


class KeyFileDetector:
    """
    Detects key files in a project that should be read for analysis.
    
    Key files include:
    - README files (README.md, README.txt, etc.)
    - Configuration files (package.json, pyproject.toml, etc.)
    - Main entry points (main.py, index.js, etc.)
    
    Requirements: 1.3 - Identify README, config files, main entry points
    """
    
    # README file patterns (case-insensitive)
    README_PATTERNS: List[str] = [
        r"^readme(\.(md|txt|rst|markdown))?$",
        r"^readme\..*$",
    ]
    
    # Configuration file names
    CONFIG_FILES: Set[str] = {
        # Python
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
        "Pipfile", "poetry.lock", "tox.ini", "pytest.ini",
        # JavaScript/Node
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "tsconfig.json", "jsconfig.json", ".eslintrc.json", ".prettierrc",
        # Rust
        "Cargo.toml", "Cargo.lock",
        # Go
        "go.mod", "go.sum",
        # Ruby
        "Gemfile", "Gemfile.lock", ".ruby-version",
        # Java/Kotlin
        "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
        # Docker
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        # CI/CD
        ".travis.yml", ".gitlab-ci.yml", "Jenkinsfile",
        # General
        "Makefile", "CMakeLists.txt", ".editorconfig",
    }
    
    # Main entry point patterns
    ENTRY_POINT_PATTERNS: List[Tuple[str, int]] = [
        # Pattern, priority (lower is higher priority)
        (r"^main\.(py|js|ts|go|rs|rb|java|kt|c|cpp)$", 1),
        (r"^index\.(py|js|ts|jsx|tsx)$", 1),
        (r"^app\.(py|js|ts|jsx|tsx)$", 2),
        (r"^cli\.(py|js|ts)$", 2),
        (r"^__main__\.py$", 1),
        (r"^src/main\.(py|js|ts|go|rs)$", 2),
        (r"^src/index\.(py|js|ts|jsx|tsx)$", 2),
        (r"^src/app\.(py|js|ts|jsx|tsx)$", 3),
        (r"^lib/.*\.(py|js|ts)$", 4),
    ]
    
    def __init__(self) -> None:
        """Initialize the detector with compiled patterns."""
        self._readme_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.README_PATTERNS
        ]
        self._entry_patterns = [
            (re.compile(pattern), priority)
            for pattern, priority in self.ENTRY_POINT_PATTERNS
        ]
    
    def detect(self, files: List[str]) -> KeyFileDetection:
        """
        Detect key files from a list of file paths.
        
        Args:
            files: List of file paths to analyze
            
        Returns:
            KeyFileDetection with categorized key files
            
        Requirements: 1.3 - Identify README, config files, main entry points
        """
        readme_files: List[str] = []
        config_files: List[str] = []
        entry_points: List[Tuple[str, int]] = []  # (path, priority)
        
        for file_path in files:
            path = Path(file_path)
            filename = path.name
            
            # Check for README files
            for pattern in self._readme_patterns:
                if pattern.match(filename):
                    readme_files.append(file_path)
                    break
            
            # Check for config files
            if filename in self.CONFIG_FILES:
                config_files.append(file_path)
            
            # Check for entry points
            for pattern, priority in self._entry_patterns:
                if pattern.match(file_path):
                    entry_points.append((file_path, priority))
                    break
        
        # Sort entry points by priority and take top ones
        entry_points.sort(key=lambda x: x[1])
        sorted_entry_points = [path for path, _ in entry_points[:5]]
        
        return KeyFileDetection(
            readme_files=readme_files,
            config_files=config_files,
            entry_points=sorted_entry_points
        )


class ProjectAnalysisEnforcer:
    """
    Enforces proper tool usage for project analysis requests.
    
    This class coordinates detection of analysis requests, directory scanning,
    and key file identification to ensure the LLM properly uses tools.
    
    Requirements:
    - 1.1: Detect analysis requests and verify list_directory was invoked
    - 1.2: Build complete file tree through recursive scanning
    - 1.3: Identify key files for reading
    """
    
    def __init__(self) -> None:
        """Initialize the enforcer with all component detectors."""
        self._analysis_detector = ProjectAnalysisDetector()
        self._directory_scanner = RecursiveDirectoryScanner()
        self._key_file_detector = KeyFileDetector()
    
    def is_analysis_request(self, user_input: str) -> ProjectAnalysisRequest:
        """
        Check if user input is a project analysis request.
        
        Args:
            user_input: The user's message
            
        Returns:
            ProjectAnalysisRequest with detection results
        """
        return self._analysis_detector.detect(user_input)
    
    def scan_directory(self, path: str = ".") -> DirectoryTree:
        """
        Scan a directory recursively.
        
        Args:
            path: The directory path to scan
            
        Returns:
            DirectoryTree with complete file structure
        """
        return self._directory_scanner.scan(path)
    
    def detect_key_files(self, files: List[str]) -> KeyFileDetection:
        """
        Detect key files from a list of file paths.
        
        Args:
            files: List of file paths
            
        Returns:
            KeyFileDetection with categorized key files
        """
        return self._key_file_detector.detect(files)
    
    def verify_list_directory_called(
        self,
        tool_calls: List[str],
        user_input: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify that list_directory was called for an analysis request.
        
        Args:
            tool_calls: List of tool names that were called
            user_input: The original user input
            
        Returns:
            Tuple of (is_valid, warning_message)
            - is_valid: True if list_directory was called or not needed
            - warning_message: Warning if list_directory should have been called
            
        Requirements: 1.1 - Verify list_directory was invoked before analysis
        """
        analysis_request = self.is_analysis_request(user_input)
        
        if not analysis_request.detected:
            return (True, None)
        
        if analysis_request.confidence < 0.6:
            return (True, None)
        
        if "list_directory" in tool_calls:
            return (True, None)
        
        return (
            False,
            f"Project analysis was requested but list_directory was not called. "
            f"The assistant should scan the directory structure before providing analysis."
        )
    
    def get_recommended_tool_sequence(
        self,
        user_input: str,
        current_directory: str = "."
    ) -> List[Tuple[str, dict]]:
        """
        Get the recommended sequence of tool calls for a request.
        
        Args:
            user_input: The user's message
            current_directory: The current working directory
            
        Returns:
            List of (tool_name, arguments) tuples for recommended calls
            
        Requirements: 1.1, 1.2, 1.3 - Recommend proper tool sequence
        """
        analysis_request = self.is_analysis_request(user_input)
        
        if not analysis_request.detected or analysis_request.confidence < 0.6:
            return []
        
        recommendations: List[Tuple[str, dict]] = []
        
        # Step 1: Always start with list_directory
        recommendations.append(("list_directory", {"path": "."}))
        
        # Step 2: Scan to find key files
        tree = self.scan_directory(current_directory)
        key_files = self.detect_key_files(tree.files)
        
        # Step 3: Recommend reading key files
        for readme in key_files.readme_files[:1]:  # Just first README
            recommendations.append(("read_file", {"path": readme}))
        
        for config in key_files.config_files[:2]:  # Top 2 config files
            recommendations.append(("read_file", {"path": config}))
        
        for entry in key_files.entry_points[:2]:  # Top 2 entry points
            recommendations.append(("read_file", {"path": entry}))
        
        return recommendations


# Module-level singleton
_enforcer: Optional[ProjectAnalysisEnforcer] = None


def get_project_analysis_enforcer() -> ProjectAnalysisEnforcer:
    """Get the global ProjectAnalysisEnforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = ProjectAnalysisEnforcer()
    return _enforcer


def is_project_analysis_request(user_input: str) -> ProjectAnalysisRequest:
    """
    Convenience function to check if input is a project analysis request.
    
    Args:
        user_input: The user's message
        
    Returns:
        ProjectAnalysisRequest with detection results
    """
    return get_project_analysis_enforcer().is_analysis_request(user_input)


def scan_directory_recursive(path: str = ".") -> DirectoryTree:
    """
    Convenience function to scan a directory recursively.
    
    Args:
        path: The directory path to scan
        
    Returns:
        DirectoryTree with complete file structure
    """
    return get_project_analysis_enforcer().scan_directory(path)


def detect_key_files(files: List[str]) -> KeyFileDetection:
    """
    Convenience function to detect key files.
    
    Args:
        files: List of file paths
        
    Returns:
        KeyFileDetection with categorized key files
    """
    return get_project_analysis_enforcer().detect_key_files(files)
