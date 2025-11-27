"""
Qwen (Alibaba Cloud DashScope) OAuth/API Key management for llm_supercli.
Supports API key storage and Alibaba Cloud OAuth.
"""
import asyncio
import json
import os
import time
import webbrowser
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx

from .session_manager import AuthSession


class QwenOAuth:
    """
    Qwen (Alibaba Cloud DashScope) authentication handler.
    
    Supports:
    - API key storage in ~/.qwen/oauth_creds.json
    - Alibaba Cloud OAuth (device flow)
    """
    
    # Alibaba Cloud OAuth endpoints
    ALIYUN_OAUTH_URL = "https://signin.aliyun.com/oauth2/v1"
    DASHSCOPE_API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    
    # For API key login, we use DashScope console
    DASHSCOPE_CONSOLE_URL = "https://dashscope.console.aliyun.com/apiKey"
    
    CREDS_DIR = Path.home() / ".qwen"
    CREDS_FILE = CREDS_DIR / "oauth_creds.json"
    SETTINGS_FILE = CREDS_DIR / "settings.json"
    
    def __init__(self, region: str = "intl") -> None:
        """
        Initialize Qwen OAuth handler.
        
        Args:
            region: "intl" for international, "cn" for China
        """
        self.region = region
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Ensure credentials directory exists."""
        self.CREDS_DIR.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self, api_key: str, user_info: Optional[dict] = None):
        """Save API key/OAuth credentials to file."""
        expiry_date = int((time.time() + 365 * 24 * 3600) * 1000)  # 1 year for API key
        
        creds = {
            "access_token": api_key,
            "refresh_token": None,
            "token_type": "Bearer",
            "expiry_date": expiry_date,
            "region": self.region,
        }
        
        with open(self.CREDS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        
        # Save user settings
        if user_info:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(user_info, f, indent=2)
        
        print(f"[Qwen] Credentials saved to {self.CREDS_FILE}")
    
    def load_credentials(self) -> Optional[dict]:
        """Load credentials from file."""
        if not self.CREDS_FILE.exists():
            return None
        
        try:
            with open(self.CREDS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    async def verify_api_key(self, api_key: str) -> bool:
        """Verify API key by making a test request."""
        base_url = (
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            if self.region == "intl"
            else "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                return response.status_code == 200
            except Exception:
                # Even if models endpoint fails, the key might still work
                # Try a minimal chat request
                try:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "qwen-turbo",
                            "messages": [{"role": "user", "content": "hi"}],
                            "max_tokens": 1
                        },
                        timeout=10.0
                    )
                    return response.status_code in (200, 400)  # 400 means auth worked but request bad
                except Exception:
                    return False
    
    async def login(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """
        Perform login flow - prompts for API key.
        
        For Qwen/DashScope, we use API key authentication as primary method.
        """
        from rich.console import Console
        from rich.prompt import Prompt
        
        console = Console()
        
        console.print("\n[bold cyan]Qwen (DashScope) Login[/]")
        console.print("[dim]DashScope uses API key authentication[/]\n")
        
        # Check for existing credentials
        existing = self.load_credentials()
        if existing and existing.get("access_token"):
            console.print("[yellow]Existing credentials found.[/]")
            replace = Prompt.ask("Replace existing credentials?", choices=["y", "n"], default="n")
            if replace.lower() != "y":
                return AuthSession(
                    provider="qwen",
                    access_token=existing["access_token"],
                    refresh_token=None,
                    token_type="Bearer",
                    expires_at=existing.get("expiry_date"),
                    user_id=None,
                    user_email=None,
                    user_name="Qwen User",
                    avatar_url=None,
                )
        
        console.print("[bold]To get your API key:[/]")
        console.print(f"1. Visit: [link={self.DASHSCOPE_CONSOLE_URL}]{self.DASHSCOPE_CONSOLE_URL}[/link]")
        console.print("2. Create or copy your API key")
        console.print("3. Paste it below\n")
        
        # Ask if user wants to open browser
        open_browser = Prompt.ask("Open DashScope console in browser?", choices=["y", "n"], default="y")
        if open_browser.lower() == "y":
            webbrowser.open(self.DASHSCOPE_CONSOLE_URL)
        
        console.print()
        api_key = Prompt.ask("[bold]Enter your DashScope API key[/]", password=True)
        
        if not api_key or len(api_key) < 10:
            console.print("[red]Invalid API key[/]")
            return None
        
        # Verify the API key
        console.print("[dim]Verifying API key...[/]")
        is_valid = await self.verify_api_key(api_key)
        
        if not is_valid:
            console.print("[yellow]Warning: Could not verify API key, but saving anyway.[/]")
            console.print("[dim]The key may still work - verification endpoints vary by region.[/]")
        
        # Save credentials
        self.save_credentials(api_key)
        
        console.print("[green]Qwen credentials saved successfully![/]")
        
        return AuthSession(
            provider="qwen",
            access_token=api_key,
            refresh_token=None,
            token_type="Bearer",
            expires_at=time.time() + 365 * 24 * 3600,
            user_id=None,
            user_email=None,
            user_name="Qwen User",
            avatar_url=None,
        )
    
    def login_sync(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """Synchronous wrapper for login."""
        return asyncio.run(self.login(on_code_received))
    
    def is_authenticated(self) -> bool:
        """Check if valid credentials exist."""
        creds = self.load_credentials()
        if not creds:
            return False
        return creds.get("access_token") is not None
    
    def logout(self) -> bool:
        """Remove stored credentials."""
        try:
            if self.CREDS_FILE.exists():
                self.CREDS_FILE.unlink()
            if self.SETTINGS_FILE.exists():
                self.SETTINGS_FILE.unlink()
            return True
        except Exception:
            return False
