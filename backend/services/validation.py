"""Input validation utilities."""

import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class InputValidator:
    """Handles input validation and sanitization."""
    
    @staticmethod
    def validate_technology_id(technology_id: Optional[str]) -> str:
        """Validate and sanitize technology ID."""
        if not technology_id:
            raise ValidationError("Technology ID cannot be empty")
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', str(technology_id).strip())
        
        if len(sanitized) > 100:
            raise ValidationError("Technology ID too long (max 100 characters)")
        
        if not sanitized:
            raise ValidationError("Technology ID cannot be empty after sanitization")
        
        return sanitized
    
    @staticmethod
    def validate_question(question: Optional[str]) -> str:
        """Validate and sanitize user question."""
        if not question:
            raise ValidationError("Question cannot be empty")
        
        # Basic HTML/script tag removal for security
        sanitized = re.sub(r'<[^>]*>', '', str(question).strip())
        
        if len(sanitized) > 5000:
            raise ValidationError("Question too long (max 5000 characters)")
        
        if not sanitized:
            raise ValidationError("Question cannot be empty after sanitization")
        
        return sanitized
    
    @staticmethod
    def validate_context(context: Optional[str]) -> str:
        """Validate and sanitize context string."""
        if not context:
            return "Nenhum contexto específico encontrado para esta pergunta."
        
        # Basic sanitization
        sanitized = str(context).strip()
        
        if len(sanitized) > 50000:
            logger.warning(f"Context very long ({len(sanitized)} chars), truncating")
            sanitized = sanitized[:50000] + "...[TRUNCATED]"
        
        return sanitized
    
    @staticmethod
    def validate_model_id(model_id: Optional[str]) -> str:
        """Validate model ID format."""
        if not model_id:
            raise ValidationError("Model ID cannot be empty")
        
        # Basic validation for HuggingFace model ID format
        if not re.match(r'^[a-zA-Z0-9._/-]+$', model_id):
            raise ValidationError("Invalid model ID format")
        
        return model_id.strip()
    
    @staticmethod
    def validate_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate message format for LLM."""
        if not messages:
            raise ValidationError("Messages list cannot be empty")
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValidationError(f"Message {i} must be a dictionary")
            
            if 'role' not in msg or 'content' not in msg:
                raise ValidationError(f"Message {i} must have 'role' and 'content' fields")
            
            if msg['role'] not in ['system', 'user', 'assistant']:
                raise ValidationError(f"Invalid role in message {i}: {msg['role']}")
            
            if not isinstance(msg['content'], str):
                raise ValidationError(f"Content in message {i} must be a string")
        
        return messages