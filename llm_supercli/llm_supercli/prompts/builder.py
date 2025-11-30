"""
PromptBuilder - Main orchestrator for assembling complete prompts.

Provides the PromptBuilder class that wires together SectionManager,
ModeManager, and ContextBuilder to generate complete system prompts.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from .config import PromptConfig
from .context import ContextBuilder
from .sections import SectionManager, SectionContext
from .modes.manager import ModeManager
from .modes.schema import ModeConfig
from .rules.loader import RulesLoader
from .tools.catalog import ToolCatalog, ToolDefinition


logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds complete system prompts from modular sections.
    
    The PromptBuilder is the main orchestrator that assembles complete prompts
    by coordinating the SectionManager, ModeManager, ContextBuilder, RulesLoader,
    and ToolCatalog components.
    
    Attributes:
        section_manager: Manages prompt section registration and rendering.
        mode_manager: Manages operational modes.
        context_builder: Builds environment and project context.
        rules_loader: Loads custom rules from file system.
        tool_catalog: Manages tool descriptions.
    
    Example:
        from llm_supercli.prompts import PromptBuilder, PromptConfig
        from llm_supercli.prompts.sections import SectionManager
        from llm_supercli.prompts.modes import ModeManager
        from llm_supercli.prompts.context import ContextBuilder
        
        builder = PromptBuilder(
            section_manager=SectionManager(),
            mode_manager=ModeManager(),
            context_builder=ContextBuilder(),
        )
        
        config = PromptConfig(mode="code")
        prompt = builder.build(config)
    """
    
    def __init__(
        self,
        section_manager: SectionManager,
        mode_manager: ModeManager,
        context_builder: ContextBuilder,
        rules_loader: Optional[RulesLoader] = None,
        tool_catalog: Optional[ToolCatalog] = None,
    ) -> None:
        """Initialize the PromptBuilder.
        
        Args:
            section_manager: The SectionManager for rendering sections.
            mode_manager: The ModeManager for mode configuration.
            context_builder: The ContextBuilder for environment context.
            rules_loader: Optional RulesLoader for custom rules.
            tool_catalog: Optional ToolCatalog for tool descriptions.
        """
        self._section_manager = section_manager
        self._mode_manager = mode_manager
        self._context_builder = context_builder
        self._rules_loader = rules_loader or RulesLoader()
        self._tool_catalog = tool_catalog or ToolCatalog()
    
    @property
    def section_manager(self) -> SectionManager:
        """Get the section manager."""
        return self._section_manager
    
    @property
    def mode_manager(self) -> ModeManager:
        """Get the mode manager."""
        return self._mode_manager
    
    @property
    def context_builder(self) -> ContextBuilder:
        """Get the context builder."""
        return self._context_builder
    
    @property
    def rules_loader(self) -> RulesLoader:
        """Get the rules loader."""
        return self._rules_loader
    
    @property
    def tool_catalog(self) -> ToolCatalog:
        """Get the tool catalog."""
        return self._tool_catalog
    
    def build(self, config: PromptConfig) -> str:
        """Build a complete system prompt.
        
        Assembles a complete system prompt by:
        1. Getting the mode configuration
        2. Building environment context
        3. Loading rules
        4. Filtering tools for the mode
        5. Rendering all sections
        
        Args:
            config: The PromptConfig specifying generation settings.
            
        Returns:
            The complete system prompt as a string.
        """
        # Get mode configuration
        mode = self._mode_manager.get(config.mode)
        
        # Build environment context
        env = self._context_builder.build_environment()
        cwd = Path(env["cwd"])
        
        # Load rules
        rules: list[str] = []
        rule_files = self._rules_loader.load(cwd)
        if rule_files:
            merged_rules = self._rules_loader.merge(rule_files)
            if merged_rules:
                rules.append(merged_rules)
        
        # Add custom instructions if provided
        if config.custom_instructions:
            rules.append(config.custom_instructions)
        
        # Get tools for the mode
        tools: list[ToolDefinition] = []
        mcp_tools: list[dict] = []
        
        if config.include_tools:
            tools = self._tool_catalog.filter_for_mode(mode)
        
        if config.include_mcp:
            # MCP tools are already in the catalog with group="mcp"
            mcp_tools = [
                {"name": t.name, "description": t.description, "inputSchema": t.parameters}
                for t in self._tool_catalog.tools
                if t.group == "mcp" and t.name not in self._tool_catalog.disabled_tools
            ]
        
        # Build section context
        context = SectionContext(
            mode=mode,
            cwd=env["cwd"],
            os_type=env["os_type"],
            shell=env["shell"],
            variables=dict(config.variables),
            tools=tools,
            mcp_tools=mcp_tools,
            rules=rules,
        )
        
        # Render all sections
        return self._section_manager.render_all(context)
    
    def build_messages(
        self,
        config: PromptConfig,
        conversation: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build complete message list with system prompt.
        
        Creates a message list suitable for sending to an LLM API,
        with the system prompt as the first message followed by
        the conversation history.
        
        Args:
            config: The PromptConfig specifying generation settings.
            conversation: List of conversation messages (user/assistant turns).
            
        Returns:
            List of messages with system prompt prepended.
        """
        system_prompt = self.build(config)
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(conversation)
        
        return messages
    
    def add_tool(self, tool: ToolDefinition) -> None:
        """Add a tool to the catalog.
        
        Args:
            tool: The tool definition to add.
        """
        self._tool_catalog.add_tool(tool)
    
    def add_mcp_tool(self, mcp_tool: dict[str, Any]) -> None:
        """Add an MCP tool to the catalog.
        
        Args:
            mcp_tool: MCP tool definition dictionary.
        """
        self._tool_catalog.add_mcp_tool(mcp_tool)
    
    def disable_tool(self, name: str) -> None:
        """Disable a tool by name.
        
        Args:
            name: The name of the tool to disable.
        """
        self._tool_catalog.disable_tool(name)
    
    def enable_tool(self, name: str) -> None:
        """Enable a previously disabled tool.
        
        Args:
            name: The name of the tool to enable.
        """
        self._tool_catalog.enable_tool(name)
