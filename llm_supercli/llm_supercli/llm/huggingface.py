"""
HuggingFace Inference API provider implementation for llm_supercli.
"""
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class HuggingFaceProvider(LLMProvider):
    """
    HuggingFace Inference API provider.
    
    Provides access to models hosted on HuggingFace's inference infrastructure.
    Supports both the free Inference API and paid Inference Endpoints.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        use_inference_endpoints: bool = False,
        endpoint_url: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize HuggingFace provider.
        
        Args:
            api_key: HuggingFace API token
            model: Default model to use
            use_inference_endpoints: Use dedicated Inference Endpoints
            endpoint_url: Custom Inference Endpoint URL
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
        
        self._use_inference_endpoints = use_inference_endpoints
        self._endpoint_url = endpoint_url
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="HuggingFace",
            base_url="https://api-inference.huggingface.co/models",
            default_model="meta-llama/Meta-Llama-3-70B-Instruct",
            available_models=[
                "meta-llama/Meta-Llama-3-70B-Instruct",
                "meta-llama/Meta-Llama-3-8B-Instruct",
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "google/gemma-7b-it",
                "google/gemma-2b-it",
                "HuggingFaceH4/zephyr-7b-beta",
                "microsoft/Phi-3-mini-4k-instruct",
                "Qwen/Qwen2-72B-Instruct",
                "bigcode/starcoder2-15b-instruct-v0.1",
                "codellama/CodeLlama-70b-Instruct-hf",
                "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
            ],
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=False,
            rate_limit_rpm=30,
            cost_per_1k_input=0.0,  # Free tier
            cost_per_1k_output=0.0,
        )
    
    def _get_api_url(self, model: str) -> str:
        """Get the API URL for the model."""
        if self._endpoint_url:
            return self._endpoint_url
        return f"{self._config.base_url}/{model}"
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to HuggingFace."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        prompt = self._format_chat_prompt(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
                "do_sample": True,
                **kwargs
            }
        }
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._get_api_url(model),
                headers=self._build_headers(),
                json=payload,
                timeout=120.0
            )
            
            if response.status_code == 503:
                data = response.json()
                if "estimated_time" in data:
                    wait_time = min(data["estimated_time"], 60)
                    import asyncio
                    await asyncio.sleep(wait_time)
                    response = await client.post(
                        self._get_api_url(model),
                        headers=self._build_headers(),
                        json=payload,
                        timeout=120.0
                    )
            
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        if isinstance(data, list):
            content = data[0].get("generated_text", "")
        else:
            content = data.get("generated_text", str(data))
        
        input_tokens = self._estimate_tokens(prompt)
        output_tokens = self._estimate_tokens(content)
        
        return LLMResponse(
            content=content,
            model=model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=0.0,
            finish_reason="stop",
            latency_ms=latency_ms,
            raw_response=data if isinstance(data, dict) else {"response": data}
        )
    
    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[StreamChunk, None]:
        """Send a streaming chat completion request to HuggingFace."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        prompt = self._format_chat_prompt(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
                "do_sample": True,
                **kwargs
            },
            "stream": True
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self._get_api_url(model),
                headers=self._build_headers(),
                json=payload,
                timeout=120.0
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if not data_str:
                            continue
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            token = data.get("token", {})
                            content = token.get("text", "")
                            
                            if content and not token.get("special", False):
                                yield StreamChunk(
                                    content=content,
                                    finish_reason=None,
                                    model=model
                                )
                        except (json.JSONDecodeError, KeyError):
                            continue
    
    def _format_chat_prompt(self, messages: list[dict]) -> str:
        """
        Format chat messages into a prompt string.
        
        Uses a generic chat format that works with most instruction-tuned models.
        """
        formatted_parts = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                formatted_parts.append(f"<|system|>\n{content}</s>")
            elif role == "user":
                formatted_parts.append(f"<|user|>\n{content}</s>")
            elif role == "assistant":
                formatted_parts.append(f"<|assistant|>\n{content}</s>")
        
        formatted_parts.append("<|assistant|>\n")
        
        return "\n".join(formatted_parts)
    
    async def list_models(self) -> list[str]:
        """List available models - returns predefined list."""
        return self._config.available_models
    
    async def get_model_info(self, model: Optional[str] = None) -> dict:
        """
        Get information about a model from HuggingFace Hub.
        
        Args:
            model: Model ID
            
        Returns:
            Model information dict
        """
        model = model or self._model
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://huggingface.co/api/models/{model}",
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                return {"id": model, "error": "Could not fetch model info"}
