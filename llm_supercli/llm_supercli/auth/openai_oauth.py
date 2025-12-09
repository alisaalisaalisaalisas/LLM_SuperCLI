"""
OpenAI OAuth PKCE Flow implementation for llm_supercli.
Uses OpenAI's OAuth for ChatGPT Plus/Pro subscription access to Codex backend.
Based on opencode-openai-codex-auth plugin.
"""
import asyncio
import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Optional
from urllib.parse import urlencode, parse_qs, urlparse

import httpx

from .session_manager import AuthSession
from ..constants import OAUTH_TIMEOUT_SECONDS


# OpenAI OAuth Configuration (from Codex CLI)
OPENAI_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OPENAI_AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"
OPENAI_REDIRECT_URI = "http://localhost:1455/auth/callback"
OPENAI_SCOPE = "openid profile email offline_access"
OPENAI_CALLBACK_PORT = 1455


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge."""
    # Generate 32 bytes of random data for verifier
    verifier_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b'=').decode('ascii')
    
    # Create S256 challenge
    challenge_bytes = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=').decode('ascii')
    
    return verifier, challenge


def generate_state() -> str:
    """Generate random state value for OAuth."""
    return secrets.token_hex(16)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""
    
    def log_message(self, format, *args):
        """Suppress HTTP server logging."""
        pass
    
    def do_GET(self):
        """Handle OAuth callback GET request."""
        parsed = urlparse(self.path)
        
        if parsed.path == "/auth/callback":
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            
            if code and state:
                self.server.auth_code = code
                self.server.auth_state = state
                
                # Success response
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                response = """
                <!DOCTYPE html>
                <html>
                <head><title>Login Successful</title></head>
                <body style="font-family: system-ui; text-align: center; padding: 50px; background: #1a1a1a; color: #fff;">
                    <h1>✓ Login Successful</h1>
                    <p>You can close this window and return to LLM SuperCLI.</p>
                </body>
                </html>
                """
                self.wfile.write(response.encode())
            else:
                # Error response
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                error = params.get("error", ["Unknown error"])[0]
                response = f"""
                <!DOCTYPE html>
                <html>
                <head><title>Login Failed</title></head>
                <body style="font-family: system-ui; text-align: center; padding: 50px; background: #1a1a1a; color: #fff;">
                    <h1>✗ Login Failed</h1>
                    <p>Error: {error}</p>
                </body>
                </html>
                """
                self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()


class OpenAIOAuth:
    """
    OpenAI OAuth 2.0 PKCE Flow implementation.
    
    Uses the same OAuth flow as OpenAI's Codex CLI.
    """
    
    CREDENTIALS_DIR = Path.home() / ".openai_codex"
    CREDENTIALS_FILE = CREDENTIALS_DIR / "oauth_creds.json"
    
    def __init__(self) -> None:
        """Initialize OpenAI OAuth handler."""
        self.client_id = OPENAI_CLIENT_ID
    
    def is_authenticated(self) -> bool:
        """Check if user is already authenticated with valid/refreshable credentials."""
        if not self.CREDENTIALS_FILE.exists():
            return False
        
        try:
            with open(self.CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
                if not creds.get("access_token"):
                    return False
                
                expires_at = creds.get("expires_at", 0)
                # Check if token is valid or we have refresh token
                if expires_at > time.time():
                    return True
                
                # Token expired - check if we can refresh
                if creds.get("refresh_token"):
                    return True
        except (json.JSONDecodeError, IOError):
            pass
        
        return False
    
    def _start_callback_server(self, expected_state: str) -> tuple[HTTPServer, Thread]:
        """Start local HTTP server for OAuth callback."""
        server = HTTPServer(("localhost", OPENAI_CALLBACK_PORT), OAuthCallbackHandler)
        server.auth_code = None
        server.auth_state = None
        server.expected_state = expected_state
        
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()
        
        return server, thread
    
    def _build_authorization_url(self, verifier: str, challenge: str, state: str) -> str:
        """Build the OAuth authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": OPENAI_REDIRECT_URI,
            "scope": OPENAI_SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
            "originator": "codex_cli_rs",
        }
        return f"{OPENAI_AUTHORIZE_URL}?{urlencode(params)}"
    
    async def _exchange_code_for_tokens(self, code: str, verifier: str) -> Optional[dict]:
        """Exchange authorization code for access/refresh tokens."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    OPENAI_TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "code": code,
                        "code_verifier": verifier,
                        "redirect_uri": OPENAI_REDIRECT_URI,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"[OpenAI] Token exchange failed: {response.status_code} {response.text}")
                    return None
                
                data = response.json()
                
                if not data.get("access_token") or not data.get("refresh_token"):
                    print(f"[OpenAI] Invalid token response: missing fields")
                    return None
                
                return data
            except Exception as e:
                print(f"[OpenAI] Token exchange error: {e}")
                return None
    
    async def _save_credentials(self, token_data: dict) -> None:
        """Save credentials to file."""
        self.CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        
        expires_in = token_data.get("expires_in", 3600)
        
        creds = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_at": time.time() + expires_in,
            "expires_in": expires_in,
        }
        
        with open(self.CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        
        # Set restrictive permissions
        try:
            self.CREDENTIALS_FILE.chmod(0o600)
        except Exception:
            pass
    
    async def refresh_token(self, refresh_token: str) -> Optional[AuthSession]:
        """Refresh an expired access token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    OPENAI_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.client_id,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"[OpenAI] Token refresh failed: {response.status_code}")
                    return None
                
                data = response.json()
                
                if not data.get("access_token"):
                    return None
                
                await self._save_credentials(data)
                
                expires_at = time.time() + data.get("expires_in", 3600)
                
                return AuthSession(
                    provider="openai",
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    token_type=data.get("token_type", "Bearer"),
                    expires_at=expires_at,
                )
            except Exception as e:
                print(f"[OpenAI] Token refresh error: {e}")
                return None
    
    async def login(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """Perform complete OAuth login flow."""
        print("\n[OpenAI] Starting OAuth login...")
        
        # Generate PKCE values
        verifier, challenge = generate_pkce()
        state = generate_state()
        
        # Build authorization URL
        auth_url = self._build_authorization_url(verifier, challenge, state)
        
        print(f"\n  Please visit: {auth_url[:80]}...")
        print(f"  Waiting for browser authorization...\n")
        
        # Start callback server
        try:
            server, thread = self._start_callback_server(state)
        except OSError as e:
            print(f"[OpenAI] Error: Could not start callback server on port {OPENAI_CALLBACK_PORT}")
            print(f"  Make sure no other application is using this port (e.g., Codex CLI).")
            return None
        
        # Open browser
        try:
            webbrowser.open(auth_url)
        except Exception:
            print(f"  Could not open browser. Please visit the URL manually.")
        
        if on_code_received:
            on_code_received(None, auth_url)
        
        # Wait for callback
        start_time = time.time()
        while time.time() - start_time < OAUTH_TIMEOUT_SECONDS:
            if server.auth_code and server.auth_state:
                break
            await asyncio.sleep(0.5)
        
        # Close server
        try:
            server.server_close()
        except Exception:
            pass
        
        # Validate state
        if server.auth_state != state:
            print("[OpenAI] Error: State mismatch - possible CSRF attack")
            return None
        
        if not server.auth_code:
            print("[OpenAI] Error: No authorization code received")
            return None
        
        print("  Authorization received, exchanging for tokens...")
        
        # Exchange code for tokens
        token_data = await self._exchange_code_for_tokens(server.auth_code, verifier)
        
        if not token_data:
            return None
        
        await self._save_credentials(token_data)
        
        expires_at = time.time() + token_data.get("expires_in", 3600)
        
        print("[OpenAI] Login successful!")
        
        return AuthSession(
            provider="openai",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=expires_at,
        )
    
    def login_sync(self, on_code_received: Optional[callable] = None) -> Optional[AuthSession]:
        """Synchronous wrapper for login."""
        return asyncio.run(self.login(on_code_received))
