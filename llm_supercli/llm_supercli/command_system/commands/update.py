"""Update command for llm_supercli."""
import asyncio
import subprocess
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..base import AsyncSlashCommand, CommandResult
from ...constants import APP_VERSION
from ...update_cache import UpdateCache
from ...update_checker import UpdateChecker
from ...update_notifier import get_update_notifier


class UpdateCommand(AsyncSlashCommand):
    """Check for and install updates."""
    
    name = "update"
    description = "Check for and install updates"
    aliases = ["upgrade"]
    usage = "[--check | --force]"
    examples = [
        "/update           # Check for updates and prompt to install",
        "/update --check   # Only check for updates, don't install",
        "/update --force   # Force update without confirmation",
    ]
    
    PACKAGE_NAME = "llm-supercli"
    
    def __init__(self) -> None:
        """Initialize the update command."""
        super().__init__()
        self.console = Console()
    
    async def run_async(self, args: str = "", **kwargs: Any) -> CommandResult:
        """
        Execute the update command.
        
        Bypasses cache and performs a fresh check against npm registry.
        Prompts user for confirmation before updating.
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 5.4
        """
        parsed = self.parse_args(args)
        check_only = parsed.get("check", False)
        force_update = parsed.get("force", False)
        
        # Display checking message
        self.console.print()
        self.console.print("[cyan]Checking for updates...[/cyan]")
        
        # Create cache and checker instances
        cache = UpdateCache()
        checker = UpdateChecker(cache)
        
        # Always bypass cache for manual update command (Requirement 5.4)
        result = await checker.check_for_update(
            current_version=APP_VERSION,
            bypass_cache=True
        )

        # Handle error case
        if result.error:
            return CommandResult.error(
                f"Failed to check for updates: {result.error}\n\n"
                "Troubleshooting:\n"
                "  • Check your internet connection\n"
                "  • Try again in a few minutes\n"
                "  • Manually check: npm view llm-supercli version"
            )
        
        # Display version information
        self._display_version_info(result)
        
        # If no update available
        if not result.update_available:
            return CommandResult.success(
                f"You're already on the latest version ({APP_VERSION})!"
            )
        
        # Check-only mode
        if check_only:
            return CommandResult.success(
                f"Update available: {result.current_version} → {result.latest_version}\n"
                f"Run `/update` to install the update."
            )
        
        # Prompt for confirmation (unless force mode)
        if not force_update:
            if not self._prompt_confirmation(result):
                return CommandResult.info("Update cancelled.")
        
        # Execute the update
        success = self._run_npm_update()
        
        if success:
            # Clear the cache so exit notification doesn't show stale info
            cache.clear_cache()
            
            # Clear any pending update notification so it doesn't show on exit
            notifier = get_update_notifier()
            notifier.clear_pending_notification()
            
            return CommandResult.success(
                f"✓ Successfully updated to version {result.latest_version}!\n\n"
                "Please restart the CLI to use the new version."
            )
        else:
            return CommandResult.error(
                "Failed to update. Please try manually:\n\n"
                f"  npm update -g {self.PACKAGE_NAME}\n\n"
                "Troubleshooting:\n"
                "  • You may need administrator/sudo privileges\n"
                "  • Try: sudo npm update -g llm-supercli\n"
                "  • Check npm permissions: npm config get prefix"
            )
    
    def _display_version_info(self, result) -> None:
        """Display current and latest version information."""
        if result.update_available and result.latest_version:
            text = Text()
            text.append("Current version: ", style="dim")
            text.append(result.current_version, style="yellow")
            text.append("\n")
            text.append("Latest version:  ", style="dim")
            text.append(result.latest_version, style="green bold")
            
            panel = Panel(
                text,
                title="[bold cyan]📦 Version Information[/bold cyan]",
                border_style="cyan",
                padding=(0, 1)
            )
            self.console.print(panel)
        else:
            self.console.print(f"[green]✓[/green] Current version: {result.current_version}")
    
    def _prompt_confirmation(self, result) -> bool:
        """
        Prompt user for confirmation before updating.
        
        Returns:
            True if user confirms, False otherwise.
        """
        self.console.print()
        self.console.print(
            f"[yellow]Do you want to update from "
            f"{result.current_version} to {result.latest_version}?[/yellow]"
        )
        
        try:
            response = input("Proceed with update? [y/N]: ").strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            self.console.print()
            return False
    
    def _run_npm_update(self) -> bool:
        """
        Execute npm update command.
        
        Returns:
            True if update succeeded, False otherwise.
            
        Requirements: 4.2, 4.3, 4.4
        """
        self.console.print()
        self.console.print("[cyan]Running npm update...[/cyan]")
        
        try:
            # Run npm update -g llm-supercli
            cmd = ["npm", "update", "-g", self.PACKAGE_NAME]
            
            # On Windows, we need shell=True for npm
            use_shell = sys.platform == "win32"
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=use_shell,
                timeout=120  # 2 minute timeout
            )
            
            if process.returncode == 0:
                return True
            else:
                # Log error output for debugging
                if process.stderr:
                    self.console.print(f"[dim]Error: {process.stderr}[/dim]")
                return False
                
        except subprocess.TimeoutExpired:
            self.console.print("[red]Update timed out after 2 minutes.[/red]")
            return False
        except FileNotFoundError:
            self.console.print("[red]npm not found. Please ensure npm is installed and in PATH.[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]Update failed: {e}[/red]")
            return False
