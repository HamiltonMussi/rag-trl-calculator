from fastapi import APIRouter, HTTPException, BackgroundTasks
from .schemas import Ask, FileUpload, ProcessingStatus, SetTechnologyContext
import base64
import pathlib
import os
import traceback
from processing.indexer import process_and_index_document, is_processing
from retrieval.context_retriever import get_cached_search, trim_for_ctx
from llm.response_generator import generate_llm_response, build_llm_prompt_and_messages
import asyncio
import logging
import uuid
import json

router = APIRouter()

log = logging.getLogger("trl-api")
UPLOAD_ROOT = pathlib.Path(__file__).parent.parent / "uploads"
UPLOAD_ROOT.mkdir(exist_ok=True)

# Persistent session store for technology_id
SESSIONS_FILE = pathlib.Path(__file__).parent.parent / "sessions.json"

def load_sessions():
    """Load sessions from file"""
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Could not load sessions file: {e}")
    return {}

def save_sessions(sessions_dict):
    """Save sessions to file"""
    try:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions_dict, f)
    except Exception as e:
        log.error(f"Could not save sessions file: {e}")

# Initialize sessions from file
sessions = load_sessions()

@router.post("/upload-files")
async def upload_files(data: FileUpload, background_tasks: BackgroundTasks):
    log.info(f"Received /upload-files request for technology_id: {data.technology_id}, filename: {data.filename}, chunk: {data.chunk_index}, final: {data.final}")
    tech_dir = UPLOAD_ROOT / data.technology_id
    tech_dir.mkdir(exist_ok=True)
    try:
        file_bytes = base64.b64decode(data.content_base64)
    except Exception as e:
        raise HTTPException(400, f"Invalid base‑64 payload: {e}")

    target = tech_dir / data.filename
    append_mode = 'ab' if data.chunk_index > 0 else 'wb'
    with open(target, append_mode) as fh:
        fh.write(file_bytes)

    if data.final:
        # Process document in background
        log.info(f"Adding process_and_index_document task to background for {data.filename}, tech_id: {data.technology_id}")
        background_tasks.add_task(process_and_index_document, str(target), data.technology_id)
        return {"status": "ok", "stored_as": str(target), "processing": "started"}
    else:
        log.info(f"Received partial file chunk {data.chunk_index} for {data.filename}, tech_id: {data.technology_id}")
        return {"status": "partial", "index": data.chunk_index}

@router.post("/status")
async def check_status(data: ProcessingStatus):
    """Check if a document is still being processed"""
    log.info(f"Received /status request for technology_id: {data.technology_id}")
    processing = is_processing(data.technology_id)
    status_response = {
        "technology_id": data.technology_id,
        "status": "processing" if processing else "ready"
    }
    log.info(f"Returning status for {data.technology_id}: {status_response['status']}")
    return status_response

@router.post("/set-technology-context")
async def set_technology_context(data: SetTechnologyContext):
    """Set the technology context for a session"""
    session_id = data.session_id or str(uuid.uuid4())
    sessions[session_id] = data.technology_id
    save_sessions(sessions)  # Persist session to file
    log.info(f"Set technology context for session {session_id}: {data.technology_id}")
    return {
        "session_id": session_id,
        "technology_id": data.technology_id,
        "status": "context_set"
    }

@router.post("/answer")
async def answer(data: Ask):
    # Get technology_id from request or session
    technology_id = data.technology_id
    if not technology_id and data.session_id:
        technology_id = sessions.get(data.session_id)
    
    if not technology_id:
        raise HTTPException(
            status_code=400,
            detail="No technology_id provided. Either include technology_id in request or set technology context first."
        )
    
    log.info(f"Received /answer request for technology_id: '{technology_id}', session_id: '{data.session_id}', question: '{data.question[:100]}...'" )
    try:
        if is_processing(technology_id):
            log.warning(f"Attempt to answer for tech_id '{technology_id}' while it is processing.")
            raise HTTPException(
                status_code=409,
                detail=f"Document for technology_id '{technology_id}' is still being processed. Please wait and try again."
            )
        passages = get_cached_search(data.question, tech_id=technology_id, k=6)
        if not passages:
            log.warning(f"No passages found by get_cached_search for tech_id '{technology_id}', question '{data.question[:100]}...'" )
            context = "Nenhum contexto específico encontrado para esta pergunta."
        else:
            log.info(f"Retrieved {len(passages)} passages for context. Trimming...")
            context = trim_for_ctx(passages)
            log.info(f"Context after trimming (length: {len(context)} chars): '{context[:200]}...'")
        # Use the shared function to build prompt and messages
        system_prompt, messages = build_llm_prompt_and_messages(technology_id, context, data.question)
        log.info("=== Preparing messages for LLM ===")
        log.info(f"System Prompt part:\n{system_prompt}")
        log.info(f"User Message part (with context and question):\n{messages[1]['content']}")
        log.info("=================================")
        response_content = await asyncio.to_thread(generate_llm_response, messages=messages)
        log.info(f"LLM response for tech_id '{technology_id}', question '{data.question[:100]}...' -> Response: '{response_content[:200]}...'")
        return response_content
    except ValueError as e:
        log.error("Error in /answer", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error("Error in /answer", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 