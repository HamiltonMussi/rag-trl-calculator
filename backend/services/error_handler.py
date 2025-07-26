"""Centralized error handling and validation service."""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standard error codes for the application."""
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # File processing errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    EMPTY_FILE = "EMPTY_FILE"
    
    # Processing errors
    DOCUMENT_PROCESSING_ERROR = "DOCUMENT_PROCESSING_ERROR"
    EMBEDDING_GENERATION_ERROR = "EMBEDDING_GENERATION_ERROR"
    CHUNKING_ERROR = "CHUNKING_ERROR"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_OPERATION_ERROR = "DATABASE_OPERATION_ERROR"
    COLLECTION_NOT_FOUND = "COLLECTION_NOT_FOUND"
    
    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    INVALID_SESSION = "INVALID_SESSION"
    
    # Processing state errors
    STILL_PROCESSING = "STILL_PROCESSING"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    
    # LLM errors
    LLM_GENERATION_ERROR = "LLM_GENERATION_ERROR"
    LLM_CONFIG_ERROR = "LLM_CONFIG_ERROR"
    
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"


@dataclass
class ApplicationError:
    """Structured error information."""
    
    code: ErrorCode
    message: str
    details: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        result = {
            "error_code": self.code.value,
            "message": self.message
        }
        
        if self.details:
            result["details"] = self.details
            
        if self.context:
            result["context"] = self.context
            
        return result


class ErrorHandler:
    """Centralized error handling service."""
    
    @staticmethod
    def create_validation_error(message: str, details: str = None) -> ApplicationError:
        """Create a validation error."""
        return ApplicationError(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details
        )
    
    @staticmethod
    def create_file_error(message: str, file_path: str = None, error_code: ErrorCode = ErrorCode.FILE_READ_ERROR) -> ApplicationError:
        """Create a file-related error."""
        context = {"file_path": file_path} if file_path else None
        return ApplicationError(
            code=error_code,
            message=message,
            context=context
        )
    
    @staticmethod
    def create_database_error(message: str, operation: str = None) -> ApplicationError:
        """Create a database-related error."""
        context = {"operation": operation} if operation else None
        return ApplicationError(
            code=ErrorCode.DATABASE_OPERATION_ERROR,
            message=message,
            context=context
        )
    
    @staticmethod
    def create_processing_error(message: str, tech_id: str = None, error_code: ErrorCode = ErrorCode.DOCUMENT_PROCESSING_ERROR) -> ApplicationError:
        """Create a processing-related error."""
        context = {"technology_id": tech_id} if tech_id else None
        return ApplicationError(
            code=error_code,
            message=message,
            context=context
        )
    
    @staticmethod
    def log_and_create_error(
        error: Exception, 
        message: str, 
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        context: Dict[str, Any] = None
    ) -> ApplicationError:
        """Log exception and create structured error."""
        logger.error(f"{message}: {error}", exc_info=True)
        
        return ApplicationError(
            code=error_code,
            message=message,
            details=str(error),
            context=context
        )


class ValidationService:
    """Input validation service."""
    
    @staticmethod
    def validate_file_upload(filename: str, content_base64: str, technology_id: str) -> Optional[ApplicationError]:
        """Validate file upload parameters."""
        if not filename:
            return ErrorHandler.create_validation_error("Filename is required")
        
        if not content_base64:
            return ErrorHandler.create_validation_error("File content is required")
        
        if not technology_id:
            return ErrorHandler.create_validation_error("Technology ID is required")
        
        # Check file extension
        if not any(filename.lower().endswith(ext) for ext in ['.pdf', '.txt', '.md']):
            return ErrorHandler.create_file_error(
                f"Unsupported file type: {filename}",
                filename,
                ErrorCode.UNSUPPORTED_FILE_TYPE
            )
        
        return None
    
    @staticmethod
    def validate_question(question: str) -> Optional[ApplicationError]:
        """Validate question input."""
        if not question:
            return ErrorHandler.create_validation_error("Question is required")
        
        if len(question.strip()) < 3:
            return ErrorHandler.create_validation_error("Question must be at least 3 characters long")
        
        if len(question) > 5000:
            return ErrorHandler.create_validation_error("Question is too long (max 5000 characters)")
        
        return None
    
    @staticmethod
    def validate_technology_id(tech_id: str) -> Optional[ApplicationError]:
        """Validate technology ID."""
        if not tech_id:
            return ErrorHandler.create_validation_error("Technology ID is required")
        
        if not tech_id.strip():
            return ErrorHandler.create_validation_error("Technology ID cannot be empty")
        
        # Basic format validation (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in '-_' for c in tech_id):
            return ErrorHandler.create_validation_error(
                "Technology ID can only contain letters, numbers, hyphens, and underscores"
            )
        
        return None
    
    @staticmethod
    def validate_session_id(session_id: str) -> Optional[ApplicationError]:
        """Validate session ID format."""
        if not session_id:
            return ErrorHandler.create_validation_error("Session ID is required")
        
        # Basic UUID format check (simple validation)
        if len(session_id) < 8:
            return ErrorHandler.create_validation_error("Invalid session ID format")
        
        return None


def handle_service_result(success: bool, result: Any, error_message: str, context: Dict[str, Any] = None) -> Tuple[bool, Any, Optional[ApplicationError]]:
    """
    Handle service operation results with consistent error handling.
    
    Args:
        success: Whether the operation was successful
        result: The result data (if successful)
        error_message: Error message (if unsuccessful)
        context: Additional context for error
        
    Returns:
        Tuple of (success, result_or_none, error_or_none)
    """
    if success:
        return True, result, None
    
    error = ErrorHandler.create_processing_error(error_message, context=context)
    return False, None, error