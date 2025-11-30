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
    """
    
    def __init__(self) -> None:
        """Initialize the CLI."""
        self._config = get_config()
        self._renderer = RichRenderer()
        self._parser = CommandParser()
        self._commands = get_command_registry()
        self._sessions = get_session_store()
        self._providers = get_provider_registry()
        self._mcp = get_mcp_manager()
        self._bash = BashRunner()
        self._files = FileLoader()
        self._tools = ToolExecutor()
        self._running = False
        self._current_mode: str = "code"  # Default mode
        self._input = PromptInput()
        self._input.set_commands(self._commands.list_commands())
        
        # Initialize the new prompt system
        self._prompt_builder = self._create_prompt_builder()
    
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
        """Run the CLI main loop."""
        self._running = True
        self._renderer.print_welcome()
        self._ensure_session()
        
        # Print startup tips
        self._renderer.print("[dim]Tips:[/dim]")
        self._renderer.print("[dim]1. Ask questions, edit files, or run commands[/dim]")
        self._renderer.print("[dim]2. Use @file to include file contents[/dim]")
        self._renderer.print("[dim]3. Use /help for more information[/dim]")
        self._renderer.print()
        
        while self._running:
            try:
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
        """Handle a slash command synchronously."""
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
            return
        
        if result.message:
            if result.is_error:
                self._renderer.print_error(result.message)
            else:
                self._renderer.print_markdown(result.message)
    
    def _get_prompt(self) -> str:
        """Get the input prompt string with model info and current mode."""
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
        mode_display = f" | [yellow]{mode_config.icon} {mode_config.name}[/yellow]"
        
        self._renderer.print(f"[cyan]{provider}[/cyan] / [green]{model}[/green]{tier}{mode_display}")
        
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
            
            # Build context with system message including current directory
            context = self._build_context_with_tools(session)
            
            # Providers without native tool support - use simple streaming
            no_tool_providers = ["qwen", "gemini", "groq"]
            if self._config.llm.provider in no_tool_providers:
                await self._get_streaming_response(provider, context, session)
            else:
                await self._get_response_with_tools(provider, context, session)
                
        except Exception as e:
            self._renderer.print_error(f"LLM Error: {e}")
    
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
            
            # Display final reasoning box if any
            if reasoning_content:
                self._renderer.print_reasoning(reasoning_content)
            
            # Display response
            if response_content:
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
        max_iterations = 3
        
        # Initialize the tool parser with registered format parsers
        tool_parser = ToolParser()
        tool_parser.register(PythonStyleParser())
        tool_parser.register(XMLStyleParser())
        
        for _ in range(max_iterations):
            self._renderer.start_live_reasoning()
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
            
            # Parse tool calls using the modular ToolParser
            content = response_content or ""
            parsed_calls = tool_parser.parse(content)
            
            # Execute parsed tool calls with consistent visual feedback
            tool_results = []
            num_calls = len(parsed_calls)
            
            # Add visual header if multiple tool calls
            if num_calls > 1:
                self._renderer.print(f"[dim]─── Executing {num_calls} tool calls ───[/dim]")
            
            for i, call in enumerate(parsed_calls):
                result_str = self._execute_tool_call(call)
                tool_results.append(result_str)
                
                # Add visual separator between multiple tool calls
                if num_calls > 1 and i < num_calls - 1:
                    self._renderer.print("[dim]───[/dim]")
            
            if tool_results:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": "Tool results:\n" + "\n".join(tool_results) + "\n\nNow give a brief summary of what was done. Do NOT call more tools."
                })
                continue
            
            # No tool calls - done
            # Display reasoning if present
            if reasoning_content and reasoning_content.strip():
                self._renderer.print_reasoning(reasoning_content.strip())
            
            # Use response_content, fall back to reasoning only if response is empty
            final_content = response_content.strip() if response_content else ""
            if not final_content and reasoning_content:
                final_content = reasoning_content.strip()
            
            # Clean any remaining think tags
            final_content = re.sub(r'</?think>?', '', final_content).strip()
            
            if final_content:
                self._renderer.print_message(final_content, role="assistant")
                session.add_message("assistant", final_content)
            break
    
    def _execute_tool_call(self, call: ParsedToolCall) -> str:
        """Execute a parsed tool call with consistent visual feedback.
        
        Provides uniform display for tool execution regardless of the parsing
        format used (Python-style, XML-style, etc.).
        
        Args:
            call: The parsed tool call to execute.
            
        Returns:
            A string describing the result for inclusion in the conversation.
            
        Requirements: 4.1, 4.2, 4.3, 4.4
        """
        tool_name = call.name
        arguments = call.arguments
        
        # Tool icons for consistent visual feedback
        tool_icons = {
            "read_file": "📖",
            "write_file": "📝",
            "list_directory": "📂",
            "create_directory": "📁",
            "run_command": "⚡",
            "get_current_directory": "📍",
        }
        icon = tool_icons.get(tool_name, "🔧")
        
        # Normalize arguments - handle both positional (arg0, arg1) and named arguments
        normalized_args = self._normalize_tool_arguments(tool_name, arguments)
        
        # Display tool execution header
        args_preview = self._format_args_preview(normalized_args)
        self._renderer.print(f"[cyan]{icon} {tool_name}[/cyan]{args_preview}")
        
        try:
            result = self._tools.execute(tool_name, normalized_args)
            
            # Display success with result preview
            preview = self._truncate_result(result, max_length=150)
            if preview.strip():
                self._renderer.print(f"[dim]   {preview}[/dim]")
            self._renderer.print(f"[green]   ✓ Success[/green]")
            
            return f"{tool_name}: {result}"
            
        except Exception as e:
            # Display failure with error message
            self._renderer.print(f"[red]   ✗ Error: {e}[/red]")
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
                    
                    for tool_call in tool_calls:
                        func = tool_call.get("function", {})
                        tool_name = func.get("name", "")
                        tool_id = tool_call.get("id", "")
                        
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        
                        self._renderer.print(f"[dim]> Using tool: {tool_name}({args})[/dim]")
                        result = self._tools.execute(tool_name, args)
                        preview = result[:200] + "..." if len(result) > 200 else result
                        self._renderer.print(f"[dim]> Result: {preview}[/dim]\n")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result
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
                if not response_content.strip() and reasoning_content.strip():
                    response_content = reasoning_content
                    reasoning_content = ""
                
                # Display response (reasoning was already shown during streaming)
                if response_content:
                    self._renderer.print_message(response_content, role="assistant")
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
