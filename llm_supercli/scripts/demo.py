#!/usr/bin/env python3
"""
Demo script showcasing llm_supercli features.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def demo_rich_ui():
    """Demonstrate Rich UI components."""
    from llm_supercli.rich_ui import RichRenderer, ASCIIArt, get_theme_manager
    
    print("\n" + "=" * 50)
    print("Rich UI Demo")
    print("=" * 50)
    
    renderer = RichRenderer()
    
    renderer.print_banner("small")
    
    renderer.print_message("Hello! How can I help you today?", role="user")
    renderer.print_message(
        "I'm an AI assistant. I can help with:\n"
        "- Code generation\n"
        "- Answering questions\n"
        "- Analysis and more!",
        role="assistant"
    )
    
    renderer.print_code(
        "def hello():\n    print('Hello, World!')\n\nhello()",
        language="python",
        title="example.py"
    )
    
    renderer.print_success("Operation completed!")
    renderer.print_warning("This is a warning")
    renderer.print_error("This is an error")
    renderer.print_info("This is info")
    
    renderer.print_table([
        {"Name": "Groq", "Status": "Active", "Models": "4"},
        {"Name": "OpenRouter", "Status": "Active", "Models": "18"},
        {"Name": "Ollama", "Status": "Local", "Models": "12"},
    ], title="Available Providers")


def demo_themes():
    """Demonstrate theme system."""
    from llm_supercli.rich_ui import get_theme_manager, RichRenderer
    
    print("\n" + "=" * 50)
    print("Theme System Demo")
    print("=" * 50)
    
    manager = get_theme_manager()
    
    print(f"Available themes: {manager.available_themes}")
    print(f"Current theme: {manager.current_theme.name}")
    
    for theme_name in manager.available_themes[:3]:
        print(f"\nSwitching to {theme_name}...")
        manager.set_theme(theme_name)
        renderer = RichRenderer()
        renderer.print(f"[primary]Primary[/] | [secondary]Secondary[/] | [accent]Accent[/]")


async def demo_providers():
    """Demonstrate LLM provider system."""
    from llm_supercli.llm import get_provider_registry
    
    print("\n" + "=" * 50)
    print("LLM Provider Demo")
    print("=" * 50)
    
    registry = get_provider_registry()
    
    print(f"Registered providers: {registry.list_providers()}")
    
    for name in registry.list_providers():
        info = registry.get_provider_info(name)
        if info:
            print(f"\n{name}:")
            print(f"  Models: {len(info['available_models'])}")
            print(f"  API Key: {'Set' if info['has_api_key'] else 'Not set'}")


def demo_commands():
    """Demonstrate command system."""
    from llm_supercli.command_system import get_command_registry
    
    print("\n" + "=" * 50)
    print("Command System Demo")
    print("=" * 50)
    
    registry = get_command_registry()
    
    print(f"Registered commands: {registry.command_count}")
    
    commands = registry.list_commands()
    for cmd in commands[:10]:
        print(f"  /{cmd['name']}: {cmd['description'][:40]}...")
    
    result = registry.execute("help")
    print(f"\n/help result: {result.status.value}")


def demo_history():
    """Demonstrate history/session system."""
    from llm_supercli.history import get_session_store, get_database
    
    print("\n" + "=" * 50)
    print("History System Demo")
    print("=" * 50)
    
    db = get_database()
    store = get_session_store()
    
    print(f"Database location: {db._db_path}")
    
    session = store.create_session(
        provider="demo",
        model="demo-model",
        title="Demo Session"
    )
    
    session.add_message("user", "Hello!")
    session.add_message("assistant", "Hi there! How can I help?")
    
    store.save_session(session)
    
    print(f"Created session: {session.id[:8]}...")
    print(f"Messages: {session.message_count}")
    
    store.delete_session(session.id)
    print("Session deleted")


def demo_mcp():
    """Demonstrate MCP system."""
    from llm_supercli.mcp import get_mcp_manager, MCPServerConfig
    
    print("\n" + "=" * 50)
    print("MCP System Demo")
    print("=" * 50)
    
    manager = get_mcp_manager()
    
    config = MCPServerConfig(
        name="demo-server",
        command="echo",
        args=["hello"],
        description="Demo MCP server"
    )
    
    manager.registry.register(config)
    print(f"Registered server: {config.name}")
    
    status = manager.get_status()
    print(f"Registered servers: {status['registered_servers']}")
    print(f"Connected servers: {status['connected_servers']}")
    
    manager.registry.unregister("demo-server")
    print("Server unregistered")


def main():
    """Run all demos."""
    print("=" * 50)
    print("LLM SuperCLI Feature Demo")
    print("=" * 50)
    
    demo_rich_ui()
    demo_themes()
    asyncio.run(demo_providers())
    demo_commands()
    demo_history()
    demo_mcp()
    
    print("\n" + "=" * 50)
    print("Demo complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
