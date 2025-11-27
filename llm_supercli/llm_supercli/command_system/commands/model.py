"""Model command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class ModelCommand(SlashCommand):
    """Switch LLM model or provider."""
    
    name = "model"
    description = "Switch LLM model or provider"
    aliases = ["m"]
    usage = "[provider/model | list]"
    examples = [
        "/model",
        "/model list",
        "/model groq/llama-3.3-70b-versatile",
        "/model openrouter/anthropic/claude-3.5-sonnet"
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute model command."""
        from ...config import get_config
        from ...llm import get_provider_registry
        
        config = get_config()
        registry = get_provider_registry()
        
        args = args.strip()
        
        if not args:
            return self._show_current(config, registry)
        
        if args.lower() == "list":
            return self._list_models(registry)
        
        return self._switch_model(args, config, registry)
    
    def _show_current(self, config, registry) -> CommandResult:
        """Show current model configuration."""
        provider = registry.get(config.llm.provider)
        
        lines = [
            "# Current Model Configuration",
            "",
            f"**Provider:** {config.llm.provider}",
            f"**Model:** {config.llm.model}",
            f"**Max Tokens:** {config.llm.max_tokens}",
            f"**Temperature:** {config.llm.temperature}",
        ]
        
        if provider:
            lines.append(f"**API Key Set:** {'Yes' if provider.api_key else 'No'}")
        
        lines.extend([
            "",
            "Use `/model list` to see available models.",
            "Use `/model <provider>/<model>` to switch."
        ])
        
        return CommandResult.success("\n".join(lines))
    
    def _list_models(self, registry) -> CommandResult:
        """List all available models."""
        all_models = registry.list_all_models()
        
        lines = ["# Available Models", ""]
        
        for provider, models in all_models.items():
            info = registry.get_provider_info(provider)
            has_key = info.get("has_api_key", False) if info else False
            key_status = "[+]" if has_key else "[-]"
            
            lines.append(f"## {provider.title()} {key_status}")
            for model in models[:10]:
                lines.append(f"  - `{provider}/{model}`")
            if len(models) > 10:
                lines.append(f"  - ... and {len(models) - 10} more")
            lines.append("")
        
        return CommandResult.success("\n".join(lines), data=all_models)
    
    def _switch_model(self, model_spec: str, config, registry) -> CommandResult:
        """Switch to a different model."""
        if "/" in model_spec:
            parts = model_spec.split("/", 1)
            provider_name = parts[0].lower()
            model_name = parts[1]
        else:
            provider_name = config.llm.provider
            model_name = model_spec
        
        provider = registry.get(provider_name)
        if not provider:
            return CommandResult.error(
                f"Unknown provider: {provider_name}. "
                f"Available: {', '.join(registry.list_providers())}"
            )
        
        if not provider.api_key and provider_name != "ollama":
            return CommandResult.error(
                f"No API key configured for {provider_name}. "
                f"Set the environment variable or use /settings."
            )
        
        config.update_llm(provider=provider_name, model=model_name)
        
        return CommandResult.success(
            f"Switched to **{provider_name}/{model_name}**"
        )
