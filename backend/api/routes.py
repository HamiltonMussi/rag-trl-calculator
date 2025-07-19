"""API routes with improved error handling and validation."""

from fastapi import APIRouter, BackgroundTasks, status
from fastapi.responses import JSONResponse
from .schemas import (
    Ask, FileUpload, ProcessingStatus, SetTechnologyContext,
    ErrorResponse, FileUploadResponse, ProcessingStatusResponse,
    SetTechnologyContextResponse, AnswerResponse
)
import base64
import pathlib
import os
import traceback
from processing.indexer import process_and_index_document, is_processing
from retrieval.context_retriever import get_cached_search, trim_for_ctx
from llm.response_generator import generate_llm_response, build_llm_prompt_and_messages
from services.session_manager import SessionManager
from services.validation import ValidationError
import asyncio
import logging
import uuid
import json

router = APIRouter()

logger = logging.getLogger("trl-api")
UPLOAD_ROOT = pathlib.Path(__file__).parent.parent / "uploads"
UPLOAD_ROOT.mkdir(exist_ok=True)

# Initialize session manager
SESSIONS_FILE = pathlib.Path(__file__).parent.parent / "sessions.json"
session_manager = SessionManager(SESSIONS_FILE)


def handle_api_error(error: Exception, error_msg: str, status_code: int = 500) -> JSONResponse:
    """Standardized error handling for API endpoints."""
    logger.error(f"{error_msg}: {error}", exc_info=True)
    
    if isinstance(error, ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                detail=str(error),
                error_code="VALIDATION_ERROR"
            ).model_dump()
        )
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            detail=error_msg,
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )

@router.post("/upload-files", response_model=FileUploadResponse)
async def upload_files(data: FileUpload, background_tasks: BackgroundTasks):
    """
    Upload files for a technology with support for chunked uploads.
    
    Args:
        data: File upload data including base64 content
        background_tasks: FastAPI background tasks for processing
        
    Returns:
        Upload status and processing information
    """
    try:
        logger.info(
            f"Received /upload-files request for technology_id: {data.technology_id}, "
            f"filename: {data.filename}, chunk: {data.chunk_index}, final: {data.final}"
        )
        
        # Create technology directory
        tech_dir = UPLOAD_ROOT / data.technology_id
        tech_dir.mkdir(exist_ok=True)
        
        # Decode base64 content
        try:
            file_bytes = base64.b64decode(data.content_base64)
        except Exception as e:
            raise ValidationError(f"Invalid base64 payload: {e}")
        
        # Write file (append for chunks > 0)
        target = tech_dir / data.filename
        append_mode = 'ab' if data.chunk_index > 0 else 'wb'
        
        with open(target, append_mode) as fh:
            fh.write(file_bytes)
        
        if data.final:
            # Process document in background
            logger.info(
                f"Adding process_and_index_document task to background for "
                f"{data.filename}, tech_id: {data.technology_id}"
            )
            background_tasks.add_task(process_and_index_document, str(target), data.technology_id)
            
            return FileUploadResponse(
                status="ok",
                stored_as=str(target),
                processing="started"
            )
        else:
            logger.info(
                f"Received partial file chunk {data.chunk_index} for "
                f"{data.filename}, tech_id: {data.technology_id}"
            )
            
            return FileUploadResponse(
                status="partial",
                index=data.chunk_index
            )
            
    except ValidationError as e:
        return handle_api_error(e, "Validation error in file upload", 422)
    except Exception as e:
        return handle_api_error(e, "Error processing file upload")

@router.post("/status", response_model=ProcessingStatusResponse)
async def check_status(data: ProcessingStatus):
    """
    Check if a document is still being processed.
    
    Args:
        data: Processing status request data
        
    Returns:
        Current processing status for the technology
    """
    try:
        logger.info(f"Received /status request for technology_id: {data.technology_id}")
        
        processing = is_processing(data.technology_id)
        current_status = "processing" if processing else "ready"
        
        logger.info(f"Returning status for {data.technology_id}: {current_status}")
        
        return ProcessingStatusResponse(
            technology_id=data.technology_id,
            status=current_status
        )
        
    except Exception as e:
        return handle_api_error(e, "Error checking processing status")

@router.post("/set-technology-context", response_model=SetTechnologyContextResponse)
async def set_technology_context(data: SetTechnologyContext):
    """
    Set the technology context for a session.
    
    Args:
        data: Technology context data
        
    Returns:
        Session information with assigned technology context
    """
    try:
        session_id = session_manager.set_technology_context(
            data.technology_id, 
            data.session_id
        )
        
        # Cleanup old sessions periodically
        if session_manager.get_session_count() > 500:
            session_manager.cleanup_sessions(400)
        
        return SetTechnologyContextResponse(
            session_id=session_id,
            technology_id=data.technology_id,
            status="context_set"
        )
        
    except Exception as e:
        return handle_api_error(e, "Error setting technology context")

@router.post("/answer", response_model=AnswerResponse)
async def answer(data: Ask):
    """
    Generate answers to questions about a technology.
    
    Args:
        data: Question and context data
        
    Returns:
        Generated answer with metadata
    """
    try:
        # Get technology_id from request or session
        technology_id = data.technology_id
        if not technology_id and data.session_id:
            technology_id = session_manager.get_technology_context(data.session_id)
        
        if not technology_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    detail="No technology_id provided. Either include technology_id in request or set technology context first.",
                    error_code="MISSING_TECHNOLOGY_ID"
                ).model_dump()
            )
        
        logger.info(
            f"Received /answer request for technology_id: '{technology_id}', "
            f"session_id: '{data.session_id}', question: '{data.question[:100]}...'"
        )
        
        # Check if still processing
        if is_processing(technology_id):
            logger.warning(f"Attempt to answer for tech_id '{technology_id}' while it is processing.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=ErrorResponse(
                    detail=f"Document for technology_id '{technology_id}' is still being processed. Please wait and try again.",
                    error_code="STILL_PROCESSING"
                ).model_dump()
            )
        
        # Retrieve context
        passages = get_cached_search(data.question, tech_id=technology_id, k=6)
        if not passages:
            logger.warning(
                f"No passages found by get_cached_search for tech_id '{technology_id}', "
                f"question '{data.question[:100]}...'"
            )
            context = "Nenhum contexto específico encontrado para esta pergunta."
        else:
            logger.info(f"Retrieved {len(passages)} passages for context. Trimming...")
            context = trim_for_ctx(passages)
            logger.info(f"Context after trimming (length: {len(context)} chars): '{context[:200]}...'")
        
        # Build prompt and generate response
        system_prompt, messages = build_llm_prompt_and_messages(technology_id, context, data.question)
        
        logger.debug("=== Preparing messages for LLM ===")
        logger.debug(f"System Prompt length: {len(system_prompt)} chars")
        logger.debug(f"User Message length: {len(messages[1]['content'])} chars")
        logger.debug("=================================")
        
        response_content = await asyncio.to_thread(generate_llm_response, messages=messages)
        
        logger.info(
            f"LLM response for tech_id '{technology_id}', question '{data.question[:100]}...' -> "
            f"Response length: {len(response_content)} chars"
        )
        
        return AnswerResponse(
            answer=response_content,
            technology_id=technology_id,
            session_id=data.session_id
        )
        
    except ValidationError as e:
        return handle_api_error(e, "Validation error in answer generation", 422)
    except ValueError as e:
        logger.error("ValueError in /answer", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                detail=str(e),
                error_code="NOT_FOUND"
            ).model_dump()
        )
    except Exception as e:
        return handle_api_error(e, "Error generating answer") 