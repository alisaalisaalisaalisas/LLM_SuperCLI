"""Login command for llm_supercli."""
from typing import Any

from ..base import AsyncSlashCommand, CommandResult


class LoginCommand(AsyncSlashCommand):
    """Login with OAuth."""
    
    name = "login"
    description = "Login with Google or GitHub OAuth"
    usage = "[google|github]"
    examples = ["/login google", "/login github"]
    
    async def run_async(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute login command."""
        from ...auth import GoogleOAuth, GitHubOAuth, get_session_manager
        from ...constants import GOOGLE_CLIENT_ID, GITHUB_CLIENT_ID
        
        session_manager = get_session_manager()
        provider = args.strip().lower() or "google"
        
        if provider not in ("google", "github"):
            return CommandResult.error(
                f"Unknown provider: {provider}. Use 'google' or 'github'."
            )
        
        # Check if OAuth credentials are configured
        if provider == "google" and GOOGLE_CLIENT_ID == "YOUR_GOOGLE_CLIENT_ID":
            return CommandResult.error(
                "Google OAuth not configured.\n\n"
                "To enable Google login:\n"
                "1. Create OAuth credentials at https://console.cloud.google.com\n"
                "2. Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in constants.py\n"
                "3. Or set environment variables GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
            )
        
        if provider == "github" and GITHUB_CLIENT_ID == "YOUR_GITHUB_CLIENT_ID":
            return CommandResult.error(
                "GitHub OAuth not configured.\n\n"
                "To enable GitHub login:\n"
                "1. Create OAuth App at https://github.com/settings/developers\n"
                "2. Update GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in constants.py\n"
                "3. Or set environment variables GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET"
            )
        
        if session_manager.is_authenticated(provider):
            user = session_manager.get_user_info()
            return CommandResult.success(
                f"Already logged in as **{user.get('name', user.get('email'))}** "
                f"via {provider.title()}"
            )
        
        if provider == "google":
            oauth = GoogleOAuth()
        else:
            oauth = GitHubOAuth()
        
        result_holder = {"code": "", "url": ""}
        
        def on_code(code: str, url: str) -> None:
            result_holder["code"] = code
            result_holder["url"] = url
        
        try:
            session = await oauth.login(on_code_received=on_code)
            
            if session:
                session_manager.store_session(session)
                return CommandResult.success(
                    f"[+] Logged in as **{session.user_name or session.user_email}**\n"
                    f"Provider: {provider.title()}"
                )
            else:
                return CommandResult.error(
                    "Login failed or was cancelled. Please try again."
                )
        except Exception as e:
            return CommandResult.error(f"Login error: {e}")
