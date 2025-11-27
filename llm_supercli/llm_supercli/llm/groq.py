"""
Groq LLM provider implementation for llm_supercli.
"""
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class GroqProvider(LLMProvider):
    """
    Groq API provider for fast inference.
    
    Groq provides extremely fast inference for open-source models
    using their custom LPU hardware.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize Groq provider.
        
        Args:
            api_key: Groq API key
            model: Default model to use
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
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="Groq",
            base_url="https://api.groq.com/openai/v1",
            default_model="llama-3.3-70b-versatile",
            available_models=[
                "llama-3.3-70b-versatile",
                "llama-3.3-70b-specdec",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
                "llama-3.2-1b-preview",
                "llama-3.2-3b-preview",
                "llama-3.2-11b-vision-preview",
                "llama-3.2-90b-vision-preview",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
                "whisper-large-v3",
                "whisper-large-v3-turbo",
            ],
            max_tokens=32768,
            supports_streaming=True,
            supports_functions=True,
            rate_limit_rpm=30,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to Groq."""
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
                timeout=60.0
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
        """Send a streaming chat completion request to Groq."""
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
                timeout=60.0
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
        """List available models from Groq API."""
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
