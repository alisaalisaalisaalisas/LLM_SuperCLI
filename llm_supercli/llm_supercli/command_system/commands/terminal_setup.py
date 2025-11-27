"""Terminal setup command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class TerminalSetupCommand(SlashCommand):
    """Setup terminal integration."""
    
    name = "terminal-setup"
    description = "Setup terminal integration and shell completion"
    aliases = ["setup"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        import sys
        
        shell_configs = {
            "bash": {
                "file": "~/.bashrc",
                "completion": 'eval "$(llm-supercli --completion bash)"',
                "alias": 'alias llm="llm-supercli"'
            },
            "zsh": {
                "file": "~/.zshrc",
                "completion": 'eval "$(llm-supercli --completion zsh)"',
                "alias": 'alias llm="llm-supercli"'
            },
            "fish": {
                "file": "~/.config/fish/config.fish",
                "completion": "llm-supercli --completion fish | source",
                "alias": 'alias llm="llm-supercli"'
            },
            "powershell": {
                "file": "$PROFILE",
                "completion": "Invoke-Expression (llm-supercli --completion powershell)",
                "alias": 'Set-Alias -Name llm -Value llm-supercli'
            }
        }
        
        lines = [
            "# Terminal Setup",
            "",
            "Add these lines to your shell configuration:",
            ""
        ]
        
        for shell, config in shell_configs.items():
            lines.extend([
                f"## {shell.title()}",
                f"File: `{config['file']}`",
                "```",
                config['alias'],
                config['completion'],
                "```",
                ""
            ])
        
        lines.extend([
            "## Current Environment",
            f"Python: {sys.executable}",
            f"Platform: {sys.platform}",
        ])
        
        return CommandResult.success("\n".join(lines))
