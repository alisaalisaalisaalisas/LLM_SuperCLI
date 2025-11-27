"""
Qwen (Alibaba Cloud) LLM provider implementation for llm_supercli.
Uses OpenAI-compatible API with OAuth or API key authentication.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class QwenProvider(LLMProvider):
    """
    Qwen API provider using OpenAI-compatible protocol.
    
    Supports:
    - OAuth credentials from ~/.qwen/oauth_creds.json (qwen-cli style)
    - API key authentication (QWEN_API_KEY or DASHSCOPE_API_KEY env var)
    
    OAuth uses chat.qwen.ai endpoint (qwen-code compatible):
    - Free tier: 2,000 requests/day, 60 requests/minute
    - Automatic token refresh
    """
    
    # DashScope API endpoints (for API key auth)
    DASHSCOPE_INTL_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_CN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # Qwen Chat API endpoint (for OAuth - qwen-cli compatible)
    QWEN_CHAT_URL = "https://chat.qwenlm.ai/api"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        region: str = "intl",  # "intl" or "cn"
        **kwargs: Any
    ) -> None:
        config = self._default_config()
        if api_key:
            config.api_key = api_key
        if model:
            config.default_model = model
        
        # Set base URL based on region
        config.base_url = self.DASHSCOPE_INTL_URL if region == "intl" else self.DASHSCOPE_CN_URL
        
        super().__init__(config)
        
        if model:
            self._model = model
        
        self._region = region
        self._oauth_token = None
        self._oauth_refresh_token = None
        self._oauth_expiry = 0
        self._use_portal_api = False  # Use portal API for portal.qwen.ai OAuth
        self._load_oauth_if_needed()
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="Qwen",
            base_url=self.DASHSCOPE_INTL_URL,
            default_model="Qwen3 Coder Flash",
            available_models=[
                # Qwen3 Coder models (qwen-cli)
                "Qwen3 Coder Flash",
                "Qwen3 Coder Plus"
              
            ],
            max_tokens=8192,
            supports_streaming=True,
            supports_functions=True,
            rate_limit_rpm=60,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )
    
    def _load_oauth_if_needed(self):
        """Load OAuth credentials from file (qwen-cli compatible)."""
        qwen_dir = Path(os.path.expanduser("~/.qwen"))
        oauth_path = qwen_dir / "oauth_creds.json"
        
        if oauth_path.exists():
            try:
                with open(oauth_path, 'r') as f:
                    creds = json.load(f)
                
                self._oauth_token = creds.get('access_token')
                self._oauth_refresh_token = creds.get('refresh_token')
                self._oauth_expiry = creds.get('expiry_date', 0)
                
                # Check if this is qwen.ai OAuth (qwen-cli style)
                resource_url = creds.get('resource_url', '')
                if 'qwen.ai' in resource_url or 'portal.qwen' in resource_url:
                    self._use_portal_api = True
                    print("[Qwen] OAuth mode: chat.qwen.ai (qwen-cli compatible)")
                else:
                    self._use_portal_api = False
                
                # Check token expiry
                current_time = int(time.time() * 1000)
                if self._oauth_expiry:
                    expires_in = (self._oauth_expiry - current_time) / 1000
                    if expires_in < 0:
                        print(f"[Qwen] OAuth token expired. Run `/login qwen` to refresh.")
                        self._oauth_token = None
                    else:
                        print(f"[Qwen] OAuth valid ({int(expires_in)}s remaining)")
                
                if self._oauth_token:
                    return
            except Exception as e:
                print(f"[Qwen] Warning: Failed to load OAuth: {e}")

        # Fallback to API key
        if not self._api_key:
            self._api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
            if self._api_key:
                print("[Qwen] Using API key")
    
    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        
        if self._oauth_token:
            headers["Authorization"] = f"Bearer {self._oauth_token}"
            if self._use_portal_api:
                # Portal API may need additional headers
                headers["Origin"] = "https://chat.qwen.ai"
                headers["Referer"] = "https://chat.qwen.ai/"
        elif self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        
        return headers
    
    def _get_api_url(self) -> str:
        """Get the appropriate API URL (qwen-cli compatible)."""
        if self._use_portal_api and self._oauth_token:
            return self.QWEN_CHAT_URL
        return self._config.base_url
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to Qwen."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        # Build request payload (OpenAI-compatible format)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Handle additional parameters
        if "stream" in kwargs:
            payload["stream"] = kwargs["stream"]
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs:
            payload["tool_choice"] = kwargs["tool_choice"]
        
        start_time = time.perf_counter()
        api_url = self._get_api_url()
        
        async with httpx.AsyncClient() as client:
            url = f"{api_url}/chat/completions"
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=2000
            )
            
            # Handle non-JSON responses
            try:
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                # Debug: print response for troubleshooting
                print(f"[Qwen] API Error: {response.status_code}")
                print(f"[Qwen] URL: {url}")
                print(f"[Qwen] Response: {response.text[:500] if response.text else 'empty'}")
                raise
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Extract response content (OpenAI-compatible format)
        content = ""
        if "choices" in data and data["choices"]:
            choice = data["choices"][0]
            if "message" in choice:
                content = choice["message"].get("content", "")
        
        # Get token counts
        input_tokens = 0
        output_tokens = 0
        if "usage" in data:
            input_tokens = data["usage"].get("prompt_tokens", 0)
            output_tokens = data["usage"].get("completion_tokens", 0)
        
        return LLMResponse(
            content=content,
            model=model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=self.calculate_cost(input_tokens, output_tokens),
            finish_reason=data.get("choices", [{}])[0].get("finish_reason", "stop"),
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
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]
        if "tool_choice" in kwargs:
            payload["tool_choice"] = kwargs["tool_choice"]
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._config.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=2000
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # Skip "data: " prefix for SSE format
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    # Check for stream end marker
                    if line.strip() == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(line)
                        
                        if "choices" in data and data["choices"]:
                            choice = data["choices"][0]
                            if "delta" in choice:
                                delta = choice["delta"]
                                if "content" in delta:
                                    yield StreamChunk(
                                        content=delta["content"],
                                        finish_reason=choice.get("finish_reason"),
                                        model=model
                                    )
                    except json.JSONDecodeError:
                        continue
    
    async def list_models(self) -> list[str]:
        """List available models."""
        return self._config.available_models
