from typing import List, Dict
import asyncio
from chromadb import PersistentClient
from hf_utils import get_hf_embeddings, get_llm_tokenizer, get_just_tokenizer
import pathlib
from functools import lru_cache
import numpy as np
import PyPDF2
import time
import re
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Added logger specific to this module
logger = logging.getLogger(__name__)

ROOT = pathlib.Path(__file__).parent
client = PersistentClient(str(ROOT / "store"))
col = client.get_or_create_collection("trl")

# Track processing status for each technology_id
processing_status: Dict[str, bool] = {}

def is_processing(technology_id: str) -> bool:
    """Check if a document is still being processed"""
    return processing_status.get(technology_id, False)

async def batch_get_embeddings(chunks: List[str]):
    """Get embeddings for a list of text chunks using Hugging Face"""
    if not chunks:
        return []
    return get_hf_embeddings(chunks)

def get_cached_search(question: str, tech_id: str, k: int) -> List[Dict]:
    """Search for relevant chunks. Returns a list of dicts with 'text' and 'metadata'."""
    logger.info(f"get_cached_search called with question: '{question[:100]}...', tech_id: '{tech_id}', k: {k}")
    if tech_id and is_processing(tech_id):
        logger.warning(f"Attempt to search for tech_id '{tech_id}' while it is still processing.")
        raise ValueError("Document is still being processed. Please wait.")
        
    q_emb = get_hf_embeddings([question])[0]

    if not tech_id:
        target_collection_name = "trl"
    else:
        target_collection_name = f"tech_{tech_id}"

    current_collection = client.get_or_create_collection(target_collection_name)
    logger.info(f"Querying collection '{target_collection_name}' for tech_id '{tech_id if tech_id else 'glossary'}'")
    
    res = current_collection.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas"]
    )
    
    results = []
    if res and res["documents"] and len(res["documents"][0]) > 0:
        docs = res["documents"][0]
        metas = res["metadatas"][0] if res["metadatas"] and len(res["metadatas"][0]) == len(docs) else [{}] * len(docs)
        
        for doc_text, meta_info in zip(docs, metas):
            source_doc_name = f"Documento ID {tech_id}" if tech_id else "Glossário TRL"
            section_name = meta_info.get('section', 'N/A')
            if not tech_id and meta_info.get('type') == 'glossary_chunk':
                section_name = f"Termo(s): {meta_info.get('terms', 'N/A')}"
            
            results.append({
                "text": doc_text,
                "metadata": meta_info,
                "source_document": source_doc_name,
                "source_section": section_name
            })

    logger.info(f"Retrieved {len(results)} passage objects from ChromaDB for '{tech_id if tech_id else 'glossary'}'.")
    if results:
        logger.info(f"First retrieved passage object example: text='{results[0]['text'][:50]}...', source_document='{results[0]['source_document']}', source_section='{results[0]['source_section']}'")
    return results

def create_semantic_chunks(text, chunk_size_tokens=450, chunk_overlap_tokens=50):
    """
    Create semantic chunks from text using RecursiveCharacterTextSplitter, 
    respecting academic sections if found. Uses LLM tokenizer for token counting.
    """
    tokenizer = get_just_tokenizer()
    logger.info(f"create_semantic_chunks called. Text length: {len(text)} chars. Target chunk size: {chunk_size_tokens} tokens, Overlap: {chunk_overlap_tokens} tokens.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_tokens,
        chunk_overlap=chunk_overlap_tokens,
        length_function=lambda x: len(tokenizer.encode(x)),
        is_separator_regex=False,
    )

    sections_map = {
        # Define in order of expected appearance for potential sequential processing if desired later
        'abstract': [], 'introduction': [], 'methodology': [], 
        'results': [], 'discussion': [], 'conclusion': [], 
        'references': [], # Added common section: References/Bibliografia
        'appendices': [], # Added common section: Appendices/Anexos
        'other': [] # Catch-all for text not fitting into known sections
    }
    # Improved regex: accounts for optional numbering (e.g., 1., 1.1), case-insensitivity, and common terms.
    section_headers = {
        'abstract':   r'(?i)^\s*(?:\d+\.?\s*)?(?:abstract|resumo|sumário executivo)\b',
        'introduction': r'(?i)^\s*(?:\d+\.?\s*)?(?:introduction|introdução)\b',
        'methodology':r'(?i)^\s*(?:\d+\.?\s*)?(?:methodology|methods|materials and methods|metodologia|materiais e métodos)\b',
        'results':    r'(?i)^\s*(?:\d+\.?\s*)?(?:results|resultados)\b',
        'discussion': r'(?i)^\s*(?:\d+\.?\s*)?(?:discussion|discussão)\b',
        'conclusion': r'(?i)^\s*(?:\d+\.?\s*)?(?:conclusion|conclusions|conclusão|conclusões)\b',
        'references': r'(?i)^\s*(?:\d+\.?\s*)?(?:references|referências|bibliografia)\b',
        'appendices': r'(?i)^\s*(?:\d+\.?\s*)?(?:appendix|appendices|anexo|anexos)\b'
        # 'other' is not in headers; it's the default bucket.
    }
    current_section_key = 'other'
    current_section_texts_buffer = []
    paragraphs = text.split('\n\n')
    logger.info(f"Initial coarse split into {len(paragraphs)} paragraphs for section detection.")

    for para in paragraphs:
        para_strip = para.strip()
        if not para_strip:
            current_section_texts_buffer.append(para)
            continue
        
        matched_section = False
        first_line_of_para = para_strip.split('\n')[0]
        for section_key, pattern in section_headers.items():
            if re.search(pattern, first_line_of_para):
                if current_section_texts_buffer:
                    sections_map[current_section_key].append("\n\n".join(current_section_texts_buffer))
                    current_section_texts_buffer = []
                current_section_key = section_key
                header_plus_content = para_strip.split('\n', 1)
                if len(header_plus_content) > 1 and header_plus_content[1].strip():
                    current_section_texts_buffer.append(header_plus_content[1].strip())
                matched_section = True
                break
        if not matched_section:
            current_section_texts_buffer.append(para)
    
    if current_section_texts_buffer:
        sections_map[current_section_key].append("\n\n".join(current_section_texts_buffer))

    final_chunks = []
    processed_text_overall = "" # Keep track of text already chunked from specific sections

    # Priority 1: Process well-defined sections first
    defined_section_keys = ['abstract', 'introduction', 'methodology', 'results', 'discussion', 'conclusion', 'references', 'appendices']
    
    for section_name in defined_section_keys:
        section_text_list = sections_map.get(section_name, [])
        full_section_text = "\n\n".join(section_text_list).strip()
        if not full_section_text:
            continue
        
        processed_text_overall += full_section_text + "\n\n" # Mark this text as processed
        logger.info(f"Splitting specific section '{section_name}' (length {len(full_section_text)} chars) with RecursiveCharacterTextSplitter.")
        split_section_texts = text_splitter.split_text(full_section_text)
        for i, chunk_text in enumerate(split_section_texts):
            token_count = len(tokenizer.encode(chunk_text))
            final_chunks.append({
                'text': chunk_text,
                'section': section_name,
                'metadata': {'section': section_name, 'chunk_in_section': i + 1, 'char_length': len(chunk_text), 'token_count': token_count}
            })
        logger.info(f"Section '{section_name}' yielded {len(split_section_texts)} chunks.")

    # Priority 2: Process the 'other' section (text that didn't fit into defined sections)
    other_section_text_list = sections_map.get('other', [])
    full_other_text = "\n\n".join(other_section_text_list).strip()
    
    # Check if 'other' text substantially differs from what was already processed from defined sections
    # This is a heuristic. A more robust way would be to only chunk text from 'other' that wasn't part of a defined section.
    # However, the current section populating logic should mostly prevent overlaps in sections_map's lists.
    if full_other_text:
        logger.info(f"Splitting 'other' section (length {len(full_other_text)} chars) with RecursiveCharacterTextSplitter.")
        split_other_texts = text_splitter.split_text(full_other_text)
        for i, chunk_text in enumerate(split_other_texts):
            token_count = len(tokenizer.encode(chunk_text))
            final_chunks.append({
                'text': chunk_text,
                'section': 'other',
                'metadata': {'section': 'other', 'chunk_in_section': i + 1, 'char_length': len(chunk_text), 'token_count': token_count}
            })
        logger.info(f"Section 'other' yielded {len(split_other_texts)} chunks.")
    
    # Fallback: If no chunks were created at all (e.g. very short doc, or all text filtered out by section logic)
    # and the original text is not empty, split the original entire text.
    if not final_chunks and text.strip():
        logger.warning("No chunks created from section-based processing, and original text is not empty. Attempting to split the entire document as a fallback.")
        split_texts = text_splitter.split_text(text) 
        for i, chunk_text in enumerate(split_texts):
            token_count = len(tokenizer.encode(chunk_text))
            final_chunks.append({
                'text': chunk_text,
                'section': 'full_document_fallback',
                'metadata': {'section': 'full_document_fallback', 'chunk_num': i + 1, 'char_length': len(chunk_text), 'token_count': token_count}
            })
        logger.info(f"Fallback full document splitting yielded {len(split_texts)} chunks.")

    logger.info(f"Total chunks created by create_semantic_chunks: {len(final_chunks)}.")
    if final_chunks:
        logger.info(f"First chunk (total {len(final_chunks)}): '{final_chunks[0]['text'][:100]}...', metadata: {final_chunks[0]['metadata']}")
        if len(final_chunks) > 1:
            logger.info(f"Last chunk (total {len(final_chunks)}): '{final_chunks[-1]['text'][:100]}...', metadata: {final_chunks[-1]['metadata']}")
        else:
            logger.info(f"Only one chunk created: '{final_chunks[0]['text'][:100]}...', metadata: {final_chunks[0]['metadata']}")

    return final_chunks

def process_and_index_document(file_path: str, tech_id: str):
    """
    Process and index a document using semantic chunking.
    Handles PDF and TXT files.
    """
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
                    # Potentially try OCR or another library as a fallback here if needed
                else:
                    logger.info(f"Successfully extracted {len(text_content)} characters from PDF: {file_path}")
            except Exception as e:
                logger.error(f"Error extracting text from PDF {file_path} using PyPDF2: {e}", exc_info=True)
                processing_status[tech_id] = False
                return False
        elif file_extension == ".txt" or file_extension == ".md": # Add other plain text types if needed
            logger.info(f"Reading plain text file: {file_path}")
            # Read the document (copied from previous logic for txt)
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
                    logger.warning(
                        f"Both utf-8 and latin-1 decode failed for {file_path}; "
                        "used utf-8 with replacement characters."
                    )
        else:
            logger.warning(f"Unsupported file type '{file_extension}' for {file_path}. Skipping processing.")
            processing_status[tech_id] = False
            return False
        
        if not text_content.strip():
            logger.warning(f"No text content extracted or read from {file_path}. Aborting indexing.")
            processing_status[tech_id] = False
            return False
            
        # Create semantic chunks
        logger.info(f"Calling create_semantic_chunks for content from {file_path}...")
        chunks_data = create_semantic_chunks(text_content) # Pass extracted text_content
        logger.info(f"create_semantic_chunks returned {len(chunks_data)} chunks for {file_path}.")

        if not chunks_data:
            logger.warning(f"No chunks created for document {file_path}, tech_id {tech_id}. Aborting indexing for this file.")
            processing_status[tech_id] = False
            return False

        # Save chunks to a text file for inspection
        chunk_dump_filename = original_file_path.stem + "_chunks.txt"
        chunk_dump_path = original_file_path.parent / chunk_dump_filename
        try:
            with open(chunk_dump_path, "w", encoding="utf-8") as f_dump:
                f_dump.write(f"--- Chunks for {original_file_path.name} (tech_id: {tech_id}) ---\n\n")
                for i, chunk_dict in enumerate(chunks_data):
                    f_dump.write(f"=== Chunk {i+1} (Section: {chunk_dict.get('section', 'N/A')}, Tokens: {chunk_dict.get('metadata', {}).get('token_count', 'N/A')}) ===\n")
                    f_dump.write(chunk_dict['text'] + "\n\n")
            logger.info(f"Successfully saved {len(chunks_data)} chunks to {chunk_dump_path}")
        except Exception as e:
            logger.error(f"Error saving chunks to file {chunk_dump_path}: {e}", exc_info=True)
            # Continue processing even if saving chunks fails

        chunk_texts = [chunk['text'] for chunk in chunks_data]
        chunk_metadatas = [chunk['metadata'] for chunk in chunks_data]
        
        logging.info(f"Generating embeddings for {len(chunk_texts)} chunks from {file_path}...")
        chunk_embeddings = get_hf_embeddings(chunk_texts)
        logger.info(f"Embeddings generated for {len(chunk_texts)} chunks from {file_path}.")

        if len(chunk_embeddings) != len(chunk_texts):
            logger.error(f"Mismatch in number of chunks ({len(chunk_texts)}) and embeddings ({len(chunk_embeddings)}) for {file_path}. Skipping indexing.")
            processing_status[tech_id] = False
            return False

        # Initialize ChromaDB for the specific technology_id
        collection_name = f"tech_{tech_id}"
        logger.info(f"Preparing to add {len(chunk_texts)} chunks to ChromaDB collection '{collection_name}'. First chunk ID will be '{tech_id}_0'.") # Log example ID
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection '{collection_name}' obtained/created.")

        # Add chunks to collection
        logger.info(f"Attempting to add {len(chunk_texts)} items to collection '{collection_name}'...")
        collection.add(
            documents=chunk_texts,
            embeddings=chunk_embeddings,
            metadatas=chunk_metadatas,
            ids=[f"{tech_id}_{i}" for i in range(len(chunk_texts))]
        )
        logger.info(f"Successfully indexed {len(chunk_texts)} chunks for tech_id '{tech_id}' into collection '{collection_name}'.")
        processing_status[tech_id] = False
        return True
    except Exception as e:
        logging.error(f"Error processing document {file_path} for {tech_id}: {str(e)}", exc_info=True)
        processing_status[tech_id] = False
        return False

def trim_for_ctx(passages: List[Dict], limit: int = 3500) -> str:
    """Builds a context string from passages, prefixing each with its source.
       Trims the context to a token limit if necessary.
    """
    tokenizer = get_just_tokenizer()
    total_tokens = 0
    selected_context_parts = []
    final_context_str = ""

    if not passages:
        logger.warning("trim_for_ctx received no passages.")
        return "Nenhum contexto específico encontrado."

    for passage_obj in passages:
        text = passage_obj.get("text", "")
        source_doc = passage_obj.get("source_document", "Fonte Desconhecida")
        source_sec = passage_obj.get("source_section", "Seção Desconhecida")
        
        # Format the chunk with its source
        # Example: "(Fonte: Documento ID 374, Seção: Introduction)
        #           Texto do chunk..." 
        # The SYSTEM_PROMPT already prepares the LLM for "Fonte: NomedoDocumento.pdf, Seção: Introdução"
        # Let's match that formatting style for consistency. We need the actual PDF name if possible.
        # For now, using the structure from get_cached_search.

        # To get the actual filename for tech_id documents, we might need to list the dir
        # or store it in metadata when `process_and_index_document` runs.
        # Current `source_document` is `Documento ID {tech_id}` or `Glossário TRL`.
        # This is a good start for the LLM to cite.

        formatted_source_prefix = f"Fonte: {source_doc}, Seção: {source_sec}\n"
        full_passage_text_with_source = formatted_source_prefix + text
        
        passage_tokens = len(tokenizer.encode(full_passage_text_with_source))
        
        if total_tokens + passage_tokens <= limit:
            selected_context_parts.append(full_passage_text_with_source)
            total_tokens += passage_tokens
        else:
            # Current passage would exceed limit. Try to take a portion if it's the first one.
            if not selected_context_parts: # This is the first passage and it's already too long
                logger.warning(f"First passage itself (source: {source_doc}, {source_sec}) with {passage_tokens} tokens exceeds limit {limit}. Truncating it.")
                # Truncate this single oversized passage
                # We need to encode, truncate token IDs, then decode to be accurate.
                token_ids = tokenizer.encode(full_passage_text_with_source)
                truncated_token_ids = token_ids[:limit]
                # Ensure we don't cut in the middle of a character if it's multi-byte
                truncated_text = tokenizer.decode(truncated_token_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
                selected_context_parts.append(truncated_text)
                total_tokens = len(tokenizer.encode(truncated_text)) # Re-calculate actual tokens after decode
                logger.info(f"Context will consist of one truncated passage with {total_tokens} tokens.")
            else:
                logger.info(f"Context limit reached. Not including further passage from {source_doc}, {source_sec} ({passage_tokens} tokens). Current total: {total_tokens}.")
            break # Stop adding more passages
    
    final_context_str = "\n\n---\n\n".join(selected_context_parts)
    logger.info(f"Final trimmed context to {total_tokens} tokens. Number of selected passages/parts: {len(selected_context_parts)}.")
    if not final_context_str.strip() and passages: # If somehow ended up empty but had passages
        logger.warning("Context string is empty after trimming, but passages were provided. This might be due to a very small token limit or issues with the first passage.")
        return "Contexto fornecido era muito grande para o limite de tokens e não pôde ser incluído." 
        
    return final_context_str if final_context_str.strip() else "Nenhum contexto específico pôde ser preparado dentro do limite de tokens."