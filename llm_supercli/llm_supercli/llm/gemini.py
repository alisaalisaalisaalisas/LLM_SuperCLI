"""
Google Gemini LLM provider implementation for llm_supercli.
Uses REST API with OAuth or API key authentication.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import httpx

from .base import LLMProvider, LLMResponse, ProviderConfig, StreamChunk


class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider using REST API.
    
    Supports:
    - API key authentication (GEMINI_API_KEY env var)
    - OAuth credentials from ~/.gemini/oauth_creds.json (gemini-cli style)
    
    OAuth uses Vertex AI endpoint which requires:
    - Google Cloud project with Vertex AI API enabled
    - OAuth token with cloud-platform scope
    """
    
    GENAI_URL = "https://generativelanguage.googleapis.com/v1beta"
    # Vertex AI endpoint for OAuth (gemini-cli compatible)
    VERTEX_AI_URL = "https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models"
    DEFAULT_REGION = "us-central1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        config = self._default_config()
        if api_key:
            config.api_key = api_key
        if model:
            config.default_model = model
        super().__init__(config)
        
        if model:
            self._model = model
        
        self._oauth_token = None
        self._oauth_refresh_token = None
        self._oauth_expiry = 0
        self._project_id = None
        self._region = self.DEFAULT_REGION
        self._use_vertex_ai = False  # Use Vertex AI for OAuth (gemini-cli style)
        self._load_oauth_if_needed()
    
    def _default_config(self) -> ProviderConfig:
        return ProviderConfig(
            name="Gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            default_model="gemini-2.0-flash",
            available_models=[
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-flash-8b",
                "gemini-1.5-pro",
            ],
            max_tokens=8192,
            supports_streaming=True,
            supports_functions=True,
            rate_limit_rpm=60,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )
    
    def _load_oauth_if_needed(self):
        """Load OAuth credentials from file (gemini-cli compatible)."""
        if self._api_key:
            return
        
        gemini_dir = Path(os.path.expanduser("~/.gemini"))
        oauth_path = gemini_dir / "oauth_creds.json"
        
        if not oauth_path.exists():
            return
        
        try:
            with open(oauth_path, 'r') as f:
                creds = json.load(f)
            
            self._oauth_token = creds.get('access_token')
            self._oauth_refresh_token = creds.get('refresh_token')
            self._oauth_expiry = creds.get('expiry_date', 0)
            
            # Load project ID from settings.json (gemini-cli style)
            settings_path = gemini_dir / "settings.json"
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    self._project_id = settings.get('project_id')
                    self._region = settings.get('region', self.DEFAULT_REGION)
            
            # Fallback to environment variables
            if not self._project_id:
                self._project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
            
            # OAuth requires Vertex AI endpoint
            if self._oauth_token and self._project_id:
                self._use_vertex_ai = True
                print(f"[Gemini] OAuth mode: project={self._project_id}, region={self._region}")
            elif self._oauth_token:
                print("[Gemini] Warning: OAuth found but no project ID")
                print("[Gemini] Set project_id in ~/.gemini/settings.json or GOOGLE_CLOUD_PROJECT env var")
                
        except Exception as e:
            print(f"[Gemini] Warning: Failed to load OAuth: {e}")
    
    def _ensure_valid_token(self):
        """Ensure we have a valid OAuth token."""
        if self._google_creds:
            try:
                from google.auth.transport.requests import Request
                if self._google_creds.expired and self._google_creds.refresh_token:
                    self._google_creds.refresh(Request())
                    self._oauth_token = self._google_creds.token
                    self._save_oauth_token()
            except Exception:
                pass
    
    def _save_oauth_token(self):
        """Save updated OAuth token to file."""
        oauth_path = Path(os.path.expanduser("~/.gemini/oauth_creds.json"))
        try:
            with open(oauth_path, 'r') as f:
                creds = json.load(f)
            
            creds['access_token'] = self._oauth_token
            creds['expiry_date'] = self._oauth_expiry
            
            with open(oauth_path, 'w') as f:
                json.dump(creds, f, indent=2)
        except Exception:
            pass  # Ignore save errors
    
    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        
        if self._oauth_token:
            headers["Authorization"] = f"Bearer {self._oauth_token}"
            # Required for OAuth billing/quota
            if self._project_id:
                headers["x-goog-user-project"] = self._project_id
        
        return headers
    
    def _get_url(self, model: str, action: str = "generateContent") -> str:
        """Build the API URL (gemini-cli compatible)."""
        if self._api_key:
            return f"{self.GENAI_URL}/models/{model}:{action}?key={self._api_key}"
        elif self._use_vertex_ai and self._project_id:
            # Vertex AI endpoint for OAuth (gemini-cli style)
            return f"https://{self._region}-aiplatform.googleapis.com/v1/projects/{self._project_id}/locations/{self._region}/publishers/google/models/{model}:{action}"
        else:
            # Fallback to Generative Language API
            return f"{self.GENAI_URL}/models/{model}:{action}"
    
    def _convert_messages(self, messages: list[dict]) -> tuple[list, Optional[str]]:
        """Convert OpenAI-style messages to Gemini format."""
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
                continue
            elif role == "assistant":
                role = "model"
            elif role == "tool":
                # Handle tool response
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"Tool result: {content}"}]
                })
                continue
            
            contents.append({
                "role": role,
                "parts": [{"text": content}]
            })
        
        return contents, system_instruction
    
    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """Send a chat completion request to Gemini."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        # Ensure valid OAuth token
        if self._oauth_token:
            self._ensure_valid_token()
        
        contents, system_instruction = self._convert_messages(messages)
        
        # Build request payload
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Handle tools if provided
        tools_param = kwargs.pop("tools", None)
        if tools_param:
            payload["tools"] = self._convert_tools(tools_param)
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._get_url(model),
                headers=self._get_headers(),
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Extract response content
        content = ""
        raw_response = {"model": model, "choices": [{"message": {}}]}
        
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                for part in parts:
                    if "text" in part:
                        content = part["text"]
                    elif "functionCall" in part:
                        # Convert to OpenAI-compatible format
                        fc = part["functionCall"]
                        raw_response["choices"][0]["message"] = {
                            "content": None,
                            "tool_calls": [{
                                "id": f"call_{int(time.time())}",
                                "type": "function",
                                "function": {
                                    "name": fc.get("name", ""),
                                    "arguments": json.dumps(fc.get("args", {}))
                                }
                            }]
                        }
        
        # Get token counts
        input_tokens = 0
        output_tokens = 0
        if "usageMetadata" in data:
            input_tokens = data["usageMetadata"].get("promptTokenCount", 0)
            output_tokens = data["usageMetadata"].get("candidatesTokenCount", 0)
        
        return LLMResponse(
            content=content,
            model=model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=self.calculate_cost(input_tokens, output_tokens),
            finish_reason="stop",
            latency_ms=latency_ms,
            raw_response=raw_response
        )
    
    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> AsyncGenerator[StreamChunk, None]:
        """Send a streaming chat completion request to Gemini."""
        model = model or self._model
        temperature = temperature if temperature is not None else self._config.temperature
        max_tokens = max_tokens or self._config.max_tokens
        
        if self._oauth_token:
            self._ensure_valid_token()
        
        contents, system_instruction = self._convert_messages(messages)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self._get_url(model, "streamGenerateContent"),
                headers=self._get_headers(),
                json=payload,
                timeout=120.0
            ) as response:
                response.raise_for_status()
                
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # Parse JSON objects from buffer
                    while True:
                        try:
                            # Try to find complete JSON object
                            if buffer.startswith("["):
                                buffer = buffer[1:]
                            if buffer.startswith(","):
                                buffer = buffer[1:]
                            if buffer.startswith("]"):
                                break
                            
                            # Find end of JSON object
                            brace_count = 0
                            end_idx = -1
                            for i, c in enumerate(buffer):
                                if c == '{':
                                    brace_count += 1
                                elif c == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_idx = i + 1
                                        break
                            
                            if end_idx == -1:
                                break
                            
                            json_str = buffer[:end_idx]
                            buffer = buffer[end_idx:]
                            
                            data = json.loads(json_str)
                            
                            if "candidates" in data and data["candidates"]:
                                candidate = data["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            yield StreamChunk(
                                                content=part["text"],
                                                finish_reason=None,
                                                model=model
                                            )
                        except json.JSONDecodeError:
                            break
    
    def _convert_tools(self, tools: list) -> list:
        """Convert OpenAI-style tools to Gemini format."""
        function_declarations = []
        
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                function_declarations.append({
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {})
                })
        
        if function_declarations:
            return [{"functionDeclarations": function_declarations}]
        return []
    
    async def list_models(self) -> list[str]:
        """List available models."""
        return self._config.available_models
