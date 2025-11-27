"""File inclusion command for llm_supercli."""
from pathlib import Path
from typing import Any
from ..base import SlashCommand, CommandResult


class FileCommand(SlashCommand):
    """Include file contents in the conversation."""
    
    name = "file"
    aliases = ["f", "include"]
    description = "Include file contents in prompt (alternative to @file)"
    usage = "<path>"
    examples = [
        "/file readme.md",
        "/file src/main.py",
        "/f config.json"
    ]
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute file inclusion command."""
        if not args.strip():
            return CommandResult.error("Usage: /file <path>\n\nExample: /file readme.md")
        
        filepath = Path(args.strip()).expanduser()
        
        if not filepath.exists():
            return CommandResult.error(f"File not found: {filepath}")
        
        if not filepath.is_file():
            return CommandResult.error(f"Not a file: {filepath}")
        
        try:
            # Check file size
            size = filepath.stat().st_size
            if size > 1024 * 1024:  # 1MB limit
                return CommandResult.error(f"File too large: {size / 1024:.1f} KB (max 1MB)")
            
            # Read file
            content = filepath.read_text(encoding='utf-8', errors='replace')
            
            # Format output
            lines = len(content.splitlines())
            output = f"**Included: {filepath.name}** ({lines} lines)\n\n```\n{content}\n```"
            
            return CommandResult.success(
                message=output,
                data={"content": content, "path": str(filepath)}
            )
            
        except Exception as e:
            return CommandResult.error(f"Error reading file: {e}")
