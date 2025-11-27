"""
Chat session storage for llm_supercli.
Manages persistent storage and retrieval of chat sessions and messages.
"""
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .db import Database, get_database
from ..utils import generate_session_id, truncate_string


@dataclass
class Message:
    """Represents a single chat message."""
    role: str
    content: str
    timestamp: float = 0
    tokens: int = 0
    cost: float = 0.0
    metadata: dict = field(default_factory=dict)
    id: Optional[int] = None
    
    def __post_init__(self) -> None:
        if self.timestamp == 0:
            self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API calls."""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class ChatSession:
    """Represents a chat session with messages."""
    id: str = ""
    title: str = "New Chat"
    provider: str = ""
    model: str = ""
    system_prompt: Optional[str] = None
    created_at: float = 0
    updated_at: float = 0
    message_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    is_favorite: bool = False
    metadata: dict = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_session_id()
        if self.created_at == 0:
            self.created_at = time.time()
        if self.updated_at == 0:
            self.updated_at = self.created_at
    
    def add_message(self, role: str, content: str, tokens: int = 0, cost: float = 0.0) -> Message:
        """
        Add a message to the session.
        
        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            tokens: Token count
            cost: Cost in USD
            
        Returns:
            Created Message object
        """
        msg = Message(
            role=role,
            content=content,
            tokens=tokens,
            cost=cost
        )
        self.messages.append(msg)
        self.message_count = len(self.messages)
        self.total_tokens += tokens
        self.total_cost += cost
        self.updated_at = time.time()
        
        if self.title == "New Chat" and role == "user":
            self.title = truncate_string(content, 50)
        
        return msg
    
    def get_context(self, max_messages: Optional[int] = None) -> list[dict]:
        """
        Get messages formatted for LLM context.
        
        Args:
            max_messages: Optional limit on number of messages
            
        Returns:
            List of message dicts
        """
        messages = self.messages
        if max_messages:
            messages = messages[-max_messages:]
        
        context = []
        if self.system_prompt:
            context.append({"role": "system", "content": self.system_prompt})
        
        context.extend([msg.to_dict() for msg in messages])
        return context
    
    def clear_messages(self) -> None:
        """Clear all messages from session."""
        self.messages.clear()
        self.message_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.updated_at = time.time()
    
    def rewind(self, count: int = 1) -> list[Message]:
        """
        Remove the last N messages.
        
        Args:
            count: Number of messages to remove
            
        Returns:
            Removed messages
        """
        removed = []
        for _ in range(min(count, len(self.messages))):
            msg = self.messages.pop()
            removed.append(msg)
            self.total_tokens -= msg.tokens
            self.total_cost -= msg.cost
        
        self.message_count = len(self.messages)
        self.updated_at = time.time()
        return removed


class SessionStore:
    """
    Manages persistent storage of chat sessions.
    
    Provides CRUD operations and search functionality for sessions.
    """
    
    def __init__(self, db: Optional[Database] = None) -> None:
        """
        Initialize session store.
        
        Args:
            db: Optional database instance
        """
        self._db = db or get_database()
        self._current_session: Optional[ChatSession] = None
    
    @property
    def current_session(self) -> Optional[ChatSession]:
        """Get the current active session."""
        return self._current_session
    
    def create_session(
        self,
        provider: str = "",
        model: str = "",
        system_prompt: Optional[str] = None,
        title: str = "New Chat"
    ) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            provider: LLM provider name
            model: Model name
            system_prompt: Optional system prompt
            title: Session title
            
        Returns:
            New ChatSession
        """
        session = ChatSession(
            title=title,
            provider=provider,
            model=model,
            system_prompt=system_prompt
        )
        
        self._db.insert("sessions", {
            "id": session.id,
            "title": session.title,
            "provider": session.provider,
            "model": session.model,
            "system_prompt": session.system_prompt,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "message_count": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "is_favorite": 0,
            "metadata": json.dumps(session.metadata)
        })
        
        self._current_session = session
        return session
    
    def save_session(self, session: Optional[ChatSession] = None) -> None:
        """
        Save a session to the database.
        
        Args:
            session: Session to save (uses current if not provided)
        """
        session = session or self._current_session
        if not session:
            return
        
        session.updated_at = time.time()
        
        self._db.update(
            "sessions",
            {
                "title": session.title,
                "provider": session.provider,
                "model": session.model,
                "system_prompt": session.system_prompt,
                "updated_at": session.updated_at,
                "message_count": session.message_count,
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost,
                "is_favorite": 1 if session.is_favorite else 0,
                "metadata": json.dumps(session.metadata)
            },
            "id = ?",
            (session.id,)
        )
    
    def save_message(self, session_id: str, message: Message) -> int:
        """
        Save a message to the database.
        
        Args:
            session_id: Session ID
            message: Message to save
            
        Returns:
            Message ID
        """
        msg_id = self._db.insert("messages", {
            "session_id": session_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp,
            "tokens": message.tokens,
            "cost": message.cost,
            "metadata": json.dumps(message.metadata)
        })
        message.id = msg_id
        return msg_id
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Load a session from the database.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            ChatSession or None if not found
        """
        row = self._db.fetch_one(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        
        if not row:
            return None
        
        session = ChatSession(
            id=row["id"],
            title=row["title"],
            provider=row["provider"],
            model=row["model"],
            system_prompt=row["system_prompt"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=row["message_count"],
            total_tokens=row["total_tokens"],
            total_cost=row["total_cost"],
            is_favorite=bool(row["is_favorite"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
        
        message_rows = self._db.fetch_all(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        
        for msg_row in message_rows:
            session.messages.append(Message(
                id=msg_row["id"],
                role=msg_row["role"],
                content=msg_row["content"],
                timestamp=msg_row["timestamp"],
                tokens=msg_row["tokens"],
                cost=msg_row["cost"],
                metadata=json.loads(msg_row["metadata"]) if msg_row["metadata"] else {}
            ))
        
        self._current_session = session
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its messages.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted
        """
        self._db.delete("messages", "session_id = ?", (session_id,))
        rows = self._db.delete("sessions", "id = ?", (session_id,))
        
        if self._current_session and self._current_session.id == session_id:
            self._current_session = None
        
        return rows > 0
    
    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        favorites_only: bool = False
    ) -> list[dict]:
        """
        List sessions with basic info.
        
        Args:
            limit: Maximum number of sessions
            offset: Pagination offset
            favorites_only: Filter to favorites only
            
        Returns:
            List of session info dicts
        """
        query = "SELECT id, title, provider, model, created_at, updated_at, message_count, is_favorite FROM sessions"
        params: list = []
        
        if favorites_only:
            query += " WHERE is_favorite = 1"
        
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = self._db.fetch_all(query, tuple(params))
        
        return [dict(row) for row in rows]
    
    def search_sessions(self, query: str, limit: int = 20) -> list[dict]:
        """
        Search sessions by title or message content.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching session info dicts
        """
        search_pattern = f"%{query}%"
        
        rows = self._db.fetch_all("""
            SELECT DISTINCT s.id, s.title, s.provider, s.model, 
                   s.created_at, s.updated_at, s.message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.title LIKE ? OR m.content LIKE ?
            ORDER BY s.updated_at DESC
            LIMIT ?
        """, (search_pattern, search_pattern, limit))
        
        return [dict(row) for row in rows]
    
    def set_current_session(self, session: ChatSession) -> None:
        """Set the current active session."""
        self._current_session = session
    
    def get_session_count(self) -> int:
        """Get total number of sessions."""
        row = self._db.fetch_one("SELECT COUNT(*) as count FROM sessions")
        return row["count"] if row else 0
    
    def get_total_usage(self) -> dict:
        """
        Get total usage statistics.
        
        Returns:
            Dict with tokens and cost totals
        """
        row = self._db.fetch_one("""
            SELECT SUM(total_tokens) as tokens, SUM(total_cost) as cost
            FROM sessions
        """)
        
        return {
            "tokens": row["tokens"] or 0,
            "cost": row["cost"] or 0.0
        } if row else {"tokens": 0, "cost": 0.0}


_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
