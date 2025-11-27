"""
Together AI LLM provider implementation for llm_supercli.
"""
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class TogetherProvider(LLMProvider):
    """
    Together AI provider for open-source model inference.
    
    Together provides fast inference for a wide variety of
    open-source models including Llama, Mistral, and others.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize Together AI provider.
        
        Args:
            api_key: Together API key
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
            name="Together",
            base_url="https://api.together.xyz/v1",
            default_model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            available_models=[
                "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
                "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",
                "mistralai/Mixtral-8x22B-Instruct-v0.1",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "Qwen/Qwen2.5-72B-Instruct-Turbo",
                "Qwen/Qwen2.5-7B-Instruct-Turbo",
                "google/gemma-2-27b-it",
                "google/gemma-2-9b-it",
                "deepseek-ai/deepseek-llm-67b-chat",
                "databricks/dbrx-instruct",
                "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
                "togethercomputer/StripedHyena-Nous-7B",
            ],
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=False,
            rate_limit_rpm=60,
            cost_per_1k_input=0.0002,
            cost_per_1k_output=0.0006,
        )
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to Together AI."""
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
        
        content = data["choices"][0]["message"]["content"]
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
        """Send a streaming chat completion request to Together AI."""
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
        """List available models from Together AI API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._config.base_url}/models",
                    headers=self._build_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                chat_models = [
                    model["id"] for model in data
                    if model.get("type") == "chat"
                ]
                return chat_models or self._config.available_models
            except httpx.HTTPError:
                return self._config.available_models
    
    async def get_embeddings(
        self,
        texts: list[str],
        model: str = "togethercomputer/m2-bert-80M-8k-retrieval"
    ) -> list[list[float]]:
        """
        Get embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use
            
        Returns:
            List of embedding vectors
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._config.base_url}/embeddings",
                headers=self._build_headers(),
                json={
                    "model": model,
                    "input": texts
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            return [item["embedding"] for item in data["data"]]
