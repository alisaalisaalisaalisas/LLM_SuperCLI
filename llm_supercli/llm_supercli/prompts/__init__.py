"""
Modular prompt system for llm_supercli.

This module provides a composable, extensible architecture for constructing
system prompts sent to LLM providers.
"""

from .sections import SectionManager, PromptSection, SectionContext
from .builder import PromptBuilder
from .config import PromptConfig
from .context import ContextBuilder, VariableError, interpolate

__all__ = [
    "SectionManager",
    "PromptSection",
    "SectionContext",
    "PromptBuilder",
    "PromptConfig",
    "ContextBuilder",
    "VariableError",
    "interpolate",
]
