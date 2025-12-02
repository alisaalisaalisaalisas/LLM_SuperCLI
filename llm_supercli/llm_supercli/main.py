"""
Main entry point for llm_supercli.
"""
import argparse
import os
import sys
from typing import Optional

from .constants import APP_NAME, APP_VERSION, APP_DESCRIPTION


# Environment variable name for disabling update checks
# Requirements: 2.1 - Environment variable to skip update check
UPDATE_CHECK_ENV_VAR = "LLM_SUPERCLI_NO_UPDATE_CHECK"


def is_update_check_disabled(args: argparse.Namespace) -> bool:
    """
    Check if update checking is disabled via CLI flag or environment variable.
    
    Args:
        args: Parsed command line arguments.
        
    Returns:
        True if update checking should be skipped, False otherwise.
        
    Requirements: 2.1, 2.2, 2.3 - Control update checking behavior
    """
    # Check CLI flag first (Requirements: 2.2)
    if getattr(args, 'no_update_check', False):
        return True
    
    # Check environment variable (Requirements: 2.1)
    env_value = os.environ.get(UPDATE_CHECK_ENV_VAR, "").strip()
    if env_value in ("1", "true", "yes", "on"):
        return True
    
    return False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=APP_DESCRIPTION
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}"
    )
    
    parser.add_argument(
        "-p", "--provider",
        type=str,
        help="LLM provider to use (groq, openrouter, together, huggingface, ollama)"
    )
    
    parser.add_argument(
        "-m", "--model",
        type=str,
        help="Model to use"
    )
    
    parser.add_argument(
        "-t", "--theme",
        type=str,
        help="UI theme (default, dark, solarized)"
    )
    
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable response streaming"
    )
    
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help="Skip automatic update check on startup"
    )
    
    parser.add_argument(
        "-c", "--command",
        type=str,
        help="Execute a single command and exit"
    )
    
    parser.add_argument(
        "-e", "--execute",
        type=str,
        help="Execute a prompt and exit"
    )
    
    parser.add_argument(
        "--completion",
        type=str,
        choices=["bash", "zsh", "fish", "powershell"],
        help="Generate shell completion script"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file"
    )
    
    return parser.parse_args()


def generate_completion(shell: str) -> str:
    """Generate shell completion script."""
    if shell == "bash":
        return '''
_llm_supercli_completions() {
    local commands="help account login logout sessions new clear model mcp settings status cost favorite compress rewind quit"
    COMPREPLY=($(compgen -W "$commands" -- "${COMP_WORDS[COMP_CWORD]}"))
}
complete -F _llm_supercli_completions llm-supercli
'''
    elif shell == "zsh":
        return '''
#compdef llm-supercli
_llm_supercli() {
    local -a commands
    commands=(
        'help:Show help'
        'account:View account'
        'login:Login'
        'logout:Logout'
        'sessions:Manage sessions'
        'new:New session'
        'clear:Clear screen'
        'model:Switch model'
        'mcp:MCP management'
        'settings:Settings'
        'status:Show status'
        'quit:Exit'
    )
    _describe 'command' commands
}
compdef _llm_supercli llm-supercli
'''
    elif shell == "fish":
        return '''
complete -c llm-supercli -n __fish_use_subcommand -a help -d 'Show help'
complete -c llm-supercli -n __fish_use_subcommand -a account -d 'View account'
complete -c llm-supercli -n __fish_use_subcommand -a login -d 'Login'
complete -c llm-supercli -n __fish_use_subcommand -a logout -d 'Logout'
complete -c llm-supercli -n __fish_use_subcommand -a sessions -d 'Manage sessions'
complete -c llm-supercli -n __fish_use_subcommand -a new -d 'New session'
complete -c llm-supercli -n __fish_use_subcommand -a model -d 'Switch model'
complete -c llm-supercli -n __fish_use_subcommand -a quit -d 'Exit'
'''
    elif shell == "powershell":
        return '''
Register-ArgumentCompleter -Native -CommandName llm-supercli -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @('help', 'account', 'login', 'logout', 'sessions', 'new', 'clear', 'model', 'mcp', 'settings', 'status', 'quit')
    $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
'''
    return ""


def run_update_check_sync(notifier: 'UpdateNotifier') -> None:
    """
    Run update check in a background thread without blocking.
    
    Args:
        notifier: UpdateNotifier instance to queue notifications.
        
    Requirements: 1.1, 3.1, 3.2 - Non-blocking async update check
    """
    import asyncio
    from .constants import APP_VERSION
    from .update_cache import UpdateCache
    from .update_checker import UpdateChecker
    
    async def _check():
        cache = UpdateCache()
        checker = UpdateChecker(cache)
        result = await checker.check_for_update(APP_VERSION)
        
        if result.update_available:
            notifier.queue_notification(result)
    
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_check())
        finally:
            loop.close()
    except Exception:
        # Silently ignore any errors during update check
        # Requirements: 1.4 - Continue normal operation without displaying errors
        pass


def main() -> int:
    """Main entry point."""
    import asyncio
    import threading
    
    args = parse_args()
    
    if args.completion:
        print(generate_completion(args.completion))
        return 0
    
    from .config import get_config
    config = get_config()
    
    if args.provider:
        config.update_llm(provider=args.provider)
    
    if args.model:
        config.update_llm(model=args.model)
    
    if args.theme:
        config.update_ui(theme=args.theme)
    
    if args.no_stream:
        config.update_ui(streaming=False)
    
    if args.command:
        from .command_system import get_command_registry
        registry = get_command_registry()
        # Parse command and args
        cmd_parts = args.command.lstrip("/").split(maxsplit=1)
        cmd_name = cmd_parts[0] if cmd_parts else ""
        cmd_args = cmd_parts[1] if len(cmd_parts) > 1 else ""
        result = registry.execute(cmd_name, cmd_args)
        if result.message:
            print(result.message)
        return 0 if result.is_success else 1
    
    if args.execute:
        from .llm import get_provider_registry
        
        async def run_prompt():
            provider = get_provider_registry().get(config.llm.provider)
            if not provider:
                print(f"Error: Provider {config.llm.provider} not found")
                return 1
            
            try:
                response = await provider.chat(
                    messages=[{"role": "user", "content": args.execute}],
                    model=config.llm.model
                )
                print(response.content)
                return 0
            except Exception as e:
                print(f"Error: {e}")
                return 1
        
        return asyncio.run(run_prompt())
    
    # Initialize update notifier for the interactive CLI
    # Requirements: 3.3 - Show notification after main operation completes
    from .update_notifier import get_update_notifier
    notifier = get_update_notifier()
    
    # Start update check in background thread if not disabled
    # Requirements: 2.1, 2.2, 2.3 - Control update checking behavior
    update_thread = None
    if not is_update_check_disabled(args):
        # Run update check in background thread without blocking CLI startup
        # Requirements: 3.1, 3.2 - Non-blocking async update check
        update_thread = threading.Thread(
            target=run_update_check_sync,
            args=(notifier,),
            daemon=True  # Thread will be killed when main program exits
        )
        update_thread.start()
    
    from .cli import CLI
    cli = CLI()
    
    try:
        cli.run()
        
        # Wait for update check thread to complete (with timeout)
        # Requirements: 3.3 - Show notification after main CLI output completes
        if update_thread is not None and update_thread.is_alive():
            # Give the update check a short time to complete if it hasn't already
            update_thread.join(timeout=0.5)
        
        # Show any pending update notification
        notifier.show_pending_notification()
        
        return 0
    except KeyboardInterrupt:
        print("\nGoodbye!")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
