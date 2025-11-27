"""IDE command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class IDECommand(SlashCommand):
    """Open in IDE."""
    
    name = "ide"
    description = "Open files or project in IDE"
    usage = "[file|path]"
    examples = ["/ide", "/ide main.py", "/ide ./src"]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        import subprocess
        import shutil
        
        path = args.strip() or "."
        
        editors = ["code", "cursor", "subl", "atom", "vim", "nano"]
        
        for editor in editors:
            if shutil.which(editor):
                try:
                    subprocess.Popen([editor, path])
                    return CommandResult.success(f"Opened `{path}` in {editor}")
                except Exception as e:
                    continue
        
        return CommandResult.error(
            "No supported IDE found. Install VS Code, Cursor, or Sublime Text."
        )
