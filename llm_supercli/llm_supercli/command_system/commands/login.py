"""Login command for llm_supercli."""
from typing import Any

from ..base import AsyncSlashCommand, CommandResult


class LoginCommand(AsyncSlashCommand):
    """Login with OAuth."""
    
    name = "login"
    description = "Login with OAuth (gemini, qwen, google, github)"
    usage = "[gemini|qwen|google|github]"
    examples = [
        "/login gemini   # Login to Google Gemini API",
        "/login qwen     # Login to Alibaba Qwen/DashScope",
        "/login google   # Login with Google account",
        "/login github   # Login with GitHub account",
    ]
    
    async def run_async(self, args: str = "", **kwargs: Any) -> CommandResult:
        """Execute login command."""
        from ...auth import GoogleOAuth, GitHubOAuth, GeminiOAuth, QwenOAuth, get_session_manager
        from ...constants import GOOGLE_CLIENT_ID, GITHUB_CLIENT_ID
        
        session_manager = get_session_manager()
        provider = args.strip().lower() or "gemini"
        
        valid_providers = ("google", "github", "gemini", "qwen")
        if provider not in valid_providers:
            return CommandResult.error(
                f"Unknown provider: {provider}. Use one of: {', '.join(valid_providers)}"
            )
        
        # Handle Gemini OAuth (LLM provider)
        if provider == "gemini":
            oauth = GeminiOAuth()
            if oauth.is_authenticated():
                return CommandResult.success(
                    "Already logged in to Gemini. Use `/logout gemini` to logout first."
                )
            
            try:
                session = await oauth.login()
                if session:
                    return CommandResult.success(
                        f"[+] Logged in to **Gemini** as **{session.user_email}**\n"
                        "You can now use Gemini models with `/model gemini`"
                    )
                else:
                    return CommandResult.error("Gemini login failed or was cancelled.")
            except Exception as e:
                return CommandResult.error(f"Gemini login error: {e}")
        
        # Handle Qwen OAuth (LLM provider)
        if provider == "qwen":
            oauth = QwenOAuth()
            if oauth.is_authenticated():
                return CommandResult.success(
                    "Already logged in to Qwen. Use `/logout qwen` to logout first."
                )
            
            try:
                session = await oauth.login()
                if session:
                    return CommandResult.success(
                        "[+] Logged in to **Qwen (DashScope)**\n"
                        "You can now use Qwen models with `/model qwen`"
                    )
                else:
                    return CommandResult.error("Qwen login failed or was cancelled.")
            except Exception as e:
                return CommandResult.error(f"Qwen login error: {e}")
        
        # Original Google/GitHub OAuth for account login
        if provider == "google" and not GOOGLE_CLIENT_ID:
            return CommandResult.error(
                "Google OAuth not configured.\n\n"
                "To enable Google login:\n"
                "1. Create OAuth credentials at https://console.cloud.google.com\n"
                "2. Set environment variables GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
            )
        
        if provider == "github" and not GITHUB_CLIENT_ID:
            return CommandResult.error(
                "GitHub OAuth not configured.\n\n"
                "To enable GitHub login:\n"
                "1. Create OAuth App at https://github.com/settings/developers\n"
                "2. Set environment variables GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET"
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
