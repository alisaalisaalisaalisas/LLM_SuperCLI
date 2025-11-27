"""
Session management for authentication in llm_supercli.
Handles storing and retrieving authentication tokens securely.
"""
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from ..constants import AUTH_CACHE_FILE, CONFIG_DIR


@dataclass
class AuthSession:
    """Represents an authenticated user session."""
    provider: str  # 'google' or 'github'
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[float] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: float = 0
    
    def __post_init__(self) -> None:
        if self.created_at == 0:
            self.created_at = time.time()
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at
    
    @property
    def time_until_expiry(self) -> Optional[float]:
        """Get seconds until token expires."""
        if self.expires_at is None:
            return None
        return max(0, self.expires_at - time.time())
    
    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AuthSession':
        """Create session from dictionary."""
        return cls(**data)


class SessionManager:
    """
    Manages authentication sessions with secure storage.
    
    Supports multiple providers and handles token refresh.
    """
    
    _instance: Optional['SessionManager'] = None
    
    def __new__(cls) -> 'SessionManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._sessions: dict[str, AuthSession] = {}
        self._cache_file = AUTH_CACHE_FILE
        self._ensure_config_dir()
        self._load_sessions()
    
    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_sessions(self) -> None:
        """Load sessions from cache file."""
        if not self._cache_file.exists():
            return
        
        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for provider, session_data in data.items():
                self._sessions[provider] = AuthSession.from_dict(session_data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to load auth cache: {e}")
    
    def _save_sessions(self) -> None:
        """Save sessions to cache file."""
        data = {
            provider: session.to_dict()
            for provider, session in self._sessions.items()
        }
        
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache_file.touch(mode=0o600, exist_ok=True)
        
        with open(self._cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def store_session(self, session: AuthSession) -> None:
        """
        Store an authentication session.
        
        Args:
            session: AuthSession to store
        """
        self._sessions[session.provider] = session
        self._save_sessions()
    
    def get_session(self, provider: str) -> Optional[AuthSession]:
        """
        Get a session for a provider.
        
        Args:
            provider: Provider name ('google' or 'github')
            
        Returns:
            AuthSession or None if not found/expired
        """
        session = self._sessions.get(provider)
        if session and not session.is_expired:
            return session
        return None
    
    def get_active_session(self) -> Optional[AuthSession]:
        """
        Get the most recent active session.
        
        Returns:
            Most recent non-expired AuthSession or None
        """
        active_sessions = [
            s for s in self._sessions.values()
            if not s.is_expired
        ]
        
        if not active_sessions:
            return None
        
        return max(active_sessions, key=lambda s: s.created_at)
    
    def remove_session(self, provider: str) -> bool:
        """
        Remove a session.
        
        Args:
            provider: Provider name
            
        Returns:
            True if session was removed
        """
        if provider in self._sessions:
            del self._sessions[provider]
            self._save_sessions()
            return True
        return False
    
    def clear_all_sessions(self) -> None:
        """Remove all stored sessions."""
        self._sessions.clear()
        if self._cache_file.exists():
            self._cache_file.unlink()
    
    def is_authenticated(self, provider: Optional[str] = None) -> bool:
        """
        Check if user is authenticated.
        
        Args:
            provider: Optional specific provider to check
            
        Returns:
            True if authenticated
        """
        if provider:
            session = self.get_session(provider)
            return session is not None
        return self.get_active_session() is not None
    
    def get_user_info(self) -> Optional[dict]:
        """
        Get current user information.
        
        Returns:
            Dict with user info or None
        """
        session = self.get_active_session()
        if not session:
            return None
        
        return {
            "provider": session.provider,
            "user_id": session.user_id,
            "email": session.user_email,
            "name": session.user_name,
            "avatar": session.avatar_url,
        }
    
    def get_access_token(self, provider: Optional[str] = None) -> Optional[str]:
        """
        Get access token for API calls.
        
        Args:
            provider: Optional specific provider
            
        Returns:
            Access token string or None
        """
        if provider:
            session = self.get_session(provider)
        else:
            session = self.get_active_session()
        
        return session.access_token if session else None
    
    def refresh_session(self, provider: str) -> bool:
        """
        Attempt to refresh an expired session.
        
        Args:
            provider: Provider name
            
        Returns:
            True if refresh was successful
        """
        session = self._sessions.get(provider)
        if not session or not session.refresh_token:
            return False
        
        # Import the appropriate OAuth handler
        if provider == "google":
            from .google_oauth import GoogleOAuth
            oauth = GoogleOAuth()
        elif provider == "github":
            from .github_oauth import GitHubOAuth
            oauth = GitHubOAuth()
        else:
            return False
        
        try:
            new_session = oauth.refresh_token(session.refresh_token)
            if new_session:
                self.store_session(new_session)
                return True
        except Exception:
            pass
        
        return False
    
    @property
    def all_sessions(self) -> dict[str, AuthSession]:
        """Get all stored sessions."""
        return self._sessions.copy()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return SessionManager()
