"""
Google OAuth Device Code Flow implementation for llm_supercli.
"""
import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx

from .session_manager import AuthSession
from ..constants import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_TIMEOUT_SECONDS


@dataclass
class DeviceCodeResponse:
    """Response from device code request."""
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int


class GoogleOAuth:
    """
    Google OAuth 2.0 Device Code Flow implementation.
    
    This flow is ideal for CLI applications where a browser redirect isn't practical.
    The user is shown a code to enter at a Google URL to authorize the application.
    """
    
    DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    
    SCOPES = [
        "openid",
        "email",
        "profile",
    ]
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> None:
        """
        Initialize Google OAuth handler.
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
        """
        self.client_id = client_id or GOOGLE_CLIENT_ID
        self.client_secret = client_secret or GOOGLE_CLIENT_SECRET
    
    async def request_device_code(self) -> DeviceCodeResponse:
        """
        Request a device code for user authorization.
        
        Returns:
            DeviceCodeResponse with codes and URLs
            
        Raises:
            httpx.HTTPError: On request failure
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.DEVICE_CODE_URL,
                data={
                    "client_id": self.client_id,
                    "scope": " ".join(self.SCOPES),
                }
            )
            response.raise_for_status()
            data = response.json()
        
        return DeviceCodeResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_url=data["verification_uri"],
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
                        data={
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "device_code": device_code,
                            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        }
                    )
                    
                    data = response.json()
                    
                    if response.status_code == 200:
                        return data
                    
                    error = data.get("error")
                    
                    if error == "authorization_pending":
                        await asyncio.sleep(interval)
                        continue
                    elif error == "slow_down":
                        interval += 1
                        await asyncio.sleep(interval)
                        continue
                    elif error in ("access_denied", "expired_token"):
                        return None
                    else:
                        return None
                        
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
                    self.USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
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
                device_response.verification_url
            )
        
        token_data = await self.poll_for_token(
            device_response.device_code,
            device_response.interval
        )
        
        if not token_data:
            return None
        
        user_info = await self.get_user_info(token_data["access_token"])
        
        expires_at = None
        if "expires_in" in token_data:
            expires_at = time.time() + token_data["expires_in"]
        
        return AuthSession(
            provider="google",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=expires_at,
            user_id=user_info.get("id") if user_info else None,
            user_email=user_info.get("email") if user_info else None,
            user_name=user_info.get("name") if user_info else None,
            avatar_url=user_info.get("picture") if user_info else None,
        )
    
    async def refresh_token(self, refresh_token: str) -> Optional[AuthSession]:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token from previous auth
            
        Returns:
            New AuthSession or None
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                user_info = await self.get_user_info(data["access_token"])
                
                expires_at = None
                if "expires_in" in data:
                    expires_at = time.time() + data["expires_in"]
                
                return AuthSession(
                    provider="google",
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    token_type=data.get("token_type", "Bearer"),
                    expires_at=expires_at,
                    user_id=user_info.get("id") if user_info else None,
                    user_email=user_info.get("email") if user_info else None,
                    user_name=user_info.get("name") if user_info else None,
                    avatar_url=user_info.get("picture") if user_info else None,
                )
            except httpx.HTTPError:
                return None
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if successful
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.REVOKE_URL,
                    params={"token": token}
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
