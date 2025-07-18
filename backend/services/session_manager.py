"""Session management service for technology contexts."""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages technology contexts for user sessions."""
    
    def __init__(self, sessions_file: Path):
        self.sessions_file = sessions_file
        self._sessions: Dict[str, str] = {}
        self._lock = Lock()
        self._load_sessions()
    
    def _load_sessions(self) -> None:
        """Load sessions from file."""
        try:
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r') as f:
                    self._sessions = json.load(f)
                logger.info(f"Loaded {len(self._sessions)} sessions from file")
            else:
                logger.info("No existing sessions file found, starting with empty sessions")
        except Exception as e:
            logger.warning(f"Could not load sessions file: {e}")
            self._sessions = {}
    
    def _save_sessions(self) -> None:
        """Save sessions to file."""
        try:
            with open(self.sessions_file, 'w') as f:
                json.dump(self._sessions, f, indent=2)
            logger.debug(f"Saved {len(self._sessions)} sessions to file")
        except Exception as e:
            logger.error(f"Could not save sessions file: {e}")
    
    def set_technology_context(
        self, 
        technology_id: str, 
        session_id: Optional[str] = None
    ) -> str:
        """
        Set technology context for a session.
        
        Args:
            technology_id: Technology identifier
            session_id: Optional session ID (will be generated if not provided)
            
        Returns:
            Session ID
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        with self._lock:
            self._sessions[session_id] = technology_id
            self._save_sessions()
        
        logger.info(f"Set technology context for session {session_id}: {technology_id}")
        return session_id
    
    def get_technology_context(self, session_id: str) -> Optional[str]:
        """
        Get technology context for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Technology ID if found, None otherwise
        """
        with self._lock:
            return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was removed, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._save_sessions()
                logger.info(f"Removed session: {session_id}")
                return True
            return False
    
    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        with self._lock:
            return len(self._sessions)
    
    def cleanup_sessions(self, max_sessions: int = 1000) -> int:
        """
        Clean up old sessions if count exceeds limit.
        
        Args:
            max_sessions: Maximum number of sessions to keep
            
        Returns:
            Number of sessions removed
        """
        with self._lock:
            current_count = len(self._sessions)
            if current_count <= max_sessions:
                return 0
            
            # Remove oldest sessions (simple FIFO)
            sessions_to_remove = current_count - max_sessions
            session_ids = list(self._sessions.keys())[:sessions_to_remove]
            
            for session_id in session_ids:
                del self._sessions[session_id]
            
            self._save_sessions()
            logger.info(f"Cleaned up {sessions_to_remove} old sessions")
            return sessions_to_remove