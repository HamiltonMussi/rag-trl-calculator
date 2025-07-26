"""DEPRECATED: Legacy document processing module.

This module has been refactored. The functionality has been moved to:
- services/document_service.py: DocumentProcessor and DocumentChunker classes
- utils/file_utils.py: FileProcessor class

Keeping this file for backward compatibility.
"""

import logging
from typing import List, Dict

from services.document_service import DocumentProcessor
from utils.hf_models import get_just_tokenizer

logger = logging.getLogger(__name__)

# Create global instance for backward compatibility
_document_processor = DocumentProcessor()


def create_semantic_chunks(text: str, chunk_size_tokens: int = 450, chunk_overlap_tokens: int = 50) -> List[Dict]:
    """
    DEPRECATED: Legacy function for creating semantic chunks.
    
    Use services.document_service.DocumentProcessor instead.
    
    Args:
        text: Input text to chunk
        chunk_size_tokens: Target chunk size (ignored, using default)
        chunk_overlap_tokens: Overlap between chunks (ignored, using default)
        
    Returns:
        List of chunk dictionaries
    """
    # Parameters are ignored for backward compatibility
    _ = chunk_size_tokens, chunk_overlap_tokens
    
    logger.warning("Using deprecated create_semantic_chunks function. "
                  "Consider using services.document_service.DocumentProcessor.")
    
    success, chunks, error = _document_processor.process_document(text, "unknown_file")
    
    if not success:
        logger.error(f"Failed to create chunks: {error}")
        return []
    
    return chunks


def get_just_tokenizer():
    """Legacy function for getting tokenizer."""
    return get_just_tokenizer() 