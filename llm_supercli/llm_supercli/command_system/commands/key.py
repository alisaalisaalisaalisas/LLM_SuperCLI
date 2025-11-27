"""API Key command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class KeyCommand(SlashCommand):
    """Manage API keys for providers."""
    
    name = "key"
    description = "Set or view API keys for providers"
    aliases = ["apikey", "keys"]
    usage = "<provider> [api_key] | list"
    examples = [
        "/key list                    # List all providers and key status",
        "/key groq sk-xxxx            # Set Groq API key",
        "/key openrouter sk-or-xxxx   # Set OpenRouter API key",
        "/key together xxxx           # Set Together AI API key",
        "/key huggingface hf_xxxx     # Set HuggingFace API key",
    ]
    
    PROVIDER_ENV_MAP = {
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "together": "TOGETHER_API_KEY",
        "huggingface": "HF_API_KEY",
        "hf": "HF_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute key command."""
        from ...config import get_config
        from ...llm import get_provider_registry
        
        config = get_config()
        registry = get_provider_registry()
        
        parts = args.strip().split(maxsplit=1)
        
        if not parts or parts[0].lower() == "list":
            return self._list_keys(config, registry)
        
        provider_name = parts[0].lower()
        
        if provider_name not in self.PROVIDER_ENV_MAP:
            available = ", ".join(sorted(set(self.PROVIDER_ENV_MAP.keys()) - {"hf"}))
            return CommandResult.error(
                f"Unknown provider: {provider_name}\n"
                f"Available providers: {available}"
            )
        
        if len(parts) < 2:
            return self._show_key_status(config, provider_name)
        
        api_key = parts[1].strip()
        return self._set_key(config, registry, provider_name, api_key)
    
    def _list_keys(self, config, registry) -> CommandResult:
        """List all providers and their API key status."""
        lines = [
            "# API Keys",
            "",
            "| Provider | Status | Env Variable |",
            "|----------|--------|--------------|",
        ]
        
        for provider, env_key in sorted(set((k, v) for k, v in self.PROVIDER_ENV_MAP.items() if k != "hf")):
            key_value = config.get_api_key(env_key)
            if key_value:
                masked = key_value[:4] + "..." + key_value[-4:] if len(key_value) > 8 else "****"
                status = f"[+] {masked}"
            else:
                status = "[-] Not set"
            lines.append(f"| {provider.title()} | {status} | `{env_key}` |")
        
        lines.extend([
            "",
            "Use `/key <provider> <api_key>` to set a key.",
            "Keys are saved to `~/.llm_supercli/config.json`."
        ])
        
        return CommandResult.success("\n".join(lines))
    
    def _show_key_status(self, config, provider_name: str) -> CommandResult:
        """Show status of a specific provider's key."""
        env_key = self.PROVIDER_ENV_MAP[provider_name]
        key_value = config.get_api_key(env_key)
        
        if key_value:
            masked = key_value[:4] + "..." + key_value[-4:] if len(key_value) > 8 else "****"
            return CommandResult.success(
                f"**{provider_name.title()}** API key is set: `{masked}`"
            )
        else:
            return CommandResult.success(
                f"**{provider_name.title()}** API key is not set.\n"
                f"Use `/key {provider_name} <your-api-key>` to set it."
            )
    
    def _set_key(self, config, registry, provider_name: str, api_key: str) -> CommandResult:
        """Set an API key for a provider."""
        env_key = self.PROVIDER_ENV_MAP[provider_name]
        
        config.set_api_key(env_key, api_key, persist=True)
        
        provider = registry.get(provider_name)
        if provider:
            provider.api_key = api_key
        
        masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "****"
        
        lines = [
            f"API key for **{provider_name.title()}** set to `{masked}`",
            "Key saved to config file.",
            "",
        ]
        
        # Show available models for this provider
        if provider and provider.available_models:
            lines.append(f"**Available models for {provider_name.title()}:**")
            for model in provider.available_models[:15]:
                lines.append(f"  - `{model}`")
            if len(provider.available_models) > 15:
                lines.append(f"  - ... and {len(provider.available_models) - 15} more")
            lines.append("")
            lines.append(f"Use `/model {provider_name}/<model_name>` to switch.")
        
        return CommandResult.success("\n".join(lines))
