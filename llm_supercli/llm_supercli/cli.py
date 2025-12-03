"""
Main CLI loop for llm_supercli.
Handles the interactive command loop and message processing.
"""
import asyncio
import json
import os
import re
import sys
from typing import Any, Optional, Tuple

from .config import get_config
from .rich_ui import RichRenderer, InputHandler, get_theme_manager
from .rich_ui.prompt_input import PromptInput
from .rich_ui.message_state import ToolCallRecord
from .rich_ui.tool_action_mapper import ToolActionMapper
from .rich_ui.layout_manager import LayoutManager, get_layout_manager
from .rich_ui.status_bar import StatusBar, StatusBarData, get_status_bar
from .rich_ui.hints_bar import HintsBar, get_hints_bar
from .command_system import CommandParser, get_command_registry
from .history import get_session_store
from .llm import get_provider_registry
from .mcp import get_mcp_manager
from .io_handlers import BashRunner, FileLoader
from .prompts import PromptBuilder, PromptConfig, SectionManager, ContextBuilder
from .prompts.sections import (
    RoleSection,
    CapabilitiesSection,
    ToolsSection,
    RulesSection,
    EnvironmentSection,
    FormattingSection,
)
from .prompts.modes import ModeManager
from .prompts.rules import RulesLoader
from .prompts.tools import (
    ToolCatalog,
    ToolDefinition,
    ToolExecutor,
    get_builtin_tools,
    ToolParser,
    PythonStyleParser,
    XMLStyleParser,
    ParsedToolCall,
)


class CLI:
    """
    Main CLI class for llm_supercli.
    
    Manages the interactive command loop, processes user input,
    and coordinates between all components.
    
    Requirements: 9.1 - Integration with LayoutManager for responsive UI
    """
    
    def __init__(self) -> None:
        """Initialize the CLI with proper component initialization order.
        
        Initialization order (Requirements: All):
        1. Configuration - load settings first
        2. LayoutManager - set up responsive layout infrastructure
        3. Renderer - UI rendering with layout awareness
        4. StatusBar - fixed footer component
        5. HintsBar - help hints display
        6. Input - user input handling
        7. Other components - commands, sessions, providers, etc.
        """
        # 1. Configuration - load settings first
        self._config = get_config()
        
        # 2. LayoutManager - set up responsive layout infrastructure
        # Requirements: 9.1, 9.2, 9.3 - Terminal responsiveness
        self._layout_manager = get_layout_manager()
        
        # 3. Renderer - UI rendering with layout awareness
        self._renderer = RichRenderer()
        
        # 4. StatusBar - fixed footer component
        # Requirements: 1.1, 1.2, 1.3, 1.4 - Fixed Status Bar Layout
        self._status_bar = get_status_bar(console=self._renderer.console)
        self._status_bar.set_layout_manager(self._layout_manager)
        
        # 5. HintsBar - help hints display
        # Requirements: 3.1, 3.2 - Help Hints Bar
        self._hints_bar = get_hints_bar(console=self._renderer.console)
        
        # 6. Input and command handling
        self._parser = CommandParser()
        self._commands = get_command_registry()
        self._input = PromptInput()
        self._input.set_commands(self._commands.list_commands())
        
        # 7. Other components
        self._sessions = get_session_store()
        self._providers = get_provider_registry()
        self._mcp = get_mcp_manager()
        self._bash = BashRunner()
        self._files = FileLoader()
        self._tools = ToolExecutor()
        self._running = False
        self._current_mode: str = "code"  # Default mode
        
        # Initialize the new prompt system
        self._prompt_builder = self._create_prompt_builder()
        
        # Initialize ToolActionMapper for action cards integration
        # Requirements: 8.1, 8.2 - Automatically generate action cards for tool execution
        self._tool_action_mapper = ToolActionMapper(
            action_renderer=self._renderer.action_renderer,
            working_dir=os.getcwd()
        )
    
    def _create_prompt_builder(self) -> PromptBuilder:
        """Create and configure the PromptBuilder with default sections and modes.
        
        Returns:
            A configured PromptBuilder instance.
        """
        # Create section manager and register default sections
        section_manager = SectionManager()
        section_manager.register(RoleSection())
        section_manager.register(CapabilitiesSection())
        section_manager.register(ToolsSection())
        section_manager.register(RulesSection())
        section_manager.register(EnvironmentSection())
        section_manager.register(FormattingSection())
        
        # Create mode manager (loads built-in modes automatically)
        mode_manager = ModeManager()
        
        # Create context builder
        context_builder = ContextBuilder()
        
        # Create rules loader
        rules_loader = RulesLoader()
        
        # Create tool catalog and populate with built-in tools
        tool_catalog = ToolCatalog()
        for tool in get_builtin_tools():
            tool_catalog.add_tool(tool)
        
        # Create and return the prompt builder
        return PromptBuilder(
            section_manager=section_manager,
            mode_manager=mode_manager,
            context_builder=context_builder,
            rules_loader=rules_loader,
            tool_catalog=tool_catalog,
        )
    
    def _parse_thinking(self, content: str) -> Tuple[str, str]:
        """
        Parse <think></think> tags from content.
        
        Returns:
            Tuple of (main_content, thinking_content)
        """
        thinking = ""
        main_content = content
        
        # Extract thinking blocks
        think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
        matches = think_pattern.findall(content)
        
        if matches:
            thinking = "\n".join(matches)
            main_content = think_pattern.sub('', content).strip()
        
        return main_content, thinking
    
    def run(self) -> None:
        """Run the CLI main loop with integrated layout management.
        
        Requirements:
        - 9.1: Use LayoutManager for responsive layout
        - 1.1, 1.2, 1.3, 1.4: Status bar integration
        - 3.1, 3.2: Hints bar integration
        """
        self._running = True
        
        # Initialize status bar with current state
        # Requirements: 1.1, 1.3, 1.4 - Status bar with session info
        self._update_status_bar()
        
        # Show welcome banner (uses LayoutManager internally)
        self._renderer.print_welcome()
        self._ensure_session()
        
        # Print hints bar after welcome
        # Requirements: 3.1 - Display hints bar
        if self._layout_manager.should_show_element("hints_bar"):
            self._hints_bar.print(centered=True)
        
        self._renderer.print()
        
        while self._running:
            try:
                # Update status bar before each prompt
                # Requirements: 1.3, 1.4 - Real-time updates
                self._update_status_bar()
                
                user_input = self._input.get_input(
                    prompt=self._get_prompt()
                )
                
                if not user_input.strip():
                    continue
                
                self._process_input_sync(user_input)
                
            except KeyboardInterrupt:
                self._renderer.print("\n[dim]Use /quit to exit[/dim]")
            except EOFError:
                self._running = False
            except Exception as e:
                self._renderer.print_error(f"Unexpected error: {e}")
    
    def _process_input_sync(self, user_input: str) -> None:
        """Process user input synchronously, only using async when necessary."""
        parsed = self._parser.parse(user_input)
        
        if parsed.type == "command":
            self._handle_command_sync(parsed.command, parsed.args)
        elif parsed.type == "shell":
            asyncio.run(self._handle_shell(parsed.shell_command))
        elif parsed.type == "message":
            asyncio.run(self._handle_message(parsed.message, parsed.files))
        elif parsed.type == "empty":
            pass
    
    def _handle_command_sync(self, command: str, args: str) -> None:
        """Handle a slash command synchronously.
        
        Requirements: 1.3 - Update status bar when provider or mode changes
        """
        result = self._commands.execute(
            command,
            args,
            session=self._sessions.current_session,
            config=self._config,
            renderer=self._renderer
        )
        
        if result.should_exit:
            self._running = False
        
        if result.should_clear:
            self._renderer.clear()
            self._renderer.print_welcome()
            # Update status bar after clear
            self._update_status_bar()
            return
        
        if result.message:
            if result.is_error:
                self._renderer.print_error(result.message)
            else:
                self._renderer.print_markdown(result.message)
        
        # Update status bar after command execution (mode/provider may have changed)
        # Requirements: 1.3 - Immediately update when provider or mode changes
        self._update_status_bar()
    
    def _update_status_bar(self) -> None:
        """Update the status bar with current session state.
        
        Requirements: 1.1, 1.3, 1.4 - Status bar updates
        """
        session = self._sessions.current_session
        
        # Get session name and branch
        session_name = "new"
        branch = "main"
        if session:
            session_name = getattr(session, 'name', 'new') or 'new'
            # Try to get git branch
            try:
                git_dir = os.path.join(os.getcwd(), '.git')
                if os.path.isdir(git_dir):
                    head_file = os.path.join(git_dir, 'HEAD')
                    if os.path.isfile(head_file):
                        with open(head_file, 'r') as f:
                            ref = f.read().strip()
                            if ref.startswith('ref: refs/heads/'):
                                branch = ref[16:]
            except Exception:
                pass
        
        # Get mode info
        mode_slug = self.current_mode
        mode_config = self._prompt_builder.mode_manager.get(mode_slug)
        
        # Get provider info
        provider = self._config.llm.provider
        model = self._config.llm.model
        free_providers = ["qwen", "gemini", "ollama"]
        is_free = provider in free_providers
        
        # Calculate context percentage (estimate based on session messages)
        context_percent = 0
        if session:
            messages = session.get_context() if hasattr(session, 'get_context') else []
            # Rough estimate: assume 4096 token context, 4 chars per token
            total_chars = sum(len(str(m.get('content', ''))) for m in messages)
            estimated_tokens = total_chars // 4
            max_tokens = self._config.llm.max_tokens or 4096
            context_percent = min(100, int((estimated_tokens / max_tokens) * 100))
        
        # Update status bar
        self._status_bar.update(
            session_name=session_name,
            branch=branch,
            mode_icon=mode_config.icon,
            mode_name=mode_config.name,
            provider=provider,
            model=model,
            is_free=is_free,
            context_percent=context_percent
        )
    
    def _get_prompt(self) -> str:
        """Get the input prompt string with model info and current mode.
        
        Requirements: 9.2 - Compact mode support for narrow terminals
        """
        cwd = os.getcwd()
        # Show shortened path in prompt
        home = os.path.expanduser('~')
        if cwd.startswith(home):
            short_path = '~' + cwd[len(home):].replace('\\', '/')
        else:
            short_path = cwd.replace('\\', '/')
        # Keep only last 2 parts if path is long
        parts = short_path.split('/')
        if len(parts) > 3:
            short_path = '.../' + '/'.join(parts[-2:])
        
        # In compact mode, use even shorter path
        if self._layout_manager.is_compact_mode and len(short_path) > 20:
            short_path = self._layout_manager.truncate_text(short_path, 20)
        
        # Print model info above prompt with current mode
        provider = self._config.llm.provider.capitalize()
        model = self._config.llm.model
        # Only show Free for OAuth providers
        free_providers = ["qwen", "gemini", "ollama"]
        if self._config.llm.provider in free_providers:
            tier = " | [magenta]Free[/magenta]"
        else:
            tier = ""
        
        # Get current mode info
        mode_slug = self.current_mode
        mode_config = self._prompt_builder.mode_manager.get(mode_slug)
        
        # Get context percentage for display
        context_percent = self._status_bar.data.context_percent
        context_style = "green" if context_percent < 50 else "yellow" if context_percent < 80 else "red"
        context_display = f" | [{context_style}]{context_percent}%[/{context_style}]"
        
        # In compact mode, show abbreviated info
        if self._layout_manager.is_compact_mode:
            # Abbreviated display for narrow terminals
            mode_display = f" | [yellow]{mode_config.icon}[/yellow]"
            self._renderer.print(f"[cyan]{provider[:4]}[/cyan]/[green]{model[:10]}[/green]{mode_display}{context_display}")
        else:
            mode_display = f" | [yellow]{mode_config.icon} {mode_config.name}[/yellow]"
            self._renderer.print(f"[cyan]{provider}[/cyan] / [green]{model}[/green]{tier}{mode_display}{context_display}")
        
        return f"[{short_path}] > "
    
    def _ensure_session(self) -> None:
        """Ensure there's an active session."""
        if not self._sessions.current_session:
            self._sessions.create_session(
                provider=self._config.llm.provider,
                model=self._config.llm.model,
                system_prompt=self._config.llm.system_prompt
            )
    
    async def _process_input(self, user_input: str) -> None:
        """Process user input."""
        parsed = self._parser.parse(user_input)
        
        if parsed.type == "command":
            await self._handle_command(parsed.command, parsed.args)
        elif parsed.type == "shell":
            await self._handle_shell(parsed.shell_command)
        elif parsed.type == "message":
            await self._handle_message(parsed.message, parsed.files)
        elif parsed.type == "empty":
            pass
    
    async def _handle_command(self, command: str, args: str) -> None:
        """Handle a slash command."""
        result = await self._commands.execute_async(
            command,
            args,
            session=self._sessions.current_session,
            config=self._config,
            renderer=self._renderer
        )
        
        if result.should_exit:
            self._running = False
        
        if result.should_clear:
            self._renderer.clear()
            self._renderer.print_welcome()
            return
        
        if result.message:
            if result.is_error:
                self._renderer.print_error(result.message)
            else:
                self._renderer.print_markdown(result.message)
    
    async def _handle_shell(self, command: str) -> None:
        """Handle a shell command."""
        self._renderer.print(f"[dim]$ {command}[/dim]")
        
        result = await self._bash.run_async(command)
        
        if result.success:
            if result.stdout:
                self._renderer.print_code(result.stdout, language="bash", line_numbers=False)
        else:
            self._renderer.print_error(result.stderr or f"Command failed with code {result.return_code}")
    
    async def _handle_message(self, message: str, files: list) -> None:
        """Handle a chat message."""
        if files:
            loaded_files = self._files.load_multiple(files)
            file_contents = []
            
            for f in loaded_files:
                if f.success:
                    file_contents.append(f.format_for_prompt())
                else:
                    self._renderer.print_warning(f.error or f"Failed to load {f.path}")
            
            if file_contents:
                message = message + "\n\n" + "\n\n".join(file_contents)
        
        session = self._sessions.current_session
        if not session:
            self._ensure_session()
            session = self._sessions.current_session
        
        session.add_message("user", message)
        self._renderer.print_message(message, role="user")
        
        try:
            provider = self._providers.get(self._config.llm.provider)
            if not provider:
                self._renderer.print_error(f"Provider not found: {self._config.llm.provider}")
                return
            
            # Providers that don't require API key (local or OAuth-based)
            no_key_providers = ["ollama", "gemini", "qwen"]
            if not provider.api_key and self._config.llm.provider not in no_key_providers:
                self._renderer.print_error(
                    f"No API key set for {self._config.llm.provider}. "
                    f"Set environment variable or use /settings."
                )
                return
            
            # Update tool executor working directory
            self._tools.working_dir = os.getcwd()
            
            # Start session tracking for status footer
            # Requirements: 8.1 - Add status footer rendering after response completion
            self._tool_action_mapper.start_session()
            
            # Build context with system message including current directory
            context = self._build_context_with_tools(session)
            
            # Determine if provider is free-tier for status footer
            free_providers = ["qwen", "gemini", "ollama"]
            is_free_tier = self._config.llm.provider in free_providers
            
            # Providers without native tool support - use simple streaming
            # Note: Gemini supports native tool calling via functionCall, so it uses _get_response_with_tools
            no_tool_providers = ["qwen", "groq"]
            if self._config.llm.provider in no_tool_providers:
                await self._get_streaming_response(provider, context, session)
            else:
                await self._get_response_with_tools(provider, context, session)
            
            # Status footer removed - time/free info now shown in prompt line
            
            # Update status bar after response (context may have changed)
            # Requirements: 1.4 - Update context percentage in real-time
            self._update_status_bar()
                
        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            self._renderer.print_error(f"LLM Error: {error_msg}")
    
    def _build_context_with_tools(self, session) -> list:
        """Build message context with system prompt using the new PromptBuilder.
        
        Uses the modular prompt system to generate the system prompt based on
        the current mode and configuration.
        
        Args:
            session: The current session containing conversation history.
            
        Returns:
            List of messages with system prompt prepended.
        """
        # Get mode from session metadata or use default
        mode = self._get_session_mode(session)
        
        # Build prompt configuration
        config = PromptConfig(
            mode=mode,
            include_tools=True,
            include_mcp=self._config.mcp.enabled,
        )
        
        # Get conversation history (excluding system messages)
        context = session.get_context()
        conversation = [msg for msg in context if msg.get("role") != "system"]
        
        # Use PromptBuilder to generate messages with system prompt
        return self._prompt_builder.build_messages(config, conversation)
    
    def _get_session_mode(self, session) -> str:
        """Get the current mode from session metadata.
        
        Args:
            session: The current session.
            
        Returns:
            The mode slug from session metadata, or default "code".
        """
        if session and hasattr(session, "metadata") and session.metadata:
            return session.metadata.get("mode", self._current_mode)
        return self._current_mode
    
    def _set_session_mode(self, session, mode: str) -> None:
        """Set the mode in session metadata.
        
        Args:
            session: The current session.
            mode: The mode slug to set.
        """
        if session:
            if not hasattr(session, "metadata") or session.metadata is None:
                session.metadata = {}
            session.metadata["mode"] = mode
            self._sessions.save_session(session)
        self._current_mode = mode
    
    @property
    def current_mode(self) -> str:
        """Get the current operational mode."""
        session = self._sessions.current_session
        return self._get_session_mode(session)
    
    @current_mode.setter
    def current_mode(self, mode: str) -> None:
        """Set the current operational mode.
        
        Args:
            mode: The mode slug to switch to.
        """
        # Validate mode exists (will fall back to default if not found)
        self._prompt_builder.mode_manager.get(mode)
        session = self._sessions.current_session
        self._set_session_mode(session, mode)
    
    @property
    def prompt_builder(self) -> PromptBuilder:
        """Get the prompt builder instance."""
        return self._prompt_builder
    
    @property
    def layout_manager(self) -> LayoutManager:
        """Get the layout manager instance.
        
        Requirements: 9.1 - Access to layout management
        """
        return self._layout_manager
    
    @property
    def status_bar(self) -> StatusBar:
        """Get the status bar instance.
        
        Requirements: 1.1 - Access to status bar
        """
        return self._status_bar
    
    @property
    def hints_bar(self) -> HintsBar:
        """Get the hints bar instance.
        
        Requirements: 3.1 - Access to hints bar
        """
        return self._hints_bar
    
    async def _stream_response(self, provider, context: list, session) -> None:
        """Stream response from LLM with live reasoning display."""
        self._renderer.start_spinner("Thinking...")
        
        try:
            first_chunk = True
            self._renderer.start_live_reasoning()
            
            async for chunk in provider.chat_stream(
                messages=context,
                model=self._config.llm.model,
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens
            ):
                if first_chunk:
                    self._renderer.stop_spinner()
                    first_chunk = False
                
                # Update live display with chunk
                self._renderer.update_live_stream(chunk.content)
            
            # Stop live stream and get final content
            response_content, reasoning_content = self._renderer.stop_live_stream()
            
            # Display final reasoning box if any (only if not already printed)
            if reasoning_content and not self._renderer.was_reasoning_printed():
                self._renderer.print_reasoning(reasoning_content)
            
            # Display response only if not already printed during streaming
            if response_content and not self._renderer.was_response_printed():
                self._renderer.print_message(response_content, role="assistant")
            
            # Save to session
            full_response = response_content
            if full_response:
                tokens = len(full_response) // 4
                session.add_message("assistant", full_response, tokens=tokens)
                self._sessions.save_session(session)
                
        finally:
            self._renderer.stop_spinner()
    
    async def _get_response(self, provider, context: list, session) -> None:
        """Get complete response from LLM."""
        live = self._renderer.start_spinner("Thinking...")
        
        try:
            response = await provider.chat(
                messages=context,
                model=self._config.llm.model,
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens
            )
            
            self._renderer.stop_spinner()
            
            # Parse and display thinking/reasoning separately
            main_content, thinking = self._parse_thinking(response.content)
            
            if thinking:
                self._renderer.print_reasoning(thinking)
            
            if main_content:
                self._renderer.print_message(main_content, role="assistant")
            
            session.add_message(
                "assistant",
                response.content,
                tokens=response.total_tokens,
                cost=response.cost
            )
            self._sessions.save_session(session)
            
            if self._config.ui.show_token_count:
                tokens = response.input_tokens + response.output_tokens
                self._renderer.print(f"[dim]{tokens} tokens[/dim]")
                
        finally:
            self._renderer.stop_spinner()
    
    async def _get_streaming_response(self, provider, context: list, session) -> None:
        """Streaming response with text-based tool parsing for providers without native tool support.
        
        Uses the modular ToolParser to parse tool calls from model output in multiple
        formats (Python-style, XML-style). Provides consistent visual feedback for
        tool execution regardless of the format used.
        
        Requirements: 1.1, 1.4, 4.1, 4.2, 4.3, 4.4
        """
        import re
        messages = context.copy()
        max_iterations = 15  # Increased to allow complex multi-step tasks
        
        # Initialize the tool parser with registered format parsers
        tool_parser = ToolParser()
        tool_parser.register(PythonStyleParser())
        tool_parser.register(XMLStyleParser())
        
        # Track executed tool calls to prevent duplicates
        executed_calls: set[str] = set()
        
        # Track displayed content to prevent duplication
        displayed_content: set[str] = set()
        
        for iteration in range(max_iterations):
            # Accumulate raw response without live display to avoid duplication
            raw_response = ""
            self._renderer.start_spinner("Thinking...")
            
            try:
                async for chunk in provider.chat_stream(
                    messages=messages,
                    model=self._config.llm.model,
                    temperature=self._config.llm.temperature,
                    max_tokens=self._config.llm.max_tokens
                ):
                    raw_response += chunk.content
            finally:
                self._renderer.stop_spinner()
            
            # Parse think tags from raw response
            from .rich_ui.content_parser import parse_think_tags
            parsed = parse_think_tags(raw_response)
            response_content = parsed.response
            reasoning_content = parsed.reasoning
            
            # Parse tool calls using the modular ToolParser
            # Check both response content AND reasoning content (model sometimes puts tools in thinking)
            content = response_content or ""
            all_content = content + "\n" + (reasoning_content or "")
            parsed_calls = tool_parser.parse(all_content)
            
            # Filter out duplicate tool calls (same tool + same args)
            unique_calls = []
            for call in parsed_calls:
                call_key = f"{call.name}:{str(sorted(call.arguments.items()))}"
                if call_key not in executed_calls:
                    unique_calls.append(call)
                    executed_calls.add(call_key)
            
            # Strip tool call syntax from displayed content
            # Remove XML-style: <tool_name(args)>...</tool_name> and <tool_name(args)>
            display_content = re.sub(r'<\w+\([^)]*\)>[^<]*</\w+>', '', content)
            display_content = re.sub(r'<\w+\([^)]*\)>', '', display_content)
            # Remove Python-style: tool_name(args) - including inside code blocks
            display_content = re.sub(r'\b(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)\s*\([^)]*\)', '', display_content)
            # Remove malformed XML closing tags (Qwen outputs these)
            display_content = re.sub(r'<\s*/\s*(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)\s*>', '', display_content)
            # Remove standalone closing/opening tags
            display_content = re.sub(r'</(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)>', '', display_content)
            display_content = re.sub(r'<(read_file|write_file|list_directory|create_directory|run_command|get_current_directory)>', '', display_content)
            # Remove empty code blocks that contained only tool calls
            display_content = re.sub(r'```\s*```', '', display_content)
            display_content = re.sub(r'```\s*\n?\s*```', '', display_content)
            # Remove lines that are just "< " artifacts
            display_content = re.sub(r'^\s*<\s*$', '', display_content, flags=re.MULTILINE)
            # Remove "python" artifacts from tool call parsing
            display_content = re.sub(r'\bpython\b(?=\s*python|\s*$)', '', display_content)
            # Remove Rich panel border characters that model might output
            display_content = re.sub(r'[┏┓┗┛┃━]+', '', display_content)
            display_content = display_content.strip()
            
            # Deduplicate repeated content (model sometimes outputs same text multiple times)
            # Split into sentences and remove duplicates while preserving order
            lines = display_content.split('\n')
            seen_lines = set()
            unique_lines = []
            for line in lines:
                line_key = line.strip().lower()
                if line_key and line_key not in seen_lines:
                    seen_lines.add(line_key)
                    unique_lines.append(line)
                elif not line_key:  # Keep empty lines for formatting
                    unique_lines.append(line)
            display_content = '\n'.join(unique_lines)
            
            # Execute parsed tool calls FIRST with consistent visual feedback
            tool_results = []
            num_calls = len(unique_calls)
            
            # Add visual header if multiple tool calls
            if num_calls > 1:
                self._renderer.print_tool_section_header(num_calls)
            
            for i, call in enumerate(unique_calls):
                result_str = self._execute_tool_call(call)
                tool_results.append(result_str)
                
                # Add visual separator between multiple tool calls
                if num_calls > 1 and i < num_calls - 1:
                    self._renderer.print_tool_separator()
            
            # Filter out invalid tool calls (tools that returned errors)
            valid_results = [r for r in tool_results if "Error: Unknown tool" not in r]
            
            if valid_results:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": "Tool results:\n" + "\n".join(valid_results) + "\n\nBased on these results, provide your analysis now. Do NOT say you already provided an analysis - you have not shown any analysis to the user yet. Present your findings clearly."
                })
                continue
            
            # No valid tool calls - check if we have a response to show
            # Clean any remaining think tags and tool syntax from response
            final_content = display_content if display_content else ""
            final_content = re.sub(r'</?think>?', '', final_content).strip()
            # Also clean any remaining tool-like patterns
            final_content = re.sub(r'<[^>]*\([^)]*\)[^>]*>', '', final_content).strip()
            # Clean malformed closing tags
            final_content = re.sub(r'<\s*/\s*\w+\s*>', '', final_content).strip()
            final_content = re.sub(r'^\s*<\s*$', '', final_content, flags=re.MULTILINE).strip()
            
            # If response is empty but we have reasoning, use reasoning as the response
            # (Qwen sometimes puts the actual response in reasoning_content)
            # But only if reasoning wasn't already printed during streaming
            if not final_content and reasoning_content and not self._renderer.was_reasoning_printed():
                final_content = reasoning_content.strip()
                final_content = re.sub(r'</?think>?', '', final_content).strip()
                final_content = re.sub(r'<[^>]*\([^)]*\)[^>]*>', '', final_content).strip()
                final_content = re.sub(r'<\s*/\s*\w+\s*>', '', final_content).strip()
                final_content = re.sub(r'^\s*<\s*$', '', final_content, flags=re.MULTILINE).strip()
            
            # Check for empty or useless responses (just punctuation, very short, filenames only, etc.)
            stripped_content = final_content.strip() if final_content else ""
            is_useless_response = (
                not final_content or 
                len(stripped_content) < 20 or  # Increased threshold - real responses are longer
                re.match(r'^[\s\.\,\!\?\-\_\*]+$', stripped_content) or
                # Just a filename or path (no actual content)
                re.match(r'^[\w\-\_\.\/\\]+\.(py|txt|md|json|toml|yaml|yml|js|ts|html|css)$', stripped_content, re.IGNORECASE) or
                # Just a single word or identifier
                re.match(r'^\w+$', stripped_content)
            )
            
            # If still no useful content after tool calls, prompt for a real response
            if is_useless_response and iteration >= 0:
                # Limit summary prompts to avoid infinite loops
                if iteration >= max_iterations - 1:
                    self._renderer.print_warning("Model did not provide a useful response.")
                    break
                # If we executed tools but got no response, ask for one
                if tool_results:
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user", 
                        "content": "Now provide a brief response based on what you found. Be concise."
                    })
                    continue
                # No tools and useless content - prompt for actual work
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": "Please provide a substantive response. If you need to analyze something, use the available tools (list_directory, read_file, etc.)."
                })
                continue
            
            # Check if model said it would do something but didn't follow through
            # Common patterns: "Let me...", "I'll...", "I will...", "First, I'll..."
            incomplete_patterns = [
                r"(?i)\blet me\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                r"(?i)\bi'?ll\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                r"(?i)\bi will\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                r"(?i)\bfirst,?\s+i'?ll\b",
                r"(?i)\blet's\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
            ]
            
            # Check if model claims it already answered but response is too short
            # (hallucinating that it provided analysis when it didn't)
            hallucination_patterns = [
                r"(?i)\bi'?ve (already|just) (completed|provided|given|done|finished)",
                r"(?i)\b(already|just) (completed|provided|given|done|finished).*analysis",
                r"(?i)\bbased on my (previous|earlier) (analysis|exploration|review)",
                r"(?i)\bas (i|I) (mentioned|said|explained|described) (earlier|before|above)",
            ]
            
            is_incomplete = False
            is_hallucinating = False
            
            if final_content and iteration < max_iterations - 1:
                for pattern in incomplete_patterns:
                    if re.search(pattern, final_content):
                        is_incomplete = True
                        break
                
                # Check for hallucination - model claims it answered but response is short
                if len(final_content) < 500:  # Real analysis should be longer
                    for pattern in hallucination_patterns:
                        if re.search(pattern, final_content):
                            is_hallucinating = True
                            break
            
            # If model said it would do something but didn't call tools, prompt to continue
            if is_incomplete and not tool_results:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": "Please proceed with the action you mentioned. Use the available tools (list_directory, read_file, etc.) to complete the task."
                })
                continue
            
            # If model is hallucinating that it already answered, force it to actually answer
            if is_hallucinating:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": "You have NOT provided any analysis yet - the user has not seen any analysis from you. Please provide your actual detailed analysis NOW based on the files you read."
                })
                continue
            
            # Print final response panel only if not already printed during streaming
            if final_content and not self._renderer.was_response_printed():
                self._renderer.print_message(final_content, role="assistant")
            if final_content:
                session.add_message("assistant", final_content)
            break
    
    def _execute_tool_call(self, call: ParsedToolCall) -> str:
        """Execute a parsed tool call with action cards visual feedback.
        
        Uses ToolActionMapper to generate action cards for tool calls,
        providing rich visual feedback for file operations, searches, etc.
        
        Args:
            call: The parsed tool call to execute.
            
        Returns:
            A string describing the result for inclusion in the conversation.
            
        Requirements: 8.1, 8.2 - Automatically generate action cards for tool execution
        """
        tool_name = call.name
        arguments = call.arguments
        
        # Valid tool names - skip unknown tools silently to avoid noise
        valid_tools = {
            "read_file", "write_file", "list_directory", 
            "create_directory", "run_command", "get_current_directory"
        }
        
        # Normalize arguments - handle both positional (arg0, arg1) and named arguments
        normalized_args = self._normalize_tool_arguments(tool_name, arguments)
        
        # Update tool action mapper working directory
        self._tool_action_mapper.working_dir = self._tools.working_dir
        
        # Skip invalid/hallucinated tool names
        if tool_name not in valid_tools:
            return f"Error: Unknown tool '{tool_name}'"
        
        # Capture state before execution for accurate create/update detection
        # Requirements: 8.1 - Detect file creation vs update based on file existence
        pre_state = self._tool_action_mapper.render_tool_action_before(
            tool_name, normalized_args
        )
        
        try:
            result = self._tools.execute(tool_name, normalized_args)
            
            # Check if the tool executor returned an error
            success = not result.startswith("Error:")
            
            # Render action card after execution with captured state
            # Requirements: 8.1, 8.2 - Generate appropriate action cards
            self._tool_action_mapper.render_tool_action_after(
                pre_state, result=result, success=success
            )
            
            return f"{tool_name}: {result}"
            
        except Exception as e:
            # Render action card for failed execution
            self._tool_action_mapper.render_tool_action_after(
                pre_state, result=str(e), success=False
            )
            return f"{tool_name} error: {e}"
    
    def _normalize_tool_arguments(self, tool_name: str, arguments: dict) -> dict:
        """Normalize tool arguments from positional to named format.
        
        Converts positional arguments (arg0, arg1, etc.) to the named
        arguments expected by the ToolExecutor.
        
        Args:
            tool_name: The name of the tool being called.
            arguments: The parsed arguments dictionary.
            
        Returns:
            Normalized arguments dictionary with proper parameter names.
        """
        # If arguments already have proper names, return as-is
        if not any(key.startswith('arg') and key[3:].isdigit() for key in arguments):
            return arguments
        
        # Map positional arguments to named parameters based on tool
        param_mappings = {
            "read_file": ["path"],
            "write_file": ["path", "content"],
            "list_directory": ["path"],
            "create_directory": ["path"],
            "run_command": ["command"],
            "get_current_directory": [],
        }
        
        param_names = param_mappings.get(tool_name, [])
        normalized = {}
        
        # Copy over any already-named arguments
        for key, value in arguments.items():
            if not (key.startswith('arg') and key[3:].isdigit()):
                normalized[key] = value
        
        # Map positional arguments to named parameters
        for i, param_name in enumerate(param_names):
            arg_key = f'arg{i}'
            if arg_key in arguments and param_name not in normalized:
                normalized[param_name] = arguments[arg_key]
        
        return normalized
    
    def _format_args_preview(self, arguments: dict) -> str:
        """Format arguments for display in tool execution header.
        
        Args:
            arguments: The tool arguments dictionary.
            
        Returns:
            Formatted string for display, or empty string if no args.
        """
        if not arguments:
            return ""
        
        # Show path or command prominently
        if "path" in arguments:
            return f": {arguments['path']}"
        elif "command" in arguments:
            cmd = arguments['command']
            if len(cmd) > 50:
                cmd = cmd[:47] + "..."
            return f": {cmd}"
        
        # For other arguments, show a brief summary
        preview_parts = []
        for key, value in list(arguments.items())[:2]:
            str_val = str(value)
            if len(str_val) > 30:
                str_val = str_val[:27] + "..."
            preview_parts.append(f"{key}={str_val}")
        
        if preview_parts:
            return f"({', '.join(preview_parts)})"
        return ""
    
    def _truncate_result(self, result: str, max_length: int = 150) -> str:
        """Truncate a result string for preview display.
        
        Args:
            result: The result string to truncate.
            max_length: Maximum length before truncation.
            
        Returns:
            Truncated string with ellipsis if needed.
        """
        if len(result) <= max_length:
            return result
        return result[:max_length] + "..."
    
    async def _get_response_with_tools(self, provider, context: list, session, max_iterations: int = 10) -> None:
        """Get response from LLM with tool calling support and streaming reasoning."""
        messages = context.copy()
        iteration = 0
        
        # Get tools filtered by current mode
        mode_slug = self._get_session_mode(session)
        mode_config = self._prompt_builder.mode_manager.get(mode_slug)
        filtered_tools = self._prompt_builder.tool_catalog.filter_for_mode(mode_config)
        
        # Convert to OpenAI format for native tool calling
        tools_for_provider = [tool.to_openai_format() for tool in filtered_tools]
        
        while iteration < max_iterations:
            iteration += 1
            
            # Start live reasoning display (handles both thinking indicator and streaming)
            self._renderer.start_live_reasoning()
            
            try:
                # First check for tool calls with non-streaming request
                response = await provider.chat(
                    messages=messages,
                    model=self._config.llm.model,
                    temperature=self._config.llm.temperature,
                    max_tokens=self._config.llm.max_tokens,
                    tools=tools_for_provider if tools_for_provider else None
                )
                
                raw = response.raw_response
                choice = raw.get("choices", [{}])[0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls")
                
                # If there are tool calls, stop live display and execute them
                if tool_calls:
                    self._renderer.stop_live_stream()
                    messages.append(message)
                    
                    # Update tool action mapper working directory
                    self._tool_action_mapper.working_dir = self._tools.working_dir
                    
                    for i, tool_call in enumerate(tool_calls):
                        func = tool_call.get("function", {})
                        tool_name = func.get("name", "")
                        tool_id = tool_call.get("id", "")
                        
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        
                        # Capture state before execution for accurate create/update detection
                        # Requirements: 8.1 - Detect file creation vs update based on file existence
                        pre_state = self._tool_action_mapper.render_tool_action_before(
                            tool_name, args
                        )
                        
                        # Execute the tool
                        try:
                            result = self._tools.execute(tool_name, args)
                            success = not result.startswith("Error:")
                        except Exception as e:
                            result = str(e)
                            success = False
                        
                        # Render action card after execution with captured state
                        # Requirements: 8.1, 8.2 - Generate appropriate action cards
                        self._tool_action_mapper.render_tool_action_after(
                            pre_state, result=result, success=success
                        )
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result or ""
                        })
                    continue
                
                # No tool calls - continue streaming for real-time reasoning display
                
                try:
                    async for chunk in provider.chat_stream(
                        messages=messages,
                        model=self._config.llm.model,
                        temperature=self._config.llm.temperature,
                        max_tokens=self._config.llm.max_tokens
                    ):
                        self._renderer.update_live_stream(chunk.content)
                finally:
                    response_content, reasoning_content = self._renderer.stop_live_stream()
                
                # If model put response in thinking, use reasoning as response
                # But only if reasoning wasn't already printed during streaming
                if not response_content.strip() and reasoning_content.strip():
                    if not self._renderer.was_reasoning_printed():
                        response_content = reasoning_content
                    reasoning_content = ""
                
                # Check if model said it would do something but didn't follow through
                # Common patterns: "Let me...", "I'll...", "I will...", "First, I'll..."
                incomplete_patterns = [
                    r"(?i)\blet me\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                    r"(?i)\bi'?ll\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                    r"(?i)\bi will\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                    r"(?i)\bfirst,?\s+i'?ll\b",
                    r"(?i)\blet's\b.*\b(check|look|analyze|examine|read|list|search|find)\b",
                ]
                
                is_incomplete = False
                if response_content and iteration < max_iterations:
                    for pattern in incomplete_patterns:
                        if re.search(pattern, response_content):
                            is_incomplete = True
                            break
                
                # If model said it would do something but didn't call tools, prompt to continue
                if is_incomplete:
                    messages.append({"role": "assistant", "content": response_content})
                    messages.append({
                        "role": "user",
                        "content": "Please proceed with the action you mentioned. Use the available tools to complete the task."
                    })
                    continue
                
                # Print final response panel only if not already printed during streaming
                if response_content and not self._renderer.was_response_printed():
                    self._renderer.print_message(response_content, role="assistant")
                if response_content:
                    session.add_message("assistant", response_content, tokens=len(response_content)//4)
                    self._sessions.save_session(session)
                    
                    if self._config.ui.show_token_count:
                        self._renderer.print(f"[dim]{len(response_content)//4} tokens[/dim]")
                
                break
                
            except Exception as e:
                self._renderer.stop_live_stream()
                raise e
        
        if iteration >= max_iterations:
            self._renderer.print_warning("Reached maximum tool iterations")
