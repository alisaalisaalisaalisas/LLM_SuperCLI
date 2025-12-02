"""
Update cache module for caching version check results.
Manages caching of npm registry version checks to minimize network requests.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .constants import CONFIG_DIR


@dataclass
class CachedVersionInfo:
    """Cached version information from npm registry."""
    latest_version: str
    checked_at: str  # ISO format datetime string


class UpdateCache:
    """
    Manages caching of version check results.
    
    Caches the latest version information from npm registry to avoid
    repeated network requests. Cache is valid for 24 hours.
    """
    
    CACHE_TTL_HOURS: int = 24
    CACHE_FILENAME: str = "update_cache.json"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the update cache.
        
        Args:
            cache_dir: Directory to store cache file. Defaults to CONFIG_DIR.
        """
        self._cache_dir = cache_dir or CONFIG_DIR
        self._cache_file = self._cache_dir / self.CACHE_FILENAME
    
    @property
    def cache_file(self) -> Path:
        """Get the cache file path."""
        return self._cache_file
    
    def get_cached_version(self) -> Optional[CachedVersionInfo]:
        """
        Get cached version if valid and not expired.
        
        Returns:
            CachedVersionInfo if cache exists and is valid, None otherwise.
        """
        if not self._cache_file.exists():
            return None
        
        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            if 'latest_version' not in data or 'checked_at' not in data:
                return None
            
            cached = CachedVersionInfo(
                latest_version=data['latest_version'],
                checked_at=data['checked_at']
            )
            
            # Check if cache is still valid
            if not self.is_cache_valid(cached):
                return None
            
            return cached
            
        except (json.JSONDecodeError, TypeError, KeyError, ValueError):
            # Cache is corrupted or invalid
            return None
    
    def save_version(self, version: str) -> None:
        """
        Save version info to cache with current timestamp.
        
        Args:
            version: The latest version string to cache.
        """
        # Ensure cache directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            'latest_version': version,
            'checked_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except (OSError, IOError):
            # Silently fail if we can't write cache
            pass
    
    def is_cache_valid(self, cached: CachedVersionInfo) -> bool:
        """
        Check if cache is within TTL.
        
        Args:
            cached: The cached version info to check.
            
        Returns:
            True if cache is within 24 hours, False otherwise.
        """
        try:
            # Parse the ISO format timestamp
            checked_at = datetime.fromisoformat(cached.checked_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            # Calculate age in hours
            age_hours = (now - checked_at).total_seconds() / 3600
            
            return age_hours < self.CACHE_TTL_HOURS
            
        except (ValueError, TypeError):
            # Invalid timestamp format
            return False
    
    def clear_cache(self) -> None:
        """Remove cached version info."""
        try:
            if self._cache_file.exists():
                self._cache_file.unlink()
        except (OSError, IOError):
            # Silently fail if we can't delete cache
            pass
