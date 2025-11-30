"""Mode command for llm_supercli."""
from typing import Any

from ..base import SlashCommand, CommandResult


class ModeCommand(SlashCommand):
    """Switch operational mode for the CLI agent."""
    
    name = "mode"
    description = "Switch operational mode (code, ask, architect)"
    aliases = []
    usage = "[mode_name | list | current]"
    examples = [
        "/mode                # Show current mode",
        "/mode list           # List all available modes",
        "/mode code           # Switch to code mode (full tool access)",
        "/mode ask            # Switch to ask mode (read-only, Q&A focused)",
        "/mode architect      # Switch to architect mode (planning focused)",
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute mode command."""
        from ...prompts.modes import ModeManager
        
        args = args.strip().lower()
        
        # Get the CLI instance to access current mode
        # The session stores the current mode
        session = kwargs.get("session")
        config = kwargs.get("config")
        renderer = kwargs.get("renderer")
        
        # Create a mode manager to access modes
        mode_manager = ModeManager()
        
        # No args or "current" - show current mode
        if not args or args == "current":
            return self._show_current(session, mode_manager)
        
        # List all modes
        if args == "list":
            return self._list_modes(mode_manager)
        
        # Switch to a specific mode
        return self._switch_mode(args, session, mode_manager)
    
    def _show_current(self, session, mode_manager: "ModeManager") -> CommandResult:
        """Show current mode configuration."""
        # Get current mode from session metadata or default to "code"
        current_mode_slug = "code"
        if session and hasattr(session, "metadata"):
            current_mode_slug = session.metadata.get("mode", "code")
        
        try:
            mode = mode_manager.get(current_mode_slug)
        except KeyError:
            mode = mode_manager.get("code")
            current_mode_slug = "code"
        
        lines = [
            "# Current Mode",
            "",
            f"**Mode:** {mode.icon} {mode.name} (`{mode.slug}`)",
            "",
            "**Role:**",
            mode.role_definition[:200] + "..." if len(mode.role_definition) > 200 else mode.role_definition,
            "",
            f"**Tool Groups:** {', '.join(mode.tool_groups) if mode.tool_groups else 'None'}",
            "",
            "Use `/mode list` to see all available modes.",
            "Use `/mode <name>` to switch modes.",
        ]
        
        return CommandResult.success("\n".join(lines))
    
    def _list_modes(self, mode_manager: "ModeManager") -> CommandResult:
        """List all available modes."""
        modes = mode_manager.list_modes()
        
        lines = ["# Available Modes", ""]
        
        for mode in modes:
            tool_groups = ", ".join(mode.tool_groups) if mode.tool_groups else "none"
            lines.append(f"## {mode.icon} {mode.name}")
            lines.append(f"**Slug:** `{mode.slug}`")
            lines.append(f"**Tool Groups:** {tool_groups}")
            lines.append("")
            # Show first line of role definition
            first_line = mode.role_definition.split("\n")[0][:100]
            lines.append(f"_{first_line}..._")
            lines.append("")
        
        lines.append("Use `/mode <slug>` to switch to a mode.")
        
        return CommandResult.success("\n".join(lines))
    
    def _switch_mode(self, mode_slug: str, session, mode_manager: "ModeManager") -> CommandResult:
        """Switch to a different mode."""
        # Check if mode exists
        if not mode_manager.has_mode(mode_slug):
            available = [m.slug for m in mode_manager.list_modes()]
            return CommandResult.error(
                f"Unknown mode: `{mode_slug}`.\n"
                f"Available modes: {', '.join(available)}"
            )
        
        mode = mode_manager.get(mode_slug)
        
        # Store mode in session metadata
        if session:
            if not hasattr(session, "metadata"):
                session.metadata = {}
            session.metadata["mode"] = mode_slug
        
        return CommandResult.success(
            f"Switched to **{mode.icon} {mode.name}** mode.\n\n"
            f"Tool groups: {', '.join(mode.tool_groups) if mode.tool_groups else 'none'}"
        )
