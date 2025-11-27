"""
Ollama (local) LLM provider implementation for llm_supercli.
"""
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference.
    
    Ollama runs models locally on your machine, providing privacy
    and offline capabilities. Requires Ollama to be installed and running.
    """
    
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize Ollama provider.
        
        Args:
            host: Ollama server host URL
            model: Default model to use
            **kwargs: Additional configuration
        """
        config = self._default_config()
        config.base_url = host
        if model:
            config.default_model = model
        super().__init__(config)
        
        if model:
            self._model = model
        
        self._host = host
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="Ollama",
            base_url="http://localhost:11434",
            default_model="llama3.2",
            available_models=[
                "llama3.2",
                "llama3.2:1b",
                "llama3.1",
                "llama3.1:70b",
                "mistral",
                "mistral-nemo",
                "mixtral",
                "codellama",
                "codellama:70b",
                "phi3",
                "phi3:medium",
                "gemma2",
                "gemma2:27b",
                "qwen2.5",
                "qwen2.5:72b",
                "deepseek-coder-v2",
                "starcoder2",
                "command-r",
                "command-r-plus",
            ],
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=False,
            rate_limit_rpm=1000,
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
        """Send a chat completion request to Ollama."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {})
            }
        }
        
        if "system" in kwargs:
            payload["system"] = kwargs["system"]
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._host}/api/chat",
                json=payload,
                timeout=300.0  # Local models can be slow
            )
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        content = data.get("message", {}).get("content", "")
        
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        
        return LLMResponse(
            content=content,
            model=data.get("model", model),
            provider=self.name,
            input_tokens=prompt_eval_count,
            output_tokens=eval_count,
            cost=0.0,
            finish_reason=data.get("done_reason", "stop"),
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
        """Send a streaming chat completion request to Ollama."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {})
            }
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._host}/api/chat",
                json=payload,
                timeout=300.0
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        import json
                        data = json.loads(line)
                        
                        content = data.get("message", {}).get("content", "")
                        
                        if content:
                            yield StreamChunk(
                                content=content,
                                finish_reason="stop" if data.get("done") else None,
                                model=data.get("model", model)
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue
    
    async def list_models(self) -> list[str]:
        """List locally available models from Ollama."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._host}/api/tags",
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            except httpx.HTTPError:
                return self._config.available_models
    
    async def pull_model(self, model: str) -> AsyncGenerator[dict, None]:
        """
        Pull (download) a model from Ollama library.
        
        Args:
            model: Model name to pull
            
        Yields:
            Progress updates as dicts
        """
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._host}/api/pull",
                json={"name": model},
                timeout=None
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
    
    async def delete_model(self, model: str) -> bool:
        """
        Delete a local model.
        
        Args:
            model: Model name to delete
            
        Returns:
            True if deleted
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self._host}/api/delete",
                    json={"name": model},
                    timeout=30.0
                )
                return response.status_code == 200
            except httpx.HTTPError:
                return False
    
    async def get_model_info(self, model: Optional[str] = None) -> dict:
        """
        Get detailed information about a model.
        
        Args:
            model: Model name
            
        Returns:
            Model information dict
        """
        model = model or self._model
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._host}/api/show",
                    json={"name": model},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                return {"name": model, "error": "Could not fetch model info"}
    
    async def generate_embeddings(
        self,
        text: str,
        model: str = "nomic-embed-text"
    ) -> list[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text to embed
            model: Embedding model to use
            
        Returns:
            Embedding vector
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._host}/api/embeddings",
                json={
                    "model": model,
                    "prompt": text
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
    
    async def is_running(self) -> bool:
        """
        Check if Ollama server is running.
        
        Returns:
            True if server is accessible
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._host}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
            except httpx.HTTPError:
                return False
