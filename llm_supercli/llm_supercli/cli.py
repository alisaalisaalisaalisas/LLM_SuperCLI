"""
Main CLI loop for llm_supercli.
Handles the interactive command loop and message processing.
"""
import asyncio
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
        self._running = False
        self._current_mode: Optional[str] = None
        self._input = PromptInput()
        self._input.set_commands(self._commands.list_commands())
    
    def run(self) -> None:
        """Run the CLI main loop."""
        self._running = True
        self._renderer.print_welcome()
        self._ensure_session()
        
        while self._running:
            try:
                user_input = self._input.get_input(
                    prompt=self._get_prompt()
                )
                
                if not user_input.strip():
                    continue
                
                asyncio.run(self._process_input(user_input))
                
            except KeyboardInterrupt:
                self._renderer.print("\n[dim]Use /quit to exit[/dim]")
            except EOFError:
                self._running = False
            except Exception as e:
                self._renderer.print_error(f"Unexpected error: {e}")
    
    def _get_prompt(self) -> str:
        """Get the input prompt string."""
        # Update status bar with current info
        cwd = os.getcwd()
        model = f"{self._config.llm.provider}/{self._config.llm.model.split('/')[-1][:15]}"
        self._input.set_status(cwd=cwd, model=model)
        return "> "
    
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
            
            if not provider.api_key and self._config.llm.provider != "ollama":
                self._renderer.print_error(
                    f"No API key set for {self._config.llm.provider}. "
                    f"Set environment variable or use /settings."
                )
                return
            
            context = session.get_context()
            
            if self._config.ui.streaming:
                await self._stream_response(provider, context, session)
            else:
                await self._get_response(provider, context, session)
                
        except Exception as e:
            self._renderer.print_error(f"LLM Error: {e}")
    
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
