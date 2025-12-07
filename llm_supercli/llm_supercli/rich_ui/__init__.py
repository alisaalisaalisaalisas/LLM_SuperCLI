"""Rich UI components for llm_supercli."""
from .renderer import RichRenderer, get_renderer
from .input import InputHandler, get_input_handler
from .theme import ThemeManager, Theme, get_theme_manager
from .ascii import ASCIIArt
from .autocomplete import InteractiveCompleter, CommandCompleter, FileCompleter
from .interactive_input import SimpleInteractiveInput
from .prompt_input import PromptInput, InputPanel, get_prompt_input, get_input_panel
from .layout_manager import LayoutManager, LayoutConfig, get_layout_manager
from .status_bar import StatusBar, StatusBarData, get_status_bar
from .hints_bar import HintsBar, HintItem, HintsBarConfig, get_hints_bar
from .action_models import (
    ActionType,
    Action,
    ReadFilesAction,
    SearchAction,
    FileAction,
    StatusAction,
    ThinkingAction,
    DoneAction,
    ErrorAction,
    ToolCallAction,
    ToolResultAction,
    ToolWarningAction,
    ToolProgressAction,
)
from .tool_action_mapper import ToolActionMapper
from .reasoning import ReasoningDisplay, ReasoningChunk, get_reasoning_display, display_reasoning
from .skipped_tool_detector import (
    SkippedToolDetector,
    SkippedToolDetection,
    get_skipped_tool_detector,
    detect_skipped_tools,
)
from .streaming_progress import (
    StreamingProgressIndicator,
    StreamingProgressConfig,
    DEFAULT_THINKING_TIMEOUT,
)

__all__ = [
    'RichRenderer', 'get_renderer',
    'InputHandler', 'get_input_handler',
    'ThemeManager', 'Theme', 'get_theme_manager',
    'ASCIIArt',
    'InteractiveCompleter', 'CommandCompleter', 'FileCompleter',
    'SimpleInteractiveInput',
    'PromptInput', 'InputPanel', 'get_prompt_input', 'get_input_panel',
    # Layout management
    'LayoutManager', 'LayoutConfig', 'get_layout_manager',
    # Status bar
    'StatusBar', 'StatusBarData', 'get_status_bar',
    # Hints bar
    'HintsBar', 'HintItem', 'HintsBarConfig', 'get_hints_bar',
    # Action models
    'ActionType',
    'Action',
    'ReadFilesAction',
    'SearchAction',
    'FileAction',
    'StatusAction',
    'ThinkingAction',
    'DoneAction',
    'ErrorAction',
    'ToolCallAction',
    'ToolResultAction',
    'ToolWarningAction',
    'ToolProgressAction',
    # Tool action mapper
    'ToolActionMapper',
    # Reasoning display
    'ReasoningDisplay', 'ReasoningChunk', 'get_reasoning_display', 'display_reasoning',
    # Skipped tool detector
    'SkippedToolDetector', 'SkippedToolDetection', 'get_skipped_tool_detector', 'detect_skipped_tools',
    # Streaming progress indicator
    'StreamingProgressIndicator', 'StreamingProgressConfig', 'DEFAULT_THINKING_TIMEOUT',
]
