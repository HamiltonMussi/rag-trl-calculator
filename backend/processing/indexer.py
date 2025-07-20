import pathlib
import logging
import PyPDF2
from processing.document_processor import create_semantic_chunks
from utils.hf_models import get_hf_embeddings
from chromadb import PersistentClient
from typing import Dict

logger = logging.getLogger(__name__)
ROOT = pathlib.Path(__file__).parent.parent
client = PersistentClient(str(ROOT / "store"))
processing_status: Dict[str, bool] = {}

def is_processing(technology_id: str) -> bool:
    return processing_status.get(technology_id, False)

def remove_document_from_index(tech_id: str, filename: str):
    """Remove all chunks related to a specific file from the ChromaDB collection."""
    logger.info(f"Starting remove_document_from_index for file: {filename}, tech_id: {tech_id}")
    try:
        collection_name = f"tech_{tech_id}"
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Get all documents from the collection to find ones related to this file
        results = collection.get()
        
        # Find IDs of chunks that belong to this file
        ids_to_remove = []
        for i, metadata in enumerate(results['metadatas']):
            if metadata and metadata.get('source') == filename:
                ids_to_remove.append(results['ids'][i])
        
        if ids_to_remove:
            collection.delete(ids=ids_to_remove)
            logger.info(f"Successfully removed {len(ids_to_remove)} chunks for file '{filename}' from collection '{collection_name}'.")
            return True
        else:
            logger.info(f"No chunks found for file '{filename}' in collection '{collection_name}'.")
            return True
            
    except Exception as e:
        logger.error(f"Error removing document {filename} from index for {tech_id}: {str(e)}", exc_info=True)
        return False

def process_and_index_document(file_path: str, tech_id: str):
    logger.info(f"Starting process_and_index_document for file: {file_path}, tech_id: {tech_id}")
    global processing_status
    processing_status[tech_id] = True
    text_content = ""
    try:
        original_file_path = pathlib.Path(file_path)
        file_extension = original_file_path.suffix.lower()
        logger.info(f"Detected file extension: {file_extension} for {file_path}")
        if file_extension == ".pdf":
            logger.info(f"Attempting to extract text from PDF: {file_path}")
            try:
                with open(file_path, "rb") as f_pdf:
                    reader = PyPDF2.PdfReader(f_pdf)
                    extracted_pages = []
                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        extracted_pages.append(page.extract_text() or "")
                    text_content = "\n".join(extracted_pages)
                if not text_content.strip():
                    logger.warning(f"PyPDF2 extracted no text from PDF: {file_path}")
                else:
                    logger.info(f"Successfully extracted {len(text_content)} characters from PDF: {file_path}")
            except Exception as e:
                logger.error(f"Error extracting text from PDF {file_path} using PyPDF2: {e}", exc_info=True)
                processing_status[tech_id] = False
                return False
        elif file_extension in [".txt", ".md"]:
            logger.info(f"Reading plain text file: {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        text_content = f.read()
                    logger.warning(f"utf-8 decode failed for {file_path}; fell back to latin-1.")
                except UnicodeDecodeError:
                    with open(file_path, "rb") as f:
                        raw = f.read()
                    text_content = raw.decode("utf-8", errors="replace")
                    logger.warning(f"Both utf-8 and latin-1 decode failed for {file_path}; used utf-8 with replacement characters.")
        else:
            logger.warning(f"Unsupported file type '{file_extension}' for {file_path}. Skipping processing.")
            processing_status[tech_id] = False
            return False
        if not text_content.strip():
            logger.warning(f"No text content extracted or read from {file_path}. Aborting indexing.")
            processing_status[tech_id] = False
            return False
        logger.info(f"Calling create_semantic_chunks for content from {file_path}...")
        chunks_data = create_semantic_chunks(text_content)
        logger.info(f"create_semantic_chunks returned {len(chunks_data)} chunks for {file_path}.")
        
        # Add source filename to metadata
        filename = pathlib.Path(file_path).name
        for chunk in chunks_data:
            chunk['metadata']['source'] = filename
        if not chunks_data:
            logger.warning(f"No chunks created for document {file_path}, tech_id {tech_id}. Aborting indexing for this file.")
            processing_status[tech_id] = False
            return False
        chunk_texts = [chunk['text'] for chunk in chunks_data]
        chunk_metadatas = [chunk['metadata'] for chunk in chunks_data]
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks from {file_path}...")
        chunk_embeddings = get_hf_embeddings(chunk_texts)
        logger.info(f"Embeddings generated for {len(chunk_texts)} chunks from {file_path}.")
        if len(chunk_embeddings) != len(chunk_texts):
            logger.error(f"Mismatch in number of chunks ({len(chunk_texts)}) and embeddings ({len(chunk_embeddings)}) for {file_path}. Skipping indexing.")
            processing_status[tech_id] = False
            return False
        collection_name = f"tech_{tech_id}"
        logger.info(f"Preparing to add {len(chunk_texts)} chunks to ChromaDB collection '{collection_name}'.")
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection '{collection_name}' obtained/created.")
        logger.info(f"Attempting to add {len(chunk_texts)} items to collection '{collection_name}'...")
        # Generate unique IDs that include filename to prevent collisions
        filename = pathlib.Path(file_path).name
        filename_safe = filename.replace('.', '_').replace('-', '_')
        unique_ids = [f"{tech_id}_{filename_safe}_{i}" for i in range(len(chunk_texts))]
        
        collection.add(
            documents=chunk_texts,
            embeddings=chunk_embeddings,
            metadatas=chunk_metadatas,
            ids=unique_ids
        )
        logger.info(f"Successfully indexed {len(chunk_texts)} chunks for tech_id '{tech_id}' into collection '{collection_name}'.")
        processing_status[tech_id] = False
        return True
    except Exception as e:
        logger.error(f"Error processing document {file_path} for {tech_id}: {str(e)}", exc_info=True)
        processing_status[tech_id] = False
        return False 