"""API request and response schemas with validation."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
import re

class Ask(BaseModel):
    """Request schema for asking questions about a technology."""
    question: str = Field(
        ..., 
        min_length=1, 
        max_length=5000,
        description="Question about the technology"
    )
    technology_id: Optional[str] = Field(
        None, 
        max_length=100,
        description="Technology identifier"
    )
    session_id: Optional[str] = Field(
        None, 
        max_length=100,
        description="Session identifier"
    )
    doc_ids: Optional[List[str]] = Field(
        None,
        description="Optional document IDs to search in"
    )
    
    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        # Remove potentially dangerous HTML/script tags
        cleaned = re.sub(r'<[^>]*>', '', v.strip())
        if not cleaned:
            raise ValueError('Question cannot be empty after sanitization')
        return cleaned
    
    @validator('technology_id')
    def validate_technology_id(cls, v):
        if v is not None:
            # Remove potentially dangerous characters
            cleaned = re.sub(r'[<>"\']', '', v.strip())
            if not cleaned:
                raise ValueError('Technology ID cannot be empty after sanitization')
            return cleaned
        return v

class SetTechnologyContext(BaseModel):
    """Request schema for setting technology context in a session."""
    technology_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Technology identifier"
    )
    session_id: Optional[str] = Field(
        None, 
        max_length=100,
        description="Session identifier (will be generated if not provided)"
    )
    
    @validator('technology_id')
    def validate_technology_id(cls, v):
        cleaned = re.sub(r'[<>"\']', '', v.strip())
        if not cleaned:
            raise ValueError('Technology ID cannot be empty after sanitization')
        return cleaned

class FileUpload(BaseModel):
    """Request schema for file upload."""
    technology_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Technology identifier"
    )
    filename: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Name of the file being uploaded"
    )
    content_base64: str = Field(
        ..., 
        min_length=1,
        description="Base64 encoded file content"
    )
    chunk_index: int = Field(
        0, 
        ge=0,
        description="Chunk index for multi-part uploads"
    )
    final: bool = Field(
        True,
        description="Whether this is the final chunk"
    )
    
    @validator('technology_id')
    def validate_technology_id(cls, v):
        cleaned = re.sub(r'[<>"\']', '', v.strip())
        if not cleaned:
            raise ValueError('Technology ID cannot be empty after sanitization')
        return cleaned
    
    @validator('filename')
    def validate_filename(cls, v):
        # Basic filename validation
        if not re.match(r'^[a-zA-Z0-9._-]+\.[a-zA-Z0-9]+$', v):
            raise ValueError('Invalid filename format')
        return v

class ProcessingStatus(BaseModel):
    """Request schema for checking processing status."""
    technology_id: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Technology identifier"
    )
    
    @validator('technology_id')
    def validate_technology_id(cls, v):
        cleaned = re.sub(r'[<>"\']', '', v.strip())
        if not cleaned:
            raise ValueError('Technology ID cannot be empty after sanitization')
        return cleaned


# Response schemas
class ErrorResponse(BaseModel):
    """Standard error response schema."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    

class FileUploadResponse(BaseModel):
    """Response schema for file upload."""
    status: Literal["ok", "partial"] = Field(..., description="Upload status")
    stored_as: Optional[str] = Field(None, description="File storage path")
    processing: Optional[str] = Field(None, description="Processing status")
    index: Optional[int] = Field(None, description="Chunk index for partial uploads")


class ProcessingStatusResponse(BaseModel):
    """Response schema for processing status."""
    technology_id: str = Field(..., description="Technology identifier")
    status: Literal["processing", "ready"] = Field(..., description="Processing status")


class SetTechnologyContextResponse(BaseModel):
    """Response schema for setting technology context."""
    session_id: str = Field(..., description="Session identifier")
    technology_id: str = Field(..., description="Technology identifier")
    status: Literal["context_set"] = Field(..., description="Operation status")


class AnswerResponse(BaseModel):
    """Response schema for question answers."""
    answer: str = Field(..., description="Generated answer")
    technology_id: str = Field(..., description="Technology identifier used")
    session_id: Optional[str] = Field(None, description="Session identifier if applicable") 