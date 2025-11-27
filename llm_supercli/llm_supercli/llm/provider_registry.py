"""
Provider registry for managing LLM providers in llm_supercli.
Handles registration, discovery, and instantiation of providers.
"""
from typing import Any, Dict, Optional, Type

from .base import LLMProvider, ProviderConfig
from ..config import get_config


class ProviderRegistry:
    """
    Registry for LLM providers.
    
    Manages available providers and provides factory methods for instantiation.
    """
    
    _instance: Optional['ProviderRegistry'] = None
    
    def __new__(cls) -> 'ProviderRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._providers: Dict[str, Type[LLMProvider]] = {}
        self._instances: Dict[str, LLMProvider] = {}
        self._config = get_config()
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register built-in providers."""
        from .groq import GroqProvider
        from .openrouter import OpenRouterProvider
        from .together import TogetherProvider
        from .huggingface import HuggingFaceProvider
        from .local_ollama import OllamaProvider
        
        self.register("groq", GroqProvider)
        self.register("openrouter", OpenRouterProvider)
        self.register("together", TogetherProvider)
        self.register("huggingface", HuggingFaceProvider)
        self.register("ollama", OllamaProvider)
    
    def register(self, name: str, provider_class: Type[LLMProvider]) -> None:
        """
        Register a provider class.
        
        Args:
            name: Provider name/identifier
            provider_class: Provider class
        """
        self._providers[name.lower()] = provider_class
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a provider.
        
        Args:
            name: Provider name
            
        Returns:
            True if provider was unregistered
        """
        name = name.lower()
        if name in self._providers:
            del self._providers[name]
            if name in self._instances:
                del self._instances[name]
            return True
        return False
    
    def get(self, name: str, **kwargs: Any) -> Optional[LLMProvider]:
        """
        Get a provider instance.
        
        Args:
            name: Provider name
            **kwargs: Additional arguments for provider constructor
            
        Returns:
            Provider instance or None if not found
        """
        name = name.lower()
        
        if name not in self._providers:
            return None
        
        cache_key = f"{name}:{hash(frozenset(kwargs.items()))}"
        
        if cache_key not in self._instances:
            provider_class = self._providers[name]
            
            if 'api_key' not in kwargs:
                from ..constants import PROVIDERS
                if name in PROVIDERS:
                    env_key = PROVIDERS[name].get('env_key')
                    if env_key:
                        kwargs['api_key'] = self._config.get_api_key(env_key)
            
            self._instances[cache_key] = provider_class(**kwargs)
        
        return self._instances[cache_key]
    
    def get_or_raise(self, name: str, **kwargs: Any) -> LLMProvider:
        """
        Get a provider instance or raise an error.
        
        Args:
            name: Provider name
            **kwargs: Additional arguments
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider not found
        """
        provider = self.get(name, **kwargs)
        if provider is None:
            raise ValueError(f"Provider '{name}' not found. Available: {self.list_providers()}")
        return provider
    
    def list_providers(self) -> list[str]:
        """
        List registered provider names.
        
        Returns:
            List of provider names
        """
        return list(self._providers.keys())
    
    def is_registered(self, name: str) -> bool:
        """
        Check if a provider is registered.
        
        Args:
            name: Provider name
            
        Returns:
            True if registered
        """
        return name.lower() in self._providers
    
    def get_provider_info(self, name: str) -> Optional[dict]:
        """
        Get information about a provider.
        
        Args:
            name: Provider name
            
        Returns:
            Dict with provider info or None
        """
        provider = self.get(name)
        if provider is None:
            return None
        
        return {
            "name": provider.name,
            "model": provider.model,
            "available_models": provider.available_models,
            "has_api_key": provider.api_key is not None,
        }
    
    def list_all_models(self) -> Dict[str, list[str]]:
        """
        List all models from all providers.
        
        Returns:
            Dict mapping provider names to model lists
        """
        result = {}
        for name in self._providers:
            provider = self.get(name)
            if provider:
                result[name] = provider.available_models
        return result
    
    def find_provider_for_model(self, model: str) -> Optional[str]:
        """
        Find which provider supports a model.
        
        Args:
            model: Model ID
            
        Returns:
            Provider name or None
        """
        for name in self._providers:
            provider = self.get(name)
            if provider and provider.supports_model(model):
                return name
        return None
    
    def get_default_provider(self) -> LLMProvider:
        """
        Get the default provider based on configuration.
        
        Returns:
            Default provider instance
        """
        provider_name = self._config.llm.provider
        return self.get_or_raise(provider_name)
    
    def clear_instances(self) -> None:
        """Clear cached provider instances."""
        self._instances.clear()
    
    def set_api_key(self, provider_name: str, api_key: str) -> bool:
        """
        Set API key for a provider.
        
        Args:
            provider_name: Provider name
            api_key: API key value
            
        Returns:
            True if set successfully
        """
        provider = self.get(provider_name)
        if provider:
            provider.api_key = api_key
            return True
        return False


_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry instance."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
