#!/usr/bin/env python3
"""
Seed the database with sample data for testing.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_supercli.history import get_database, get_session_store, get_favorites_manager


def seed_sessions():
    """Create sample chat sessions."""
    store = get_session_store()
    
    session1 = store.create_session(
        provider="groq",
        model="llama-3.3-70b-versatile",
        title="Python Help Session"
    )
    session1.add_message("user", "How do I read a file in Python?", tokens=10)
    session1.add_message(
        "assistant",
        "You can read a file in Python using the `open()` function:\n\n```python\nwith open('file.txt', 'r') as f:\n    content = f.read()\n```",
        tokens=50
    )
    session1.add_message("user", "What about reading line by line?", tokens=8)
    session1.add_message(
        "assistant",
        "To read line by line:\n\n```python\nwith open('file.txt', 'r') as f:\n    for line in f:\n        print(line.strip())\n```",
        tokens=40
    )
    store.save_session(session1)
    
    session2 = store.create_session(
        provider="openrouter",
        model="anthropic/claude-3.5-sonnet",
        title="JavaScript async/await"
    )
    session2.add_message("user", "Explain async/await in JavaScript", tokens=8)
    session2.add_message(
        "assistant",
        "Async/await is syntactic sugar for working with Promises in JavaScript...",
        tokens=100
    )
    store.save_session(session2)
    
    session3 = store.create_session(
        provider="groq",
        model="mixtral-8x7b-32768",
        title="SQL Query Optimization"
    )
    session3.add_message("user", "How can I optimize slow SQL queries?", tokens=10)
    session3.add_message(
        "assistant",
        "Here are key strategies for SQL optimization:\n1. Use indexes\n2. Avoid SELECT *\n3. Use EXPLAIN ANALYZE...",
        tokens=80
    )
    store.save_session(session3)
    
    print(f"Created {store.get_session_count()} sessions")
    return [session1, session2, session3]


def seed_favorites(sessions):
    """Add some sessions to favorites."""
    favorites = get_favorites_manager()
    
    if sessions:
        favorites.add_favorite(
            item_type="session",
            reference_id=sessions[0].id,
            title=sessions[0].title,
            tags=["python", "tutorial"]
        )
        print("Added 1 favorite")


def main():
    """Run database seeding."""
    print("Seeding database...")
    
    db = get_database()
    print(f"Database location: {db._db_path}")
    
    sessions = seed_sessions()
    seed_favorites(sessions)
    
    stats = db.get_stats()
    print(f"\nDatabase stats:")
    print(f"  Sessions: {stats['sessions']}")
    print(f"  Messages: {stats['messages']}")
    print(f"  Favorites: {stats['favorites']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    
    print("\nSeeding complete!")


if __name__ == "__main__":
    main()
