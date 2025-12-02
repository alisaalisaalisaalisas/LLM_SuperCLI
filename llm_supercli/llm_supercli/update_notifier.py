"""
Update notifier module for displaying update notifications.
Handles queuing and displaying styled update notifications to users.
"""
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .update_checker import UpdateResult


class UpdateNotifier:
    """
    Handles update notification display.
    
    Queues notifications to be shown after main CLI output completes,
    and formats them with styled messages including the update command.
    
    Requirements: 1.2, 1.5, 3.3, 3.4
    """
    
    PACKAGE_NAME: str = "llm-supercli"
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the update notifier.
        
        Args:
            console: Optional Rich Console instance. If not provided,
                     a new Console will be created.
        """
        self.console = console or Console()
        self._pending_notification: Optional[UpdateResult] = None
    
    def queue_notification(self, result: UpdateResult) -> None:
        """
        Queue a notification to be shown later.
        
        Only queues if an update is actually available.
        
        Args:
            result: UpdateResult from the update checker.
            
        Requirements: 3.3 - Queue notification for display after main output
        """
        if result.update_available and result.latest_version:
            self._pending_notification = result
    
    def show_pending_notification(self) -> None:
        """
        Display any pending update notification.
        
        Only shows if there's a pending notification and we should
        show notifications (TTY check, interactive mode).
        
        Requirements: 3.3 - Show notification after main CLI output completes
        """
        if self._pending_notification is None:
            return
        
        if not self.should_show_notification():
            self._pending_notification = None
            return
        
        message = self.format_notification(self._pending_notification)
        
        # Create a styled panel for the update notification
        panel = Panel(
            Text(message),
            title="[bold yellow]📦 Update Available[/bold yellow]",
            border_style="yellow",
            padding=(0, 1)
        )
        
        self.console.print()  # Add spacing before notification
        self.console.print(panel)
        
        # Clear the pending notification after showing
        self._pending_notification = None
    
    def format_notification(self, result: UpdateResult) -> str:
        """
        Format the update notification message.
        
        Creates a styled message containing current version, latest version,
        and the npm update command.
        
        Args:
            result: UpdateResult with version information.
            
        Returns:
            Formatted notification message string.
            
        Requirements: 1.2, 1.5 - Include current/latest versions and update command
        """
        if not result.update_available or not result.latest_version:
            return ""
        
        lines = [
            f"A new version of {self.PACKAGE_NAME} is available!",
            f"",
            f"  Current version: {result.current_version}",
            f"  Latest version:  {result.latest_version}",
            f"",
            f"Run the following command to update:",
            f"  npm update -g {self.PACKAGE_NAME}",
        ]
        
        return "\n".join(lines)
    
    def should_show_notification(self) -> bool:
        """
        Check if notifications should be shown.
        
        Returns False if:
        - stdout is not a TTY (piped output)
        - stdin is not a TTY (non-interactive mode)
        
        Returns:
            True if notifications should be shown, False otherwise.
            
        Requirements: 3.4 - Suppress notifications in pipe/non-interactive mode
        """
        # Check if stdout is a TTY (not piped)
        if not sys.stdout.isatty():
            return False
        
        # Check if stdin is a TTY (interactive mode)
        if not sys.stdin.isatty():
            return False
        
        return True
    
    def has_pending_notification(self) -> bool:
        """
        Check if there's a pending notification.
        
        Returns:
            True if there's a pending notification, False otherwise.
        """
        return self._pending_notification is not None
    
    def clear_pending_notification(self) -> None:
        """Clear any pending notification without showing it."""
        self._pending_notification = None
