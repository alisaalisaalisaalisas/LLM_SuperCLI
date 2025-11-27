"""
Base classes for LLM providers in llm_supercli.
Defines the abstract interface that all providers must implement.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional


@dataclass
class StreamChunk:
    """Represents a chunk of streamed response."""
    content: str
    finish_reason: Optional[str] = None
    tokens: int = 0
    model: Optional[str] = None


@dataclass
class LLMResponse:
    """Represents a complete LLM response."""
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    raw_response: Optional[dict] = None
    
    def __post_init__(self) -> None:
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass 
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    base_url: str
    api_key: Optional[str] = None
    default_model: str = ""
    available_models: list[str] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    supports_streaming: bool = True
    supports_functions: bool = False
    rate_limit_rpm: int = 60
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All provider implementations must inherit from this class and implement
    the required methods for chat completion.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        """
        Initialize the provider.
        
        Args:
            config: Provider configuration
        """
        self._config = config or self._default_config()
        self._api_key = self._config.api_key
        self._model = self._config.default_model
        self._headers: dict[str, str] = {}
    
    @abstractmethod
    def _default_config(self) -> ProviderConfig:
        """
        Get the default configuration for this provider.
        
        Returns:
            Default ProviderConfig
        """
        pass
    
    @property
    def name(self) -> str:
        """Provider name."""
        return self._config.name
    
    @property
    def model(self) -> str:
        """Current model."""
        return self._model
    
    @model.setter
    def model(self, value: str) -> None:
        """Set current model."""
        self._model = value
    
    @property
    def available_models(self) -> list[str]:
        """List of available models."""
        return self._config.available_models
    
    @property
    def api_key(self) -> Optional[str]:
        """API key."""
        return self._api_key
    
    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set API key."""
        self._api_key = value
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with completion
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Send a streaming chat completion request.
        
        Args:
            messages: List of message dicts
            model: Optional model override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Additional provider-specific parameters
            
        Yields:
            StreamChunk objects as response comes in
        """
        pass
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate the cost for a request.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1000) * self._config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self._config.cost_per_1k_output
        return input_cost + output_cost
    
    async def validate_api_key(self) -> bool:
        """
        Validate that the API key works.
        
        Returns:
            True if API key is valid
        """
        try:
            response = await self.chat(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return bool(response.content)
        except Exception:
            return False
    
    async def list_models(self) -> list[str]:
        """
        List available models from the provider API.
        
        Returns:
            List of model IDs
        """
        return self._config.available_models
    
    def supports_model(self, model: str) -> bool:
        """
        Check if a model is supported.
        
        Args:
            model: Model ID to check
            
        Returns:
            True if supported
        """
        return model in self._config.available_models
    
    def get_model_info(self, model: Optional[str] = None) -> dict:
        """
        Get information about a model.
        
        Args:
            model: Model ID (uses current if not provided)
            
        Returns:
            Dict with model information
        """
        model = model or self._model
        return {
            "id": model,
            "provider": self.name,
            "max_tokens": self._config.max_tokens,
            "cost_per_1k_input": self._config.cost_per_1k_input,
            "cost_per_1k_output": self._config.cost_per_1k_output,
        }
    
    def _build_headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        headers.update(self._headers)
        return headers
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self._model})"
