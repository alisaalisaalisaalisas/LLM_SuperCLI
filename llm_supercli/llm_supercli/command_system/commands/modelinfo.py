"""
Model info command - displays detailed information about a model.
"""
from typing import Optional

from ..base import CommandResult, SlashCommand
from ...model_specs import format_model_info


class ModelInfoCommand(SlashCommand):
    """Display detailed information about a model."""

    name = "modelinfo"
    description = "Show detailed information about a specific model"
    usage = "[provider/model] - Show pricing, context window, and features"

    def run(self, args: str = "", **kwargs) -> CommandResult:
        """Execute the modelinfo command."""
        if not args or not args.strip():
            return CommandResult.error(
                "Please specify a model.\n"
                f"Usage: {self.usage}\n"
                "Example: /modelinfo gemini/gemini-2.5-flash"
            )

        # Parse provider/model
        parts = args.strip().split("/", 1)
        if len(parts) != 2:
            return CommandResult.error(
                "Invalid format. Use: /modelinfo provider/model\n"
                "Example: /modelinfo gemini/gemini-2.5-flash"
            )

        provider, model = parts
        provider = provider.strip().lower()
        model = model.strip()

        # Get model info
        info_text = format_model_info(provider, model)

        if "No information available" in info_text:
            return CommandResult.error(
                f"No information available for {provider}/{model}\n"
                "Available providers: gemini, qwen"
            )

        return CommandResult.success(
            message=info_text,
            data={"provider": provider, "model": model}
        )
