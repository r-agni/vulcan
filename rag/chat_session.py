"""
Chat session management for multi-turn conversations
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json


@dataclass
class ChatMessage:
    """Single message in a chat conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ChatSession:
    """Chat session with conversation history"""
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    messages: List[ChatMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """
        Add a message to the conversation

        Args:
            role: "user" or "assistant"
            content: Message content
            metadata: Additional metadata (sources, tool_calls, etc.)
        """
        message = ChatMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_updated = datetime.utcnow().isoformat()

    def get_messages(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get conversation messages

        Args:
            limit: Limit number of messages (most recent)

        Returns:
            List of messages
        """
        if limit:
            return self.messages[-limit:]
        return self.messages

    def get_context_for_claude(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Get messages formatted for Claude API

        Args:
            max_messages: Maximum number of messages to include

        Returns:
            List of message dicts for Claude
        """
        messages = self.get_messages(limit=max_messages)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.last_updated = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata
        }


class ChatSessionManager:
    """Manage multiple chat sessions"""

    def __init__(self, session_timeout_minutes: int = 60):
        """
        Initialize session manager

        Args:
            session_timeout_minutes: Session timeout in minutes
        """
        self.sessions: Dict[str, ChatSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)

    def create_session(self, metadata: Dict[str, Any] = None) -> ChatSession:
        """
        Create a new chat session

        Args:
            metadata: Session metadata

        Returns:
            New ChatSession object
        """
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            metadata=metadata or {}
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get session by ID

        Args:
            session_id: Session ID

        Returns:
            ChatSession or None if not found
        """
        session = self.sessions.get(session_id)
        if session:
            # Check if session has timed out
            last_updated = datetime.fromisoformat(session.last_updated)
            if datetime.utcnow() - last_updated > self.session_timeout:
                print(f"Session {session_id} has timed out")
                self.delete_session(session_id)
                return None
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired = []

        for session_id, session in self.sessions.items():
            last_updated = datetime.fromisoformat(session.last_updated)
            if now - last_updated > self.session_timeout:
                expired.append(session_id)

        for session_id in expired:
            self.delete_session(session_id)

        if expired:
            print(f"Cleaned up {len(expired)} expired sessions")

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active sessions

        Returns:
            List of session dictionaries
        """
        self.cleanup_expired_sessions()
        return [session.to_dict() for session in self.sessions.values()]

    def count_sessions(self) -> int:
        """
        Count active sessions

        Returns:
            Number of active sessions
        """
        self.cleanup_expired_sessions()
        return len(self.sessions)


# Global session manager instance
_session_manager = None


def get_session_manager() -> ChatSessionManager:
    """
    Get global session manager instance

    Returns:
        ChatSessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = ChatSessionManager(session_timeout_minutes=60)
    return _session_manager
