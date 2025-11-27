"""
Clipboard management for llm_supercli.
Cross-platform clipboard access.
"""
import subprocess
from typing import Optional

from ..utils import is_windows, is_macos, is_linux


class ClipboardManager:
    """
    Cross-platform clipboard manager.
    
    Provides read/write access to the system clipboard.
    """
    
    def __init__(self) -> None:
        """Initialize clipboard manager."""
        self._impl = self._detect_implementation()
    
    def _detect_implementation(self) -> str:
        """Detect the best clipboard implementation."""
        if is_windows():
            return "windows"
        elif is_macos():
            return "macos"
        elif is_linux():
            for cmd in ["xclip", "xsel", "wl-copy"]:
                try:
                    subprocess.run(
                        ["which", cmd],
                        capture_output=True,
                        check=True
                    )
                    return cmd
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            return "none"
        return "none"
    
    def get(self) -> Optional[str]:
        """
        Get content from clipboard.
        
        Returns:
            Clipboard content or None if unavailable
        """
        try:
            if self._impl == "windows":
                return self._windows_get()
            elif self._impl == "macos":
                return self._macos_get()
            elif self._impl == "xclip":
                return self._xclip_get()
            elif self._impl == "xsel":
                return self._xsel_get()
            elif self._impl == "wl-copy":
                return self._wayland_get()
        except Exception:
            pass
        return None
    
    def set(self, content: str) -> bool:
        """
        Set clipboard content.
        
        Args:
            content: Content to copy to clipboard
            
        Returns:
            True if successful
        """
        try:
            if self._impl == "windows":
                return self._windows_set(content)
            elif self._impl == "macos":
                return self._macos_set(content)
            elif self._impl == "xclip":
                return self._xclip_set(content)
            elif self._impl == "xsel":
                return self._xsel_set(content)
            elif self._impl == "wl-copy":
                return self._wayland_set(content)
        except Exception:
            pass
        return False
    
    def _windows_get(self) -> Optional[str]:
        """Get clipboard on Windows."""
        result = subprocess.run(
            ["powershell.exe", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    
    def _windows_set(self, content: str) -> bool:
        """Set clipboard on Windows."""
        escaped = content.replace("'", "''")
        result = subprocess.run(
            ["powershell.exe", "-Command", f"Set-Clipboard -Value '{escaped}'"],
            capture_output=True
        )
        return result.returncode == 0
    
    def _macos_get(self) -> Optional[str]:
        """Get clipboard on macOS."""
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else None
    
    def _macos_set(self, content: str) -> bool:
        """Set clipboard on macOS."""
        result = subprocess.run(
            ["pbcopy"],
            input=content,
            text=True,
            capture_output=True
        )
        return result.returncode == 0
    
    def _xclip_get(self) -> Optional[str]:
        """Get clipboard using xclip."""
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else None
    
    def _xclip_set(self, content: str) -> bool:
        """Set clipboard using xclip."""
        result = subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=content,
            text=True,
            capture_output=True
        )
        return result.returncode == 0
    
    def _xsel_get(self) -> Optional[str]:
        """Get clipboard using xsel."""
        result = subprocess.run(
            ["xsel", "--clipboard", "--output"],
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else None
    
    def _xsel_set(self, content: str) -> bool:
        """Set clipboard using xsel."""
        result = subprocess.run(
            ["xsel", "--clipboard", "--input"],
            input=content,
            text=True,
            capture_output=True
        )
        return result.returncode == 0
    
    def _wayland_get(self) -> Optional[str]:
        """Get clipboard on Wayland."""
        result = subprocess.run(
            ["wl-paste"],
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else None
    
    def _wayland_set(self, content: str) -> bool:
        """Set clipboard on Wayland."""
        result = subprocess.run(
            ["wl-copy"],
            input=content,
            text=True,
            capture_output=True
        )
        return result.returncode == 0
    
    @property
    def available(self) -> bool:
        """Check if clipboard is available."""
        return self._impl != "none"


_clipboard: Optional[ClipboardManager] = None


def get_clipboard_manager() -> ClipboardManager:
    """Get the global clipboard manager instance."""
    global _clipboard
    if _clipboard is None:
        _clipboard = ClipboardManager()
    return _clipboard


def get_clipboard() -> Optional[str]:
    """Get clipboard content."""
    return get_clipboard_manager().get()


def set_clipboard(content: str) -> bool:
    """Set clipboard content."""
    return get_clipboard_manager().set(content)
