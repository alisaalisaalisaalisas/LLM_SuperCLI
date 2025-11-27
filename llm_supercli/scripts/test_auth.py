#!/usr/bin/env python3
"""
Test OAuth authentication flows.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_google_auth():
    """Test Google OAuth flow."""
    from llm_supercli.auth import GoogleOAuth
    
    print("Testing Google OAuth...")
    print("Note: This requires valid OAuth credentials in constants.py")
    
    oauth = GoogleOAuth()
    
    def on_code(code: str, url: str):
        print(f"\n1. Open this URL: {url}")
        print(f"2. Enter this code: {code}")
        print("\nWaiting for authorization...")
    
    try:
        session = await oauth.login(on_code_received=on_code)
        
        if session:
            print(f"\n✅ Login successful!")
            print(f"   User: {session.user_name}")
            print(f"   Email: {session.user_email}")
            print(f"   Token expires: {session.expires_at}")
        else:
            print("\n❌ Login failed or was cancelled")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


async def test_github_auth():
    """Test GitHub OAuth flow."""
    from llm_supercli.auth import GitHubOAuth
    
    print("Testing GitHub OAuth...")
    print("Note: This requires valid OAuth credentials in constants.py")
    
    oauth = GitHubOAuth()
    
    def on_code(code: str, url: str):
        print(f"\n1. Open this URL: {url}")
        print(f"2. Enter this code: {code}")
        print("\nWaiting for authorization...")
    
    try:
        session = await oauth.login(on_code_received=on_code)
        
        if session:
            print(f"\n✅ Login successful!")
            print(f"   User: {session.user_name}")
            print(f"   Email: {session.user_email}")
        else:
            print("\n❌ Login failed or was cancelled")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_session_manager():
    """Test session manager."""
    from llm_supercli.auth import SessionManager, AuthSession
    
    print("\nTesting SessionManager...")
    
    manager = SessionManager()
    
    test_session = AuthSession(
        provider="test",
        access_token="test_token_123",
        user_email="test@example.com",
        user_name="Test User"
    )
    
    manager.store_session(test_session)
    print("  Stored test session")
    
    retrieved = manager.get_session("test")
    assert retrieved is not None
    assert retrieved.user_email == "test@example.com"
    print("  Retrieved session successfully")
    
    assert manager.is_authenticated("test")
    print("  Authentication check passed")
    
    manager.remove_session("test")
    assert not manager.is_authenticated("test")
    print("  Session removed successfully")
    
    print("✅ SessionManager tests passed!")


def main():
    """Run authentication tests."""
    print("=" * 50)
    print("LLM SuperCLI Authentication Tests")
    print("=" * 50)
    
    test_session_manager()
    
    print("\nTo test OAuth flows, uncomment the desired test below:")
    print("  - test_google_auth()")
    print("  - test_github_auth()")
    
    # Uncomment to test actual OAuth flows:
    # asyncio.run(test_google_auth())
    # asyncio.run(test_github_auth())


if __name__ == "__main__":
    main()
