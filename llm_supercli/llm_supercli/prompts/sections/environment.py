"""
EnvironmentSection - Renders environment context information.

This section appears later in the prompt (order: 50) and provides
detailed information about the current working environment.
"""

from .base import PromptSection, SectionContext


class EnvironmentSection(PromptSection):
    """Renders environment context information.
    
    The EnvironmentSection provides detailed information about the
    current working environment including OS, shell, working directory,
    and optionally a project structure summary.
    
    Example output:
        # Environment
        
        Operating System: Windows
        Shell: PowerShell
        Working Directory: C:\\Users\\dev\\project
        
        ## Project Structure
        
        project/
        ├── src/
        │   ├── main.py
        │   └── utils.py
        ├── tests/
        └── README.md
    """
    
    def __init__(self, include_project_structure: bool = True) -> None:
        """Initialize the EnvironmentSection.
        
        Args:
            include_project_structure: Whether to include project structure
                summary when available.
        """
        self._include_project_structure = include_project_structure
        self._project_summary: str | None = None
    
    @property
    def name(self) -> str:
        """Section identifier."""
        return "environment"
    
    @property
    def order(self) -> int:
        """Sort order - later in prompt."""
        return 50
    
    def set_project_summary(self, summary: str | None) -> None:
        """Set the project structure summary.
        
        Args:
            summary: The project structure summary string, or None.
        """
        self._project_summary = summary
    
    def render(self, context: SectionContext) -> str:
        """Render environment information.
        
        Args:
            context: The SectionContext containing environment info.
            
        Returns:
            Formatted environment section.
        """
        lines = ["# Environment", ""]
        
        # Basic environment info
        os_name = self._get_os_display_name(context.os_type)
        shell_name = self._get_shell_display_name(context.shell)
        
        lines.append(f"Operating System: {os_name}")
        lines.append(f"Shell: {shell_name}")
        lines.append(f"Working Directory: {context.cwd}")
        
        # Add any custom variables that might be relevant
        if context.variables:
            env_vars = {k: v for k, v in context.variables.items() 
                       if k.startswith("env_") or k in ("user", "home")}
            if env_vars:
                lines.append("")
                lines.append("## Environment Variables")
                lines.append("")
                for key, value in env_vars.items():
                    display_key = key.replace("env_", "").upper()
                    lines.append(f"- {display_key}: {value}")
        
        # Add project structure if available and enabled
        if self._include_project_structure and self._project_summary:
            lines.append("")
            lines.append("## Project Structure")
            lines.append("")
            lines.append(self._project_summary)
        
        return "\n".join(lines)
    
    def _get_os_display_name(self, os_type: str) -> str:
        """Get a human-readable OS name.
        
        Args:
            os_type: The os.name value (nt, posix, etc.)
            
        Returns:
            Human-readable OS name.
        """
        os_names = {
            "nt": "Windows",
            "posix": "Unix/Linux/macOS",
            "darwin": "macOS",
        }
        return os_names.get(os_type, os_type.capitalize() if os_type else "Unknown")
    
    def _get_shell_display_name(self, shell: str) -> str:
        """Get a human-readable shell name.
        
        Args:
            shell: The shell path or name.
            
        Returns:
            Human-readable shell name.
        """
        if not shell or shell == "unknown":
            return "Default Shell"
        
        # Extract shell name from path
        shell_lower = shell.lower()
        if "bash" in shell_lower:
            return "Bash"
        elif "zsh" in shell_lower:
            return "Zsh"
        elif "fish" in shell_lower:
            return "Fish"
        elif "powershell" in shell_lower or "pwsh" in shell_lower:
            return "PowerShell"
        elif "cmd" in shell_lower:
            return "Command Prompt (cmd)"
        
        # Return the last component of the path, capitalized
        name = shell.split("/")[-1].split("\\")[-1]
        return name.capitalize() if name else "Unknown Shell"
