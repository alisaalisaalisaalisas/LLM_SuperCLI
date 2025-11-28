"""
Qwen Code provider with OAuth authentication.
Uses Qwen's OAuth for free tier access via chat.qwen.ai.
Based on KiloCode implementation.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urlencode

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


# Qwen OAuth Configuration
QWEN_OAUTH_BASE_URL = "https://chat.qwen.ai"
QWEN_OAUTH_TOKEN_ENDPOINT = f"{QWEN_OAUTH_BASE_URL}/api/v1/oauth2/token"
QWEN_OAUTH_CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"

# Default API endpoint
QWEN_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Qwen models (matching Qwen Code CLI)
QWEN_MODELS = [
    "coder-model",  # Latest Qwen Coder model (qwen3-coder-plus)
    "vision-model",  # Latest Qwen Vision model (qwen3-vl-plus)
]

QWEN_DEFAULT_MODEL = "coder-model"


class QwenProvider(LLMProvider):
    """
    Qwen provider with OAuth support.
    
    Reads OAuth credentials from ~/.qwen/oauth_creds.json
    Uses the OpenAI-compatible API at dashscope.aliyuncs.com.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Initialize Qwen provider."""
        config = self._default_config()
        if api_key:
            config.api_key = api_key
        super().__init__(config)
        
        if model:
            self._model = model
        
        self._credentials: Optional[dict] = None
        self._refresh_promise: Optional[Any] = None
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="Qwen",
            base_url=QWEN_DEFAULT_BASE_URL,
            default_model=QWEN_DEFAULT_MODEL,
            available_models=QWEN_MODELS,
            max_tokens=128_000,  # 128K tokens for coder-model
            supports_streaming=True,
            supports_functions=True,
            rate_limit_rpm=60,  # Free tier: 60 requests/minute
            cost_per_1k_input=0.0,  # Free tier via OAuth
            cost_per_1k_output=0.0,  # Free tier via OAuth
        )
    
    def _get_credentials_path(self) -> Path:
        """Get path to credentials file."""
        return Path.home() / ".qwen" / "oauth_creds.json"
    
    async def _load_credentials(self) -> dict:
        """Load OAuth credentials from file."""
        cred_path = self._get_credentials_path()
        
        if not cred_path.exists():
            raise ValueError(
                "Qwen OAuth credentials not found.\n"
                "Please login with: /login qwen\n"
                "Or copy oauth_creds.json to ~/.qwen/"
            )
        
        try:
            with open(cred_path, 'r') as f:
                self._credentials = json.load(f)
            return self._credentials
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load Qwen credentials: {e}")
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid."""
        if not self._credentials:
            return False
        
        expiry = self._credentials.get("expiry_date", 0)
        # 30 second buffer
        return time.time() * 1000 < expiry - 30000
    
    async def _refresh_access_token(self) -> dict:
        """Refresh the OAuth access token."""
        if not self._credentials or not self._credentials.get("refresh_token"):
            raise ValueError("No refresh token available")
        
        body_data = {
            "grant_type": "refresh_token",
            "refresh_token": self._credentials["refresh_token"],
            "client_id": QWEN_OAUTH_CLIENT_ID
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                QWEN_OAUTH_TOKEN_ENDPOINT,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                },
                content=urlencode(body_data),
                timeout=30.0
            )
            
            if not response.is_success:
                raise ValueError(f"Token refresh failed: {response.status_code} {response.text}")
            
            token_data = response.json()
            
            if token_data.get("error"):
                raise ValueError(f"Token refresh failed: {token_data['error']}")
            
            # Update credentials
            self._credentials["access_token"] = token_data["access_token"]
            self._credentials["token_type"] = token_data.get("token_type", "Bearer")
            if token_data.get("refresh_token"):
                self._credentials["refresh_token"] = token_data["refresh_token"]
            self._credentials["expiry_date"] = int(time.time() * 1000 + token_data.get("expires_in", 3600) * 1000)
            
            # Save to file
            cred_path = self._get_credentials_path()
            try:
                cred_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cred_path, 'w') as f:
                    json.dump(self._credentials, f, indent=2)
            except IOError as e:
                print(f"[Qwen] Failed to save credentials: {e}")
            
            return self._credentials
    
    async def _ensure_authenticated(self) -> str:
        """Ensure we have a valid OAuth access token."""
        # OAuth-only authentication (like Qwen Code CLI)
        if not self._credentials:
            await self._load_credentials()
        
        if not self._is_token_valid():
            await self._refresh_access_token()
        
        return self._credentials["access_token"]
    
    def _get_base_url(self) -> str:
        """Get the API base URL."""
        if not self._credentials:
            return QWEN_DEFAULT_BASE_URL
        
        base_url = self._credentials.get("resource_url", QWEN_DEFAULT_BASE_URL)
        
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = f"https://{base_url}"
        
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        
        return base_url
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to Qwen."""
        access_token = await self._ensure_authenticated()
        base_url = self._get_base_url()
        
        model = model or self._model
        temperature = temperature if temperature is not None else 0
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            **kwargs
        }
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=120.0
            )
            
            # Retry on 401
            if response.status_code == 401:
                await self._refresh_access_token()
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._credentials['access_token']}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=120.0
                )
            
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        message = data["choices"][0]["message"]
        content = message.get("content") or ""
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        return LLMResponse(
            content=content,
            model=data.get("model", model),
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=0.0,
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            latency_ms=latency_ms,
            raw_response=data
        )
    
    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[StreamChunk, None]:
        """Send a streaming chat completion request to Qwen."""
        access_token = await self._ensure_authenticated()
        base_url = self._get_base_url()
        
        model = model or self._model
        temperature = temperature if temperature is not None else 0
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=180.0
            ) as response:
                response.raise_for_status()
                
                full_content = ""
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        if "choices" in data and data["choices"]:
                            choice = data["choices"][0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                # Handle incremental vs full content
                                new_text = content
                                if new_text.startswith(full_content):
                                    new_text = new_text[len(full_content):]
                                full_content = content
                                
                                if new_text:
                                    # Check for thinking blocks
                                    if "<think>" in new_text or "</think>" in new_text:
                                        # Parse thinking blocks
                                        import re
                                        parts = re.split(r'</?think>', new_text)
                                        for i, part in enumerate(parts):
                                            if part:
                                                yield StreamChunk(
                                                    content=part,
                                                    finish_reason=choice.get("finish_reason"),
                                                    model=data.get("model", model)
                                                )
                                    else:
                                        yield StreamChunk(
                                            content=new_text,
                                            finish_reason=choice.get("finish_reason"),
                                            model=data.get("model", model)
                                        )
                            
                            # Handle reasoning_content
                            if delta.get("reasoning_content"):
                                yield StreamChunk(
                                    content=delta["reasoning_content"],
                                    finish_reason=choice.get("finish_reason"),
                                    model=data.get("model", model)
                                )
                    except json.JSONDecodeError:
                        continue
    
    async def list_models(self) -> list[str]:
        """List available Qwen models."""
        return QWEN_MODELS
