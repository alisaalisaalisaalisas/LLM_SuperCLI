"""I/O handlers for llm_supercli."""
from .bash_runner import BashRunner, run_command
from .file_loader import FileLoader, load_file
from .clipboard import ClipboardManager, get_clipboard, set_clipboard
from .deduplicator import OutputDeduplicator, deduplicate_content, get_deduplicator
from .chunk_deduplicator import (
    ChunkDeduplicator,
    ChunkDeduplicationResult,
    get_chunk_deduplicator,
    deduplicate_streaming_chunk,
    reset_chunk_deduplicator,
)
from .project_analyzer import (
    ProjectAnalysisDetector,
    ProjectAnalysisRequest,
    RecursiveDirectoryScanner,
    DirectoryTree,
    KeyFileDetector,
    KeyFileDetection,
    ProjectAnalysisEnforcer,
    get_project_analysis_enforcer,
    is_project_analysis_request,
    scan_directory_recursive,
    detect_key_files,
)
from .file_creation_enforcer import (
    FileCreationDetector,
    FileCreationRequest,
    FileCreationSession,
    CreatedFileRecord,
    DirectoryCreationChecker,
    FileCreationEnforcer,
    get_file_creation_enforcer,
    is_file_creation_request,
    needs_directory_creation,
)
from .error_handler import (
    ErrorType,
    ErrorResult,
    EmptyDirectoryHandler,
    WriteFailureHandler,
    CorruptedOutputHandler,
    ToolErrorHandler,
    get_error_handler,
    handle_empty_directory,
    handle_write_error,
    recover_corrupted_output,
)

__all__ = [
    'BashRunner', 'run_command',
    'FileLoader', 'load_file',
    'ClipboardManager', 'get_clipboard', 'set_clipboard',
    'OutputDeduplicator', 'deduplicate_content', 'get_deduplicator',
    # Chunk deduplication for streaming
    'ChunkDeduplicator', 'ChunkDeduplicationResult',
    'get_chunk_deduplicator', 'deduplicate_streaming_chunk', 'reset_chunk_deduplicator',
    # Project analysis enforcement
    'ProjectAnalysisDetector', 'ProjectAnalysisRequest',
    'RecursiveDirectoryScanner', 'DirectoryTree',
    'KeyFileDetector', 'KeyFileDetection',
    'ProjectAnalysisEnforcer', 'get_project_analysis_enforcer',
    'is_project_analysis_request', 'scan_directory_recursive', 'detect_key_files',
    # File creation enforcement
    'FileCreationDetector', 'FileCreationRequest',
    'FileCreationSession', 'CreatedFileRecord',
    'DirectoryCreationChecker', 'FileCreationEnforcer',
    'get_file_creation_enforcer', 'is_file_creation_request', 'needs_directory_creation',
    # Error handling
    'ErrorType', 'ErrorResult',
    'EmptyDirectoryHandler', 'WriteFailureHandler', 'CorruptedOutputHandler',
    'ToolErrorHandler', 'get_error_handler',
    'handle_empty_directory', 'handle_write_error', 'recover_corrupted_output',
]
