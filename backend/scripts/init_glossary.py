#!/usr/bin/env python3
"""
Glossary initialization script for TRL RAG system.
This script processes the glossario.txt file and indexes it into the ChromaDB 'trl' collection
with the same metadata structure as other document indexing.
"""

import pathlib
import logging
import sys
import os

# Add the backend directory to Python path
backend_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from processing.document_processor import create_semantic_chunks
from utils.hf_models import get_hf_embeddings
from chromadb import PersistentClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_glossary():
    """Initialize the TRL glossary collection from the glossario.txt file."""
    
    # Paths
    ROOT = pathlib.Path(__file__).parent.parent
    data_dir = ROOT / "data"
    glossary_file = data_dir / "glossario.txt"
    store_dir = ROOT / "store"
    
    # Check if glossary file exists
    if not glossary_file.exists():
        logger.error(f"Glossary file not found: {glossary_file}")
        return False
    
    # Initialize ChromaDB client
    client = PersistentClient(str(store_dir))
    
    try:
        # Read glossary content
        logger.info(f"Reading glossary file: {glossary_file}")
        with open(glossary_file, "r", encoding="utf-8") as f:
            text_content = f.read()
        
        if not text_content.strip():
            logger.error("Glossary file is empty")
            return False
        
        logger.info(f"Successfully read {len(text_content)} characters from glossary file")
        
        # Create semantic chunks
        logger.info("Creating semantic chunks from glossary content...")
        chunks_data = create_semantic_chunks(text_content)
        logger.info(f"Created {len(chunks_data)} chunks from glossary")
        
        if not chunks_data:
            logger.error("No chunks created from glossary content")
            return False
        
        # Add metadata consistent with other document processing
        filename = glossary_file.name
        for chunk in chunks_data:
            chunk['metadata']['source'] = filename
            chunk['metadata']['type'] = 'glossary_chunk'
        
        # Prepare data for ChromaDB
        chunk_texts = [chunk['text'] for chunk in chunks_data]
        chunk_metadatas = [chunk['metadata'] for chunk in chunks_data]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
        chunk_embeddings = get_hf_embeddings(chunk_texts)
        logger.info(f"Generated embeddings for {len(chunk_texts)} chunks")
        
        if len(chunk_embeddings) != len(chunk_texts):
            logger.error(f"Mismatch in chunks ({len(chunk_texts)}) and embeddings ({len(chunk_embeddings)})")
            return False
        
        # Get or create TRL collection
        collection_name = "trl"
        logger.info(f"Creating/accessing ChromaDB collection '{collection_name}'")
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Check if collection already has data
        existing_count = collection.count()
        if existing_count > 0:
            logger.warning(f"TRL collection already contains {existing_count} items. Clearing before reindexing...")
            # Clear existing data
            existing_data = collection.get()
            if existing_data['ids']:
                collection.delete(ids=existing_data['ids'])
                logger.info("Cleared existing TRL collection data")
        
        # Generate unique IDs for glossary chunks
        unique_ids = [f"trl_glossary_{i}" for i in range(len(chunk_texts))]
        
        # Add to collection
        logger.info(f"Adding {len(chunk_texts)} chunks to TRL collection...")
        collection.add(
            documents=chunk_texts,
            embeddings=chunk_embeddings,
            metadatas=chunk_metadatas,
            ids=unique_ids
        )
        
        logger.info(f"Successfully indexed {len(chunk_texts)} glossary chunks into '{collection_name}' collection")
        
        # Verify the data was added
        final_count = collection.count()
        logger.info(f"TRL collection now contains {final_count} items")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing glossary: {str(e)}", exc_info=True)
        return False

def check_trl_collection():
    """Check if TRL collection exists and has data."""
    ROOT = pathlib.Path(__file__).parent.parent
    store_dir = ROOT / "store"
    
    try:
        client = PersistentClient(str(store_dir))
        collection = client.get_collection("trl")
        count = collection.count()
        logger.info(f"TRL collection exists with {count} items")
        return count > 0
    except Exception as e:
        logger.info(f"TRL collection does not exist or is empty: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting glossary initialization script...")
    
    # Check if TRL collection already has data
    if check_trl_collection():
        logger.info("TRL collection already exists with data. Use --force to reinitialize.")
        if "--force" not in sys.argv:
            sys.exit(0)
    
    # Initialize glossary
    success = init_glossary()
    
    if success:
        logger.info("Glossary initialization completed successfully!")
        sys.exit(0)
    else:
        logger.error("Glossary initialization failed!")
        sys.exit(1)