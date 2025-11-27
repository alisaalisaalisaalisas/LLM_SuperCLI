"""Interactive menu utilities for llm_supercli."""
import asyncio
from typing import List, Optional, Tuple, Dict, Any
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import radiolist_dialog, button_dialog
from prompt_toolkit.styles import Style
from rich.console import Console


console = Console()


def _run_dialog(dialog):
    """Run a prompt_toolkit dialog safely, handling existing event loops."""
    try:
        # Check if there's already a running event loop
        asyncio.get_running_loop()
        # If we get here, there's a running loop - raise to trigger fallback
        raise RuntimeError("Running in async context")
    except RuntimeError as e:
        if "no running event loop" in str(e).lower():
            # No running loop, safe to use .run()
            return dialog.run()
        # Already in async context, re-raise to trigger fallback
        raise


def select_from_list(
    title: str,
    items: List[Tuple[Any, str]],
    description: str = ""
) -> Optional[Any]:
    """
    Show an interactive selection menu.
    
    Args:
        title: Title of the menu
        items: List of (value, label) tuples
        description: Optional description text
        
    Returns:
        Selected value or None if cancelled
    """
    if not items:
        console.print("[yellow]No items available to select[/yellow]")
        return None
    
    # Custom style for the dialog
    dialog_style = Style.from_dict({
        'dialog': 'bg:#1e1e1e',
        'dialog frame.label': 'bg:#00aaaa #ffffff bold',
        'dialog.body': 'bg:#1e1e1e #cccccc',
        'dialog shadow': 'bg:#000000',
        'button': 'bg:#004488',
        'button.focused': 'bg:#00aaaa',
        'radio-list': 'bg:#1e1e1e',
        'radio': 'bg:#1e1e1e',
        'radio-checked': '#00aaaa bold',
        'radio-selected': 'bg:#004488',
    })
    
    dialog = radiolist_dialog(
        title=title,
        text=description,
        values=items,
        style=dialog_style
    )
    
    result = _run_dialog(dialog)
    
    return result


def select_model_interactive(registry) -> Optional[Tuple[str, str]]:
    """
    Interactive model selection menu.
    
    Returns:
        Tuple of (provider, model) or None if cancelled
    """
    try:
        # First, select provider
        all_models = registry.list_all_models()
        
        if not all_models:
            console.print("[red]No providers available. Please configure API keys.[/red]")
            return None
        
        console.print(f"[dim]Found {len(all_models)} providers[/dim]")
        
        provider_items = []
        for provider, models in all_models.items():
            info = registry.get_provider_info(provider)
            has_key = info.get("has_api_key", False) if info else False
            key_status = "✓" if has_key else "✗"
            label = f"{provider.title()} [{key_status}] ({len(models)} models)"
            provider_items.append((provider, label))
        
        try:
            selected_provider = select_from_list(
                title="Select Provider",
                items=provider_items,
                description="Choose an LLM provider (✓ = API key configured)"
            )
        except Exception as e:
            console.print(f"[yellow]Dialog error: {e}[/yellow]")
            console.print("[yellow]Falling back to console selection...[/yellow]\n")
            
            # Fallback: console-based selection
            console.print("[bold cyan]Available Providers:[/bold cyan]")
            for idx, (provider, label) in enumerate(provider_items, 1):
                console.print(f"  {idx}. {label}")
            
            from rich.prompt import IntPrompt
            choice = IntPrompt.ask(
                "Select provider number",
                choices=[str(i) for i in range(1, len(provider_items) + 1)]
            )
            selected_provider = provider_items[choice - 1][0]
        
        if not selected_provider:
            return None
        
        # Then, select model from that provider
        models = all_models.get(selected_provider, [])
        if not models:
            console.print(f"[red]No models available for {selected_provider}[/red]")
            return None
        
        console.print(f"[dim]Found {len(models)} models for {selected_provider}[/dim]")
        
        # Limit to first 50 models for usability
        display_models = models[:50]
        model_items = [(model, model) for model in display_models]
        
        if len(models) > 50:
            console.print(f"[yellow]Showing first 50 of {len(models)} models[/yellow]")
        
        try:
            selected_model = select_from_list(
                title=f"Select Model from {selected_provider.title()}",
                items=model_items,
                description=f"Choose a model from {selected_provider}"
            )
        except Exception as e:
            console.print(f"[yellow]Dialog error: {e}[/yellow]")
            console.print("[yellow]Falling back to console selection...[/yellow]\n")
            
            # Fallback: console-based selection
            console.print(f"[bold cyan]Available Models for {selected_provider.title()}:[/bold cyan]")
            for idx, (model, _) in enumerate(model_items, 1):
                console.print(f"  {idx}. {model}")
            
            from rich.prompt import IntPrompt
            choice = IntPrompt.ask(
                "Select model number",
                choices=[str(i) for i in range(1, len(model_items) + 1)]
            )
            selected_model = model_items[choice - 1][0]
        
        if not selected_model:
            return None
        
        return (selected_provider, selected_model)
    
    except Exception as e:
        console.print(f"[red]Error in model selection: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return None


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Show a confirmation dialog.
    
    Args:
        message: Message to display
        default: Default selection (True for Yes, False for No)
        
    Returns:
        True if confirmed, False otherwise
    """
    dialog_style = Style.from_dict({
        'dialog': 'bg:#1e1e1e',
        'dialog frame.label': 'bg:#00aaaa #ffffff bold',
        'dialog.body': 'bg:#1e1e1e #cccccc',
        'button': 'bg:#004488',
        'button.focused': 'bg:#00aaaa',
    })
    
    dialog = button_dialog(
        title="Confirm",
        text=message,
        buttons=[
            ('Yes', True),
            ('No', False),
        ],
        style=dialog_style
    )
    
    try:
        result = _run_dialog(dialog)
    except RuntimeError:
        # Fallback to console
        from rich.prompt import Confirm
        result = Confirm.ask(message, default=default)
    
    return result if result is not None else default


def select_provider_interactive(registry) -> Optional[str]:
    """
    Interactive provider selection menu.
    
    Returns:
        Selected provider name or None if cancelled
    """
    all_models = registry.list_all_models()
    
    provider_items = []
    for provider, models in all_models.items():
        info = registry.get_provider_info(provider)
        has_key = info.get("has_api_key", False) if info else False
        key_status = "✓" if has_key else "✗"
        label = f"{provider.title()} [{key_status}] ({len(models)} models)"
        provider_items.append((provider, label))
    
    selected_provider = select_from_list(
        title="Select Provider",
        items=provider_items,
        description="Choose an LLM provider (✓ = API key configured)"
    )
    
    return selected_provider


def select_settings_option(config) -> Optional[Tuple[str, Any]]:
    """
    Interactive settings menu.
    
    Returns:
        Tuple of (setting_key, new_value) or None if cancelled
    """
    from prompt_toolkit.shortcuts import input_dialog
    
    # Create list of all configurable settings
    settings_items = [
        ("provider", f"LLM Provider (current: {config.llm.provider})"),
        ("model", f"LLM Model (current: {config.llm.model})"),
        ("temperature", f"Temperature (current: {config.llm.temperature})"),
        ("max_tokens", f"Max Tokens (current: {config.llm.max_tokens})"),
        ("theme", f"UI Theme (current: {config.ui.theme})"),
        ("streaming", f"Streaming (current: {config.ui.streaming})"),
        ("show_token_count", f"Show Token Count (current: {config.ui.show_token_count})"),
        ("show_cost", f"Show Cost (current: {config.ui.show_cost})"),
    ]
    
    selected_setting = select_from_list(
        title="Select Setting to Change",
        items=settings_items,
        description="Choose a setting to modify"
    )
    
    if not selected_setting:
        return None
    
    # Get new value
    dialog_style = Style.from_dict({
        'dialog': 'bg:#1e1e1e',
        'dialog frame.label': 'bg:#00aaaa #ffffff bold',
        'dialog.body': 'bg:#1e1e1e #cccccc',
        'dialog shadow': 'bg:#000000',
        'text-area': 'bg:#1e1e1e #cccccc',
        'button': 'bg:#004488',
        'button.focused': 'bg:#00aaaa',
    })
    
    dialog = input_dialog(
        title=f"Set {selected_setting}",
        text=f"Enter new value for {selected_setting}:",
        style=dialog_style
    )
    
    try:
        new_value = _run_dialog(dialog)
    except RuntimeError:
        # Fallback to console input
        from rich.prompt import Prompt
        new_value = Prompt.ask(f"Enter new value for {selected_setting}")
    
    if new_value is None:
        return None
    
    return (selected_setting, new_value)

