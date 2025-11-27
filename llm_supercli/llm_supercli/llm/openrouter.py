"""
OpenRouter LLM provider implementation for llm_supercli.
"""
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter API provider for unified access to multiple LLMs.
    
    OpenRouter provides a single API to access models from OpenAI,
    Anthropic, Google, Meta, and many other providers.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        site_url: Optional[str] = None,
        site_name: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize OpenRouter provider.
        
        Args:
            api_key: OpenRouter API key
            model: Default model to use
            site_url: Your site URL for rankings
            site_name: Your site name for rankings
            **kwargs: Additional configuration
        """
        config = self._default_config()
        if api_key:
            config.api_key = api_key
        if model:
            config.default_model = model
        super().__init__(config)
        
        if model:
            self._model = model
        
        self._headers["HTTP-Referer"] = site_url or "https://github.com/llm-supercli"
        self._headers["X-Title"] = site_name or "LLM SuperCLI"
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            default_model="anthropic/claude-3.5-sonnet",
            available_models=[
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-opus",
                "anthropic/claude-3-sonnet",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "openai/gpt-4-turbo",
                "openai/o1-preview",
                "openai/o1-mini",
                "google/gemini-pro-1.5",
                "google/gemini-flash-1.5",
                "meta-llama/llama-3.1-405b-instruct",
                "meta-llama/llama-3.1-70b-instruct",
                "meta-llama/llama-3.1-8b-instruct",
                "mistralai/mistral-large",
                "mistralai/mixtral-8x22b-instruct",
                "deepseek/deepseek-chat",
                "qwen/qwen-2.5-72b-instruct",
            ],
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
            rate_limit_rpm=60,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        )
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to OpenRouter."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._config.base_url}/chat/completions",
                headers=self._build_headers(),
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
            cost=self.calculate_cost(input_tokens, output_tokens),
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
        """Send a streaming chat completion request to OpenRouter."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._config.base_url}/chat/completions",
                headers=self._build_headers(),
                json=payload,
                timeout=120.0
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        import json
                        data = json.loads(data_str)
                        
                        if "choices" in data and data["choices"]:
                            choice = data["choices"][0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield StreamChunk(
                                    content=content,
                                    finish_reason=choice.get("finish_reason"),
                                    model=data.get("model", model)
                                )
                    except (json.JSONDecodeError, KeyError):
                        continue
    
    async def list_models(self) -> list[str]:
        """List available models from OpenRouter API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._config.base_url}/models",
                    headers=self._build_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return [model["id"] for model in data.get("data", [])]
            except httpx.HTTPError:
                return self._config.available_models
    
    async def get_generation_stats(self, generation_id: str) -> Optional[dict]:
        """
        Get stats for a specific generation.
        
        Args:
            generation_id: Generation ID from response
            
        Returns:
            Generation stats or None
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._config.base_url}/generation?id={generation_id}",
                    headers=self._build_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                return None
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost - OpenRouter has variable pricing per model.
        This is a rough estimate; actual cost comes from usage response.
        """
        return super().calculate_cost(input_tokens, output_tokens)
