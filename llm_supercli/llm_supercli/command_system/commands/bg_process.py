"""Background process command for llm_supercli."""
from typing import Any
from ..base import SlashCommand, CommandResult


class BGProcessCommand(SlashCommand):
    """Manage background processes."""
    
    name = "bg"
    description = "Manage background processes"
    aliases = ["background", "jobs"]
    usage = "[list|kill] [pid]"
    
    _processes: dict = {}
    
    def run(self, args: str = "", **kwargs: Any) -> CommandResult:
        parts = args.strip().split()
        subcommand = parts[0].lower() if parts else "list"
        
        if subcommand == "list":
            if not self._processes:
                return CommandResult.success("No background processes running")
            
            lines = ["# Background Processes", ""]
            for pid, info in self._processes.items():
                lines.append(f"- [{pid}] {info.get('command', 'Unknown')}")
            return CommandResult.success("\n".join(lines))
        
        elif subcommand == "kill":
            if len(parts) < 2:
                return CommandResult.error("Please specify a process ID")
            
            pid = parts[1]
            if pid in self._processes:
                del self._processes[pid]
                return CommandResult.success(f"Killed process {pid}")
            return CommandResult.error(f"Process not found: {pid}")
        
        return CommandResult.error("Unknown subcommand. Use: list, kill")
