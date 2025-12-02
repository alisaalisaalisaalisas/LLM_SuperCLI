"""
Update checker module for checking npm registry for newer versions.
Handles version comparison and update checking with caching support.
"""
from dataclasses import dataclass
from typing import Optional

import httpx
from packaging import version as pkg_version

from .update_cache import UpdateCache


@dataclass
class UpdateResult:
    """Result of an update check operation."""
    update_available: bool
    current_version: str
    latest_version: Optional[str] = None
    error: Optional[str] = None


class UpdateChecker:
    """
    Handles version checking against npm registry.
    
    Checks the npm registry for the latest version of the package
    and compares it with the current version using semver rules.
    """
    
    PACKAGE_NAME: str = "llm-supercli"
    NPM_REGISTRY_URL: str = "https://registry.npmjs.org"
    CHECK_TIMEOUT: float = 3.0  # seconds
    
    def __init__(self, cache: UpdateCache):
        """
        Initialize the update checker.
        
        Args:
            cache: UpdateCache instance for caching version check results.
        """
        self.cache = cache
    
    async def check_for_update(
        self, 
        current_version: str, 
        bypass_cache: bool = False
    ) -> UpdateResult:
        """
        Check if a newer version is available.
        
        Args:
            current_version: The current version of the package.
            bypass_cache: If True, skip cache and fetch fresh from npm.
            
        Returns:
            UpdateResult with update availability information.
        """
        # Try to use cached version first (unless bypassing)
        if not bypass_cache:
            cached = self.cache.get_cached_version()
            if cached is not None:
                is_newer = self.compare_versions(current_version, cached.latest_version)
                return UpdateResult(
                    update_available=is_newer,
                    current_version=current_version,
                    latest_version=cached.latest_version
                )
        
        # Fetch latest version from npm
        latest_version = await self.fetch_latest_version()
        
        if latest_version is None:
            return UpdateResult(
                update_available=False,
                current_version=current_version,
                latest_version=None,
                error="Failed to fetch latest version from npm registry"
            )
        
        # Cache the result
        self.cache.save_version(latest_version)
        
        # Compare versions
        is_newer = self.compare_versions(current_version, latest_version)
        
        return UpdateResult(
            update_available=is_newer,
            current_version=current_version,
            latest_version=latest_version
        )
    
    async def fetch_latest_version(self) -> Optional[str]:
        """
        Fetch latest version from npm registry.
        
        Returns:
            The latest version string, or None if fetch failed.
        """
        url = f"{self.NPM_REGISTRY_URL}/{self.PACKAGE_NAME}/latest"
        
        try:
            async with httpx.AsyncClient(timeout=self.CHECK_TIMEOUT) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("version")
        except httpx.TimeoutException:
            # Timeout - return None without raising
            return None
        except httpx.HTTPStatusError:
            # HTTP error (4xx, 5xx) - return None without raising
            return None
        except httpx.RequestError:
            # Network error - return None without raising
            return None
        except (ValueError, KeyError, TypeError):
            # JSON parsing error or missing key - return None without raising
            return None

    def compare_versions(self, current: str, latest: str) -> bool:
        """
        Compare two version strings using semver rules.
        
        Args:
            current: The current version string.
            latest: The latest version string.
            
        Returns:
            True if latest > current, False otherwise.
        """
        try:
            current_ver = pkg_version.parse(current)
            latest_ver = pkg_version.parse(latest)
            return latest_ver > current_ver
        except (pkg_version.InvalidVersion, TypeError):
            # If version parsing fails, assume no update available
            return False
