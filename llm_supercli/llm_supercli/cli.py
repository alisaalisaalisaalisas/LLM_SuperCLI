"""
Main CLI loop for llm_supercli.
Handles the interactive command loop and message processing.
"""
import asyncio
import json
import os
import sys
from typing import Any, Optional

from .config import get_config
from .rich_ui import RichRenderer, InputHandler, get_theme_manager
from .rich_ui.prompt_input import PromptInput
from .command_system import CommandParser, get_command_registry
from .history import get_session_store
from .llm import get_provider_registry
from .mcp import get_mcp_manager
from .io_handlers import BashRunner, FileLoader
from .tools import TOOLS, ToolExecutor


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
        self._current_mode: Optional[str] = None
        self._input = PromptInput()
        self._input.set_commands(self._commands.list_commands())
    
    def run(self) -> None:
        """Run the CLI main loop."""
        self._running = True
        self._renderer.print_welcome()
        self._ensure_session()
        
        # Print initial model status
        self._renderer.print_status(
            provider=self._config.llm.provider,
            model=self._config.llm.model
        )
        self._renderer.print()
        
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
        """Get the input prompt string."""
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
            
            # Use non-streaming for tool support
            await self._get_response_with_tools(provider, context, session)
                
        except Exception as e:
            self._renderer.print_error(f"LLM Error: {e}")
    
    def _build_context_with_tools(self, session) -> list:
        """Build message context with system prompt including current directory info."""
        cwd = os.getcwd()
        
        # Enhanced system prompt with tool awareness
        system_content = f"""You are a helpful AI assistant running in a command-line interface.
You have access to the user's file system and can help with file operations.

Current working directory: {cwd}

You have the following tools available:
- get_current_directory: Get the current working directory
- list_directory: List files and folders in a directory
- read_file: Read the contents of a file
- write_file: Write content to a file
- create_directory: Create a new directory
- run_command: Run a shell command

When the user asks about files, projects, or needs file operations, USE THE TOOLS to help them.
Always use tools when you need to see file contents or directory structure.
Be concise and helpful."""

        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history
        context = session.get_context()
        for msg in context:
            if msg.get("role") != "system":
                messages.append(msg)
        
        return messages
    
    async def _stream_response(self, provider, context: list, session) -> None:
        """Stream response from LLM."""
        full_response = ""
        
        live = self._renderer.start_spinner("Thinking...")
        
        try:
            first_chunk = True
            async for chunk in provider.chat_stream(
                messages=context,
                model=self._config.llm.model,
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens
            ):
                if first_chunk:
                    self._renderer.stop_spinner()
                    first_chunk = False
                
                full_response += chunk.content
                self._renderer.print(chunk.content, end="")
            
            self._renderer.print()  # Newline after streaming
            
        finally:
            self._renderer.stop_spinner()
        
        if full_response:
            tokens = len(full_response) // 4
            session.add_message("assistant", full_response, tokens=tokens)
            self._sessions.save_session(session)
    
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
            
            self._renderer.print_message(response.content, role="assistant")
            
            session.add_message(
                "assistant",
                response.content,
                tokens=response.total_tokens,
                cost=response.cost
            )
            self._sessions.save_session(session)
            
            if self._config.ui.show_token_count:
                self._renderer.print_status(
                    provider=response.provider,
                    model=response.model,
                    tokens=(response.input_tokens, response.output_tokens),
                    cost=response.cost if self._config.ui.show_cost else None
                )
                
        finally:
            self._renderer.stop_spinner()
    
    async def _get_response_with_tools(self, provider, context: list, session, max_iterations: int = 10) -> None:
        """Get response from LLM with tool calling support."""
        messages = context.copy()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            self._renderer.start_spinner("Thinking...")
            
            try:
                response = await provider.chat(
                    messages=messages,
                    model=self._config.llm.model,
                    temperature=self._config.llm.temperature,
                    max_tokens=self._config.llm.max_tokens,
                    tools=TOOLS
                )
                
                self._renderer.stop_spinner()
                
                raw = response.raw_response
                choice = raw.get("choices", [{}])[0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls")
                
                # If there are tool calls, execute them
                if tool_calls:
                    # Add assistant message with tool calls to context
                    messages.append(message)
                    
                    for tool_call in tool_calls:
                        func = tool_call.get("function", {})
                        tool_name = func.get("name", "")
                        tool_id = tool_call.get("id", "")
                        
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        
                        # Show tool execution
                        self._renderer.print(f"[dim]> Using tool: {tool_name}({args})[/dim]")
                        
                        # Execute the tool
                        result = self._tools.execute(tool_name, args)
                        
                        # Show result preview
                        preview = result[:200] + "..." if len(result) > 200 else result
                        self._renderer.print(f"[dim]> Result: {preview}[/dim]\n")
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result
                        })
                    
                    # Continue loop to get next response
                    continue
                
                # No tool calls - this is the final response
                content = response.content or ""
                if content:
                    self._renderer.print_message(content, role="assistant")
                    
                    session.add_message(
                        "assistant",
                        content,
                        tokens=response.total_tokens,
                        cost=response.cost
                    )
                    self._sessions.save_session(session)
                    
                    if self._config.ui.show_token_count:
                        self._renderer.print_status(
                            provider=response.provider,
                            model=response.model,
                            tokens=(response.input_tokens, response.output_tokens),
                            cost=response.cost if self._config.ui.show_cost else None
                        )
                
                break
                
            except Exception as e:
                self._renderer.stop_spinner()
                raise e
        
        if iteration >= max_iterations:
            self._renderer.print_warning("Reached maximum tool iterations")
