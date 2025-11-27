"""
GitHub OAuth Device Code Flow implementation for llm_supercli.
"""
import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx

from .session_manager import AuthSession
from ..constants import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, OAUTH_TIMEOUT_SECONDS


@dataclass
class GitHubDeviceCodeResponse:
    """Response from GitHub device code request."""
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class GitHubOAuth:
    """
    GitHub OAuth 2.0 Device Code Flow implementation.
    
    This flow allows CLI applications to authenticate users through GitHub
    without requiring a local web server for redirects.
    """
    
    DEVICE_CODE_URL = "https://github.com/login/device/code"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"
    USER_EMAILS_URL = "https://api.github.com/user/emails"
    
    SCOPES = [
        "read:user",
        "user:email",
    ]
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> None:
        """
        Initialize GitHub OAuth handler.
        
        Args:
            client_id: GitHub OAuth client ID
            client_secret: GitHub OAuth client secret (optional for device flow)
        """
        self.client_id = client_id or GITHUB_CLIENT_ID
        self.client_secret = client_secret or GITHUB_CLIENT_SECRET
    
    async def request_device_code(self) -> GitHubDeviceCodeResponse:
        """
        Request a device code for user authorization.
        
        Returns:
            GitHubDeviceCodeResponse with codes and URLs
            
        Raises:
            httpx.HTTPError: On request failure
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.DEVICE_CODE_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "scope": " ".join(self.SCOPES),
                }
            )
            response.raise_for_status()
            data = response.json()
        
        return GitHubDeviceCodeResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data["verification_uri"],
            expires_in=data["expires_in"],
            interval=data.get("interval", 5)
        )
    
    async def poll_for_token(
        self,
        device_code: str,
        interval: int = 5,
        timeout: int = OAUTH_TIMEOUT_SECONDS
    ) -> Optional[dict]:
        """
        Poll for access token after user authorizes.
        
        Args:
            device_code: Device code from initial request
            interval: Polling interval in seconds
            timeout: Maximum time to wait
            
        Returns:
            Token response dict or None if timeout/denied
        """
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.post(
                        self.TOKEN_URL,
                        headers={"Accept": "application/json"},
                        data={
                            "client_id": self.client_id,
                            "device_code": device_code,
                            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        }
                    )
                    
                    data = response.json()
                    
                    if "access_token" in data:
                        return data
                    
                    error = data.get("error")
                    
                    if error == "authorization_pending":
                        await asyncio.sleep(interval)
                        continue
                    elif error == "slow_down":
                        interval += 5
                        await asyncio.sleep(interval)
                        continue
                    elif error in ("access_denied", "expired_token"):
                        return None
                    else:
                        await asyncio.sleep(interval)
                        
                except httpx.HTTPError:
                    await asyncio.sleep(interval)
        
        return None
    
    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """
        Fetch user information with access token.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User info dict or None
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.USER_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    }
                )
                response.raise_for_status()
                user_data = response.json()
                
                if not user_data.get("email"):
                    email_response = await client.get(
                        self.USER_EMAILS_URL,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/vnd.github.v3+json",
                        }
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        primary_email = next(
                            (e["email"] for e in emails if e.get("primary")),
                            emails[0]["email"] if emails else None
                        )
                        user_data["email"] = primary_email
                
                return user_data
            except httpx.HTTPError:
                return None
    
    async def login(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """
        Perform complete OAuth login flow.
        
        Args:
            on_code_received: Callback when user code is ready
            
        Returns:
            AuthSession on success, None on failure
        """
        device_response = await self.request_device_code()
        
        if on_code_received:
            on_code_received(
                device_response.user_code,
                device_response.verification_uri
            )
        
        token_data = await self.poll_for_token(
            device_response.device_code,
            device_response.interval
        )
        
        if not token_data:
            return None
        
        user_info = await self.get_user_info(token_data["access_token"])
        
        return AuthSession(
            provider="github",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=None,  # GitHub tokens don't expire by default
            user_id=str(user_info.get("id")) if user_info else None,
            user_email=user_info.get("email") if user_info else None,
            user_name=user_info.get("name") or user_info.get("login") if user_info else None,
            avatar_url=user_info.get("avatar_url") if user_info else None,
        )
    
    async def refresh_token(self, refresh_token: str) -> Optional[AuthSession]:
        """
        Refresh an access token (GitHub OAuth apps with refresh tokens).
        
        Args:
            refresh_token: Refresh token from previous auth
            
        Returns:
            New AuthSession or None
        """
        if not self.client_secret:
            return None
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if "access_token" not in data:
                    return None
                
                user_info = await self.get_user_info(data["access_token"])
                
                expires_at = None
                if "expires_in" in data:
                    expires_at = time.time() + data["expires_in"]
                
                return AuthSession(
                    provider="github",
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    token_type=data.get("token_type", "Bearer"),
                    expires_at=expires_at,
                    user_id=str(user_info.get("id")) if user_info else None,
                    user_email=user_info.get("email") if user_info else None,
                    user_name=user_info.get("name") or user_info.get("login") if user_info else None,
                    avatar_url=user_info.get("avatar_url") if user_info else None,
                )
            except httpx.HTTPError:
                return None
    
    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke a GitHub access token.
        
        Note: Requires client_secret for OAuth Apps.
        
        Args:
            access_token: Token to revoke
            
        Returns:
            True if successful
        """
        if not self.client_secret:
            return False
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"https://api.github.com/applications/{self.client_id}/token",
                    auth=(self.client_id, self.client_secret),
                    headers={"Accept": "application/vnd.github.v3+json"},
                    json={"access_token": access_token}
                )
                return response.status_code == 204
            except httpx.HTTPError:
                return False
    
    async def check_token(self, access_token: str) -> bool:
        """
        Check if a token is still valid.
        
        Args:
            access_token: Token to check
            
        Returns:
            True if token is valid
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.USER_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    }
                )
                return response.status_code == 200
            except httpx.HTTPError:
                return False
    
    def login_sync(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """
        Synchronous wrapper for login.
        
        Args:
            on_code_received: Callback when user code is ready
            
        Returns:
            AuthSession on success, None on failure
        """
        return asyncio.run(self.login(on_code_received))
