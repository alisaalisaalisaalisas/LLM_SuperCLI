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
        """Get the input prompt string with model info."""
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
        
        # Print model info above prompt
        provider = self._config.llm.provider.capitalize()
        model = self._config.llm.model
        # Only show Free for OAuth providers
        free_providers = ["qwen", "gemini", "ollama"]
        if self._config.llm.provider in free_providers:
            tier = " | [magenta]Free[/magenta]"
        else:
            tier = ""
        self._renderer.print(f"[cyan]{provider}[/cyan] / [green]{model}[/green]{tier}")
        
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
            no_tool_providers = ["qwen", "gemini"]
            if self._config.llm.provider in no_tool_providers:
                await self._get_streaming_response(provider, context, session)
            else:
                await self._get_response_with_tools(provider, context, session)
                
        except Exception as e:
            self._renderer.print_error(f"LLM Error: {e}")
    
    def _build_context_with_tools(self, session) -> list:
        """Build message context with system prompt including current directory info."""
        cwd = os.getcwd()
        
        # Enhanced system prompt - KiloCode style
        system_content = f"""You are an expert software engineer assistant with extensive capabilities.

## Environment
- Current working directory: {cwd}
- Operating system: {os.name}

## Your Capabilities

### Code Development & Analysis
- Write, modify, and refactor code in any programming language
- Analyze existing codebases and suggest improvements
- Debug and troubleshoot technical issues
- Explain complex code and algorithms

### File & Project Management
- Read, edit, and create files
- Analyze project structure and dependencies
- Search across codebases using patterns

### Development Environment
- Execute shell commands and scripts
- Work with version control (git)
- Manage project workflows

## Available Tools
- list_directory('path') - List files and folders
- read_file('path') - Read file contents  
- write_file('path', 'content') - Create/write a file
- create_directory('path') - Create a folder
- run_command('command') - Run shell command

## IMPORTANT: To use tools, write them exactly like this:
write_file('landing.html', '<html>...</html>')
list_directory('.')
read_file('main.py')

The system will execute these and show you the results.

## Guidelines
1. When asked about files or code, USE TOOLS to examine them first
2. Provide detailed, technical responses with code examples when relevant
3. Think through complex problems step by step
4. Be proactive - suggest improvements and best practices
5. Format responses with markdown for readability

## Response Format
For complex tasks, use this format:
<think>
Your reasoning and thought process here (brief, 1-3 sentences)
</think>
Your actual response to the user here (this is required - never leave empty)

IMPORTANT: Always include a response AFTER the </think> tag. The thinking is optional but the response is mandatory."""

        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history
        context = session.get_context()
        for msg in context:
            if msg.get("role") != "system":
                messages.append(msg)
        
        return messages
    
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
        """Streaming response with text-based tool parsing for providers without native tool support."""
        import re
        messages = context.copy()
        max_iterations = 3
        
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
            
            # Check for text-based tool calls
            tool_results = []
            content = response_content or ""
            
            # write_file('path', 'content')
            for match in re.finditer(r'write_file\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([\s\S]*?)[\'"]\s*\)', content):
                path, file_content = match.groups()
                self._renderer.print(f"[cyan]📝 Writing file:[/cyan] {path}")
                try:
                    result = self._tools.execute("write_file", {"path": path, "content": file_content})
                    self._renderer.print(f"[green]   ✓ Created successfully[/green]")
                    tool_results.append(f"write_file({path}): success")
                except Exception as e:
                    self._renderer.print(f"[red]   ✗ Error: {e}[/red]")
                    tool_results.append(f"write_file error: {e}")
            
            # Single-arg tools
            for tool_name, arg in re.findall(r'(list_directory|read_file|create_directory)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content):
                icons = {"list_directory": "📂", "read_file": "📖", "create_directory": "📁"}
                self._renderer.print(f"[cyan]{icons.get(tool_name, '🔧')} {tool_name}:[/cyan] {arg}")
                try:
                    result = self._tools.execute(tool_name, {"path": arg})
                    preview = result[:150] + "..." if len(result) > 150 else result
                    self._renderer.print(f"[dim]   {preview}[/dim]")
                    tool_results.append(f"{tool_name}: {result}")
                except Exception as e:
                    self._renderer.print(f"[red]   ✗ Error: {e}[/red]")
                    tool_results.append(f"{tool_name} error: {e}")
            
            # run_command
            for cmd in re.findall(r'run_command\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content):
                self._renderer.print(f"[cyan]⚡ Running:[/cyan] {cmd}")
                try:
                    result = self._tools.execute("run_command", {"command": cmd})
                    preview = result[:150] + "..." if len(result) > 150 else result
                    if preview.strip():
                        self._renderer.print(f"[dim]   {preview}[/dim]")
                    self._renderer.print(f"[green]   ✓ Done[/green]")
                    tool_results.append(f"run_command: {result}")
                except Exception as e:
                    self._renderer.print(f"[red]   ✗ Error: {e}[/red]")
                    tool_results.append(f"run_command error: {e}")
            
            if tool_results:
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "Tool results:\n" + "\n".join(tool_results) + "\n\nNow give a brief summary of what was done. Do NOT call more tools."})
                continue
            
            # No tool calls - done
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
    
    async def _get_response_with_tools(self, provider, context: list, session, max_iterations: int = 10) -> None:
        """Get response from LLM with tool calling support and streaming reasoning."""
        messages = context.copy()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            self._renderer.start_spinner("Thinking...")
            
            try:
                # First check for tool calls with non-streaming request
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
                
                # No tool calls - use streaming for real-time reasoning display
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
                self._renderer.stop_spinner()
                raise e
        
        if iteration >= max_iterations:
            self._renderer.print_warning("Reached maximum tool iterations")
