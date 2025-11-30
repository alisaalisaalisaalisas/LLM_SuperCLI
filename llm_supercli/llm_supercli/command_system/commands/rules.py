"""Rules command for llm_supercli."""
from pathlib import Path
from typing import Any

from ..base import SlashCommand, CommandResult


class RulesCommand(SlashCommand):
    """View and manage custom rules."""
    
    name = "rules"
    description = "View and manage custom rules loaded from .supercli/rules/"
    aliases = []
    usage = "[list | reload | show <filename>]"
    examples = [
        "/rules              # List all loaded rules",
        "/rules list         # List all loaded rules with sources",
        "/rules reload       # Force reload rules from disk",
        "/rules show <name>  # Show contents of a specific rule file",
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute rules command."""
        from ...prompts.rules import RulesLoader
        
        args = args.strip()
        parts = args.split(maxsplit=1)
        subcommand = parts[0].lower() if parts else ""
        subargs = parts[1] if len(parts) > 1 else ""
        
        # Create rules loader
        rules_loader = RulesLoader()
        cwd = Path.cwd()
        
        # No args or "list" - show loaded rules
        if not subcommand or subcommand == "list":
            return self._list_rules(rules_loader, cwd)
        
        # Reload rules
        if subcommand == "reload":
            return self._reload_rules(rules_loader, cwd)
        
        # Show specific rule file
        if subcommand == "show":
            return self._show_rule(rules_loader, cwd, subargs)
        
        return CommandResult.error(
            f"Unknown subcommand: `{subcommand}`.\n"
            f"Available: list, reload, show <filename>"
        )
    
    def _list_rules(self, rules_loader: "RulesLoader", cwd: Path) -> CommandResult:
        """List all loaded rules with their sources."""
        rule_files = rules_loader.load(cwd)
        
        if not rule_files:
            lines = [
                "# No Rules Loaded",
                "",
                "No custom rules found. You can create rules in:",
                "",
                f"**Global rules:** `{rules_loader.GLOBAL_RULES_DIR}`",
                f"**Local rules:** `{cwd / rules_loader.LOCAL_RULES_DIR}`",
                "",
                "Rules files are plain text files with instructions for the AI.",
                "Files are loaded alphabetically, with local rules taking precedence.",
            ]
            return CommandResult.success("\n".join(lines))
        
        lines = ["# Loaded Rules", ""]
        
        # Group by source
        global_rules = [r for r in rule_files if r.source == "global"]
        local_rules = [r for r in rule_files if r.source == "local"]
        
        if global_rules:
            lines.append("## Global Rules")
            lines.append(f"_From: `{rules_loader.GLOBAL_RULES_DIR}`_")
            lines.append("")
            for rule in global_rules:
                size = len(rule.content)
                lines.append(f"- **{rule.path.name}** ({size} chars)")
            lines.append("")
        
        if local_rules:
            lines.append("## Local Rules")
            lines.append(f"_From: `{cwd / rules_loader.LOCAL_RULES_DIR}`_")
            lines.append("")
            for rule in local_rules:
                size = len(rule.content)
                # Check if it's a legacy file
                is_legacy = rule.path.name in rules_loader.LEGACY_FILES
                legacy_marker = " (legacy)" if is_legacy else ""
                lines.append(f"- **{rule.path.name}**{legacy_marker} ({size} chars)")
            lines.append("")
        
        lines.append("Use `/rules show <filename>` to view a rule's contents.")
        lines.append("Use `/rules reload` to reload rules from disk.")
        
        return CommandResult.success("\n".join(lines))
    
    def _reload_rules(self, rules_loader: "RulesLoader", cwd: Path) -> CommandResult:
        """Force reload rules from disk."""
        # Load rules (this always reads from disk)
        rule_files = rules_loader.load(cwd)
        
        count = len(rule_files)
        global_count = len([r for r in rule_files if r.source == "global"])
        local_count = len([r for r in rule_files if r.source == "local"])
        
        return CommandResult.success(
            f"Reloaded **{count}** rule files.\n"
            f"- Global: {global_count}\n"
            f"- Local: {local_count}\n\n"
            f"Rules will be applied to the next prompt."
        )
    
    def _show_rule(self, rules_loader: "RulesLoader", cwd: Path, filename: str) -> CommandResult:
        """Show contents of a specific rule file."""
        if not filename:
            return CommandResult.error(
                "Please specify a filename.\n"
                "Usage: `/rules show <filename>`"
            )
        
        rule_files = rules_loader.load(cwd)
        
        # Find the rule file by name
        matching = [r for r in rule_files if r.path.name == filename]
        
        if not matching:
            available = [r.path.name for r in rule_files]
            if available:
                return CommandResult.error(
                    f"Rule file not found: `{filename}`.\n"
                    f"Available: {', '.join(available)}"
                )
            else:
                return CommandResult.error(
                    f"Rule file not found: `{filename}`.\n"
                    f"No rule files are currently loaded."
                )
        
        rule = matching[0]
        
        lines = [
            f"# Rule: {rule.path.name}",
            "",
            f"**Source:** {rule.source}",
            f"**Path:** `{rule.path}`",
            f"**Size:** {len(rule.content)} characters",
            "",
            "## Contents",
            "",
            "```",
            rule.content.strip(),
            "```",
        ]
        
        return CommandResult.success("\n".join(lines))
