"""Settings command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class SettingsCommand(SlashCommand):
    """View and modify settings."""
    
    name = "settings"
    description = "View and modify CLI settings (use -i for interactive menu)"
    aliases = ["config", "prefs"]
    usage = "[key] [value] | -i"
    examples = [
        "/settings              # Show all settings",
        "/settings -i           # Interactive settings menu",
        "/settings theme dark",
        "/settings temperature 0.8",
        "/settings streaming true"
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute settings command."""
        from ...config import get_config
        from ...rich_ui.falling_menu import SettingsMenu
        
        config = get_config()
        parts = args.strip().split(maxsplit=1)
        
        # Interactive mode - show falling menu
        # Default to interactive if no args, or if -i flag is present
        if not parts or (len(parts) == 1 and parts[0] in ["-i", "--interactive"]):
            # Force interactive with falling menu
            menu = SettingsMenu()
            result = menu.show(config)
            if result:
                key, value = result
                # Handle combined provider + model change
                if key == "provider_and_model":
                    provider, model = value
                    self._set_setting(config, "provider", provider)
                    return self._set_setting(config, "model", model)
                return self._set_setting(config, key, value)
            else:
                return CommandResult.info("Settings modification cancelled")
            from rich.console import Console
            console = Console()
            try:
                console.print()
                choice = console.input("[dim]Press Enter for interactive menu, or type setting name: [/]")
                if not choice.strip():
                    menu = SettingsMenu(console)
                    result = menu.show(config)
                    if result:
                        key, value = result
                        # Handle combined provider + model change
                        if key == "provider_and_model":
                            provider, model = value
                            self._set_setting(config, "provider", provider)
                            return self._set_setting(config, "model", model)
                        return self._set_setting(config, key, value)
                    return CommandResult.info("Settings modification cancelled")
                else:
                    parts = choice.strip().split(maxsplit=1)
                    key = parts[0].lower()
                    value = parts[1] if len(parts) > 1 else None
                    if value is None:
                        return self._show_setting(config, key)
                    return self._set_setting(config, key, value)
            except (EOFError, KeyboardInterrupt):
                return CommandResult.info("Cancelled")
        
        key = parts[0].lower()
        value = parts[1] if len(parts) > 1 else None
        
        if value is None:
            return self._show_setting(config, key)
        
        return self._set_setting(config, key, value)
    
    def _show_settings(self, config) -> CommandResult:
        """Show all settings."""
        lines = [
            "# Settings",
            "",
            "## LLM",
            f"  provider: {config.llm.provider}",
            f"  model: {config.llm.model}",
            f"  temperature: {config.llm.temperature}",
            f"  max_tokens: {config.llm.max_tokens}",
            "",
            "## UI",
            f"  theme: {config.ui.theme}",
            f"  streaming: {config.ui.streaming}",
            f"  markdown_rendering: {config.ui.markdown_rendering}",
            f"  syntax_highlighting: {config.ui.syntax_highlighting}",
            f"  show_token_count: {config.ui.show_token_count}",
            f"  show_cost: {config.ui.show_cost}",
            "",
            "## MCP",
            f"  enabled: {config.mcp.enabled}",
            f"  auto_connect: {config.mcp.auto_connect}",
            "",
            "Use `/settings <key> <value>` to change a setting."
        ]
        
        return CommandResult.success("\n".join(lines))
    
    def _show_setting(self, config, key: str) -> CommandResult:
        """Show a specific setting."""
        value = self._get_setting(config, key)
        if value is not None:
            return CommandResult.success(f"**{key}**: {value}")
        return CommandResult.error(f"Unknown setting: {key}")
    
    def _set_setting(self, config, key: str, value: str) -> CommandResult:
        """Set a setting value."""
        value_lower = value.lower()
        if value_lower in ("true", "yes", "1", "on"):
            typed_value = True
        elif value_lower in ("false", "no", "0", "off"):
            typed_value = False
        else:
            try:
                typed_value = float(value) if "." in value else int(value)
            except ValueError:
                typed_value = value
        
        llm_keys = ["provider", "model", "temperature", "max_tokens", "system_prompt"]
        ui_keys = ["theme", "streaming", "markdown_rendering", "syntax_highlighting", 
                   "show_token_count", "show_cost"]
        mcp_keys = ["enabled", "auto_connect"]
        
        if key in llm_keys:
            config.update_llm(**{key: typed_value})
            return CommandResult.success(f"Set **{key}** to `{typed_value}`")
        elif key in ui_keys:
            config.update_ui(**{key: typed_value})
            return CommandResult.success(f"Set **{key}** to `{typed_value}`")
        elif key.startswith("mcp.") or key in mcp_keys:
            actual_key = key.replace("mcp.", "")
            if hasattr(config.mcp, actual_key):
                setattr(config.mcp, actual_key, typed_value)
                config.save()
                return CommandResult.success(f"Set **{key}** to `{typed_value}`")
        
        return CommandResult.error(
            f"Unknown setting: {key}. Use `/settings` to see available settings."
        )
    
    def _get_setting(self, config, key: str) -> Any:
        """Get a setting value by key."""
        if hasattr(config.llm, key):
            return getattr(config.llm, key)
        if hasattr(config.ui, key):
            return getattr(config.ui, key)
        if hasattr(config.mcp, key):
            return getattr(config.mcp, key)
        return None
