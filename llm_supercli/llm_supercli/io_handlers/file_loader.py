"""
File loader for llm_supercli.
Handles loading file contents via @file syntax.
"""
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ..utils import format_bytes


@dataclass
class LoadedFile:
    """Represents a loaded file."""
    path: str
    content: str
    size: int
    mime_type: str
    encoding: str
    is_binary: bool
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if file was loaded successfully."""
        return self.error is None
    
    def format_for_prompt(self) -> str:
        """Format file content for inclusion in prompt."""
        if self.error:
            return f"[Error loading {self.path}: {self.error}]"
        
        if self.is_binary:
            return f"[Binary file: {self.path} ({format_bytes(self.size)})]"
        
        filename = os.path.basename(self.path)
        extension = os.path.splitext(filename)[1].lstrip('.')
        
        return f"```{extension or 'text'}\n# File: {filename}\n{self.content}\n```"


class FileLoader:
    """
    Loads file contents for inclusion in prompts.
    
    Supports text files, binary detection, encoding handling,
    and size limits.
    """
    
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    MAX_TEXT_SIZE = 100 * 1024   # 100KB for text inclusion
    
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
        '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go',
        '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
        '.html', '.css', '.scss', '.sass', '.less',
        '.json', '.yaml', '.yml', '.toml', '.xml',
        '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1',
        '.r', '.m', '.lua', '.pl', '.vim', '.el',
        '.dockerfile', '.makefile', '.cmake',
        '.gitignore', '.env', '.ini', '.cfg', '.conf',
        '.rst', '.tex', '.org', '.adoc'
    }
    
    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
        '.mp3', '.wav', '.ogg', '.flac', '.aac',
        '.mp4', '.avi', '.mkv', '.mov', '.webm',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib',
        '.pyc', '.pyo', '.class', '.o', '.obj'
    }
    
    ENCODINGS = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii']
    
    def __init__(self, base_dir: Optional[str] = None) -> None:
        """
        Initialize file loader.
        
        Args:
            base_dir: Base directory for relative paths
        """
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()
    
    def load(self, path: str) -> LoadedFile:
        """
        Load a file.
        
        Args:
            path: File path (absolute or relative)
            
        Returns:
            LoadedFile with contents or error
        """
        try:
            file_path = self._resolve_path(path)
            
            if not file_path.exists():
                return LoadedFile(
                    path=path,
                    content="",
                    size=0,
                    mime_type="",
                    encoding="",
                    is_binary=False,
                    error=f"File not found: {path}"
                )
            
            if not file_path.is_file():
                # If it's a directory, list its contents
                if file_path.is_dir():
                    return self._load_directory(path, file_path)
                return LoadedFile(
                    path=path,
                    content="",
                    size=0,
                    mime_type="",
                    encoding="",
                    is_binary=False,
                    error=f"Not a file: {path}"
                )
            
            size = file_path.stat().st_size
            
            if size > self.MAX_FILE_SIZE:
                return LoadedFile(
                    path=path,
                    content="",
                    size=size,
                    mime_type="",
                    encoding="",
                    is_binary=False,
                    error=f"File too large: {format_bytes(size)} (max: {format_bytes(self.MAX_FILE_SIZE)})"
                )
            
            mime_type = self._get_mime_type(file_path)
            is_binary = self._is_binary(file_path)
            
            if is_binary:
                return LoadedFile(
                    path=str(file_path),
                    content="",
                    size=size,
                    mime_type=mime_type,
                    encoding="binary",
                    is_binary=True
                )
            
            content, encoding = self._read_text(file_path)
            
            if size > self.MAX_TEXT_SIZE:
                content = content[:self.MAX_TEXT_SIZE]
                content += f"\n\n... [truncated, showing first {format_bytes(self.MAX_TEXT_SIZE)} of {format_bytes(size)}]"
            
            return LoadedFile(
                path=str(file_path),
                content=content,
                size=size,
                mime_type=mime_type,
                encoding=encoding,
                is_binary=False
            )
            
        except PermissionError:
            return LoadedFile(
                path=path,
                content="",
                size=0,
                mime_type="",
                encoding="",
                is_binary=False,
                error=f"Permission denied: {path}"
            )
        except Exception as e:
            return LoadedFile(
                path=path,
                content="",
                size=0,
                mime_type="",
                encoding="",
                is_binary=False,
                error=str(e)
            )
    
    def _load_directory(self, path: str, dir_path: Path) -> LoadedFile:
        """Load directory listing."""
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            lines = [f"# Directory: {path}\n"]
            for item in items[:50]:  # Limit to 50 items
                prefix = "📁 " if item.is_dir() else "📄 "
                lines.append(f"{prefix}{item.name}")
            if len(list(dir_path.iterdir())) > 50:
                lines.append(f"... and {len(list(dir_path.iterdir())) - 50} more items")
            content = "\n".join(lines)
            return LoadedFile(
                path=path,
                content=content,
                size=len(content),
                mime_type="text/plain",
                encoding="utf-8",
                is_binary=False
            )
        except Exception as e:
            return LoadedFile(path=path, content="", size=0, mime_type="", encoding="", is_binary=False, error=str(e))
    
    def load_multiple(self, paths: List[str]) -> List[LoadedFile]:
        """
        Load multiple files.
        
        Args:
            paths: List of file paths
            
        Returns:
            List of LoadedFile objects
        """
        return [self.load(path) for path in paths]
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base directory."""
        path = path.strip()
        
        if path.startswith('~'):
            return Path(path).expanduser()
        
        p = Path(path)
        if p.is_absolute():
            return p
        
        return (self._base_dir / path).resolve()
    
    def _get_mime_type(self, path: Path) -> str:
        """Get MIME type for a file."""
        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type or "application/octet-stream"
    
    def _is_binary(self, path: Path) -> bool:
        """Check if a file is binary."""
        suffix = path.suffix.lower()
        
        if suffix in self.TEXT_EXTENSIONS:
            return False
        if suffix in self.BINARY_EXTENSIONS:
            return True
        
        try:
            with open(path, 'rb') as f:
                chunk = f.read(8192)
                if b'\x00' in chunk:
                    return True
                
                text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
                non_text = chunk.translate(None, text_chars)
                return len(non_text) / len(chunk) > 0.30
        except Exception:
            return True
    
    def _read_text(self, path: Path) -> Tuple[str, str]:
        """Read text file with encoding detection."""
        for encoding in self.ENCODINGS:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read(), encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read(), 'utf-8 (with replacements)'


_loader: Optional[FileLoader] = None


def get_loader() -> FileLoader:
    """Get the global file loader instance."""
    global _loader
    if _loader is None:
        _loader = FileLoader()
    return _loader


def load_file(path: str) -> LoadedFile:
    """Convenience function to load a file."""
    return get_loader().load(path)
