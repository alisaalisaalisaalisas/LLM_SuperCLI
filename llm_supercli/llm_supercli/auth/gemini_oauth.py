"""
Google Gemini OAuth Device Code Flow implementation for llm_supercli.
Uses Google OAuth with Gemini API scopes.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx

from .session_manager import AuthSession


@dataclass
class DeviceCodeResponse:
    """Response from device code request."""
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int


class GeminiOAuth:
    """
    Google OAuth 2.0 Device Code Flow for Gemini API.
    
    Uses Google's OAuth with generative AI scopes to access Gemini API.
    Credentials are stored in ~/.gemini/oauth_creds.json
    """
    
    DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    
    # Google OAuth client credentials - load from environment or use defaults
    # Set GEMINI_OAUTH_CLIENT_ID and GEMINI_OAUTH_CLIENT_SECRET env vars
    CLIENT_ID = os.getenv("GEMINI_OAUTH_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("GEMINI_OAUTH_CLIENT_SECRET", "")
    
    SCOPES = [
        "openid",
        "email", 
        "profile",
        "https://www.googleapis.com/auth/generative-language.tuning",
        "https://www.googleapis.com/auth/generative-language.retriever",
        "https://www.googleapis.com/auth/cloud-platform",
    ]
    
    CREDS_DIR = Path.home() / ".gemini"
    CREDS_FILE = CREDS_DIR / "oauth_creds.json"
    SETTINGS_FILE = CREDS_DIR / "settings.json"
    
    def __init__(self) -> None:
        self.client_id = self.CLIENT_ID
        self.client_secret = self.CLIENT_SECRET
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Ensure credentials directory exists."""
        self.CREDS_DIR.mkdir(parents=True, exist_ok=True)
    
    async def request_device_code(self) -> DeviceCodeResponse:
        """Request a device code for user authorization."""
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
        timeout: int = 300
    ) -> Optional[dict]:
        """Poll for access token after user authorizes."""
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
        """Fetch user information with access token."""
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
    
    def save_credentials(self, token_data: dict, user_info: Optional[dict] = None):
        """Save OAuth credentials to file."""
        expiry_date = None
        if "expires_in" in token_data:
            expiry_date = int((time.time() + token_data["expires_in"]) * 1000)
        
        creds = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expiry_date": expiry_date,
            "scope": token_data.get("scope", ""),
        }
        
        with open(self.CREDS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        
        # Save user settings
        if user_info:
            settings = {
                "user_email": user_info.get("email"),
                "user_name": user_info.get("name"),
            }
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
        
        print(f"[Gemini] Credentials saved to {self.CREDS_FILE}")
    
    def load_credentials(self) -> Optional[dict]:
        """Load OAuth credentials from file."""
        if not self.CREDS_FILE.exists():
            return None
        
        try:
            with open(self.CREDS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh an expired access token."""
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
                
                # Preserve refresh token if not returned
                if "refresh_token" not in data:
                    data["refresh_token"] = refresh_token
                
                return data
            except httpx.HTTPError as e:
                print(f"[Gemini] Token refresh failed: {e}")
                return None
    
    async def login(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """Perform complete OAuth login flow."""
        from rich.console import Console
        console = Console()
        
        console.print("\n[bold cyan]Gemini OAuth Login[/]")
        console.print("[dim]Starting device authorization flow...[/]\n")
        
        device_response = await self.request_device_code()
        
        console.print(f"[bold]1. Go to:[/] [link={device_response.verification_url}]{device_response.verification_url}[/link]")
        console.print(f"[bold]2. Enter code:[/] [bold yellow]{device_response.user_code}[/]")
        console.print("\n[dim]Waiting for authorization...[/]")
        
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
            console.print("[red]Authorization failed or timed out[/]")
            return None
        
        user_info = await self.get_user_info(token_data["access_token"])
        
        # Save credentials for Gemini provider
        self.save_credentials(token_data, user_info)
        
        expires_at = None
        if "expires_in" in token_data:
            expires_at = time.time() + token_data["expires_in"]
        
        console.print(f"[green]Successfully logged in as {user_info.get('email', 'user')}[/]")
        
        return AuthSession(
            provider="gemini",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=expires_at,
            user_id=user_info.get("id") if user_info else None,
            user_email=user_info.get("email") if user_info else None,
            user_name=user_info.get("name") if user_info else None,
            avatar_url=user_info.get("picture") if user_info else None,
        )
    
    def login_sync(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """Synchronous wrapper for login."""
        return asyncio.run(self.login(on_code_received))
    
    def is_authenticated(self) -> bool:
        """Check if valid credentials exist."""
        creds = self.load_credentials()
        if not creds:
            return False
        
        # Check if token is expired
        expiry = creds.get("expiry_date", 0)
        if expiry:
            current_time = int(time.time() * 1000)
            if current_time > expiry:
                # Token expired, check if we can refresh
                return creds.get("refresh_token") is not None
        
        return creds.get("access_token") is not None
