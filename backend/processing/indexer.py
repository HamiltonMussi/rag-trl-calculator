"""Document indexing service with improved architecture."""

import pathlib
import logging
from typing import Dict

from utils.file_utils import FileProcessor, generate_unique_chunk_ids
from services.document_service import DocumentProcessor
from services.chromadb_service import ChromaDBService
from utils.hf_models import get_hf_embeddings

logger = logging.getLogger(__name__)

# Global processing status tracker
processing_status: Dict[str, bool] = {}

# Initialize services
chromadb_service = ChromaDBService()
document_processor = DocumentProcessor()

def is_processing(technology_id: str) -> bool:
    return processing_status.get(technology_id, False)

def remove_document_from_index(tech_id: str, filename: str) -> bool:
    """Remove all chunks related to a specific file from the ChromaDB collection."""
    logger.info(f"Removing document '{filename}' from index for tech_id: {tech_id}")
    return chromadb_service.remove_document_chunks(tech_id, filename)

def process_and_index_document(file_path: str, tech_id: str) -> bool:
    """Process and index a document for a specific technology."""
    logger.info(f"Starting document processing for file: {file_path}, tech_id: {tech_id}")
    
    global processing_status
    processing_status[tech_id] = True
    
    try:
        # Step 1: Extract text from file
        success, text_content, error = FileProcessor.extract_text(file_path)
        if not success:
            logger.error(f"Failed to extract text from {file_path}: {error}")
            return _set_processing_complete(tech_id, False)
        
        if not text_content.strip():
            logger.warning(f"No text content found in {file_path}")
            return _set_processing_complete(tech_id, False)
        
        # Step 2: Process document into chunks
        filename = pathlib.Path(file_path).name
        success, chunks_data, error = document_processor.process_document(text_content, filename)
        if not success:
            logger.error(f"Failed to process document {file_path}: {error}")
            return _set_processing_complete(tech_id, False)
        
        # Step 3: Generate embeddings
        chunk_texts = [chunk['text'] for chunk in chunks_data]
        chunk_metadatas = [chunk['metadata'] for chunk in chunks_data]
        
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks")
        chunk_embeddings = get_hf_embeddings(chunk_texts)
        
        if len(chunk_embeddings) != len(chunk_texts):
            logger.error(f"Embedding count mismatch: {len(chunk_embeddings)} vs {len(chunk_texts)}")
            return _set_processing_complete(tech_id, False)
        
        # Step 4: Generate unique IDs and store in database
        chunk_ids = generate_unique_chunk_ids(tech_id, filename, len(chunk_texts))
        
        success = chromadb_service.add_document_chunks(
            tech_id, chunk_texts, chunk_embeddings, chunk_metadatas, chunk_ids
        )
        
        if not success:
            logger.error(f"Failed to store chunks in database for {file_path}")
            return _set_processing_complete(tech_id, False)
        
        logger.info(f"Successfully indexed {len(chunk_texts)} chunks for tech_id '{tech_id}'")
        return _set_processing_complete(tech_id, True)
        
    except Exception as e:
        logger.error(f"Unexpected error processing document {file_path}: {e}", exc_info=True)
        return _set_processing_complete(tech_id, False)


def _set_processing_complete(tech_id: str, success: bool) -> bool:
    """Helper function to set processing status and return result."""
    global processing_status
    processing_status[tech_id] = False
    return success 