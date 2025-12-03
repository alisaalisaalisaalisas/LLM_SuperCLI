"""
Card styling configuration for the action cards system.

This module defines the visual styling for each action type,
including icons, title templates, border colors, and text styles.
"""
from dataclasses import dataclass
from typing import Dict

from .action_models import ActionType


@dataclass(frozen=True)
class CardStyle:
    """
    Visual styling configuration for an action card.
    
    Attributes:
        icon: Unicode icon or emoji to display in the card header
        title_template: Template string for the card title (may include {filename})
        border_color: Rich color name for the card border
        title_style: Rich style string for the title text
    """
    icon: str
    title_template: str
    border_color: str
    title_style: str


# Mapping of ActionType to CardStyle for consistent visual rendering
CARD_STYLES: Dict[ActionType, CardStyle] = {
    ActionType.READ_FILES: CardStyle(
        icon="📂",
        title_template="Read file(s)",
        border_color="cyan",
        title_style="bold cyan"
    ),
    ActionType.SEARCH: CardStyle(
        icon="🔍",
        title_template="Searched workspace",
        border_color="yellow",
        title_style="bold yellow"
    ),
    ActionType.CREATE_FILE: CardStyle(
        icon="🟢",
        title_template="Created {filename}",
        border_color="green",
        title_style="bold green"
    ),
    ActionType.UPDATE_FILE: CardStyle(
        icon="🟦",
        title_template="Updated {filename}",
        border_color="blue",
        title_style="bold blue"
    ),
    ActionType.THINKING: CardStyle(
        icon="⠋",
        title_template="Thinking...",
        border_color="dim",
        title_style="dim italic"
    ),
    ActionType.DONE: CardStyle(
        icon="✓",
        title_template="Done!",
        border_color="green",
        title_style="bold green"
    ),
    ActionType.STATUS: CardStyle(
        icon="📊",
        title_template="Status",
        border_color="dim",
        title_style="dim"
    ),
    ActionType.ERROR: CardStyle(
        icon="✗",
        title_template="Error",
        border_color="red",
        title_style="bold red"
    ),
}


def get_card_style(action_type: ActionType) -> CardStyle:
    """
    Get the CardStyle for a given ActionType.
    
    Args:
        action_type: The type of action to get styling for
        
    Returns:
        CardStyle for the action type, or ERROR style if not found
    """
    return CARD_STYLES.get(action_type, CARD_STYLES[ActionType.ERROR])
