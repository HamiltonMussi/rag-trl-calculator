from typing import List, Dict
import logging
from processing.indexer import is_processing
from processing.document_processor import get_just_tokenizer
from utils.hf_models import get_hf_embeddings
import pathlib
from chromadb import PersistentClient

logger = logging.getLogger(__name__)

ROOT = pathlib.Path(__file__).parent.parent
client = PersistentClient(str(ROOT / "store"))
col = client.get_or_create_collection("trl")

def get_cached_search(question: str, tech_id: str, k: int) -> List[Dict]:
    logger.info(f"get_cached_search called with question: '{question[:100]}...', tech_id: '{tech_id}', k: {k}")
    if is_processing(tech_id):
        logger.warning(f"Attempt to search for tech_id '{tech_id}' while it is still processing.")
        raise ValueError("Document is still being processed. Please wait.")
    
    q_emb = get_hf_embeddings([question])[0]
    all_candidates = []
    
    # Search technology-specific collection
    tech_collection_name = f"tech_{tech_id}"
    tech_collection = client.get_or_create_collection(tech_collection_name)
    logger.info(f"Querying collection '{tech_collection_name}' for tech_id '{tech_id}'")
    tech_res = tech_collection.query(
        query_embeddings=[q_emb],
        n_results=k * 2,  # Get more candidates to ensure good ranking
        include=["documents", "metadatas", "distances"]
    )
    tech_candidates = _process_collection_results_with_scores(tech_res, tech_id=tech_id)
    all_candidates.extend(tech_candidates)
    
    # Always search TRL collection for universal glossary context
    trl_collection = client.get_or_create_collection("trl")
    logger.info(f"Querying TRL collection for universal glossary context")
    trl_res = trl_collection.query(
        query_embeddings=[q_emb],
        n_results=k * 2,  # Get more candidates to ensure good ranking
        include=["documents", "metadatas", "distances"]
    )
    trl_candidates = _process_collection_results_with_scores(trl_res, tech_id=None)
    all_candidates.extend(trl_candidates)
    
    # Sort all candidates by similarity score (lower distance = higher similarity)
    all_candidates.sort(key=lambda x: x['distance'])
    
    # Take the top k results based on similarity
    results = [candidate for candidate in all_candidates[:k]]
    
    # Count results by source for logging
    tech_count = sum(1 for r in results if r['source_document'] != 'Glossário TRL')
    trl_count = len(results) - tech_count
    
    logger.info(f"Selected top {len(results)} results by similarity: {tech_count} from tech collection, {trl_count} from TRL collection")
    logger.info(f"Retrieved {len(results)} total passage objects from ChromaDB")
    if results:
        logger.info(f"First result (best similarity): text='{results[0]['text'][:50]}...', source='{results[0]['source_document']}', distance={results[0]['distance']:.4f}")
    
    return results

def _process_collection_results_with_scores(res, tech_id: str = None) -> List[Dict]:
    """Process ChromaDB query results with similarity scores into standardized format."""
    results = []
    if res and res["documents"] and len(res["documents"][0]) > 0:
        docs = res["documents"][0]
        metas = res["metadatas"][0] if res["metadatas"] and len(res["metadatas"][0]) == len(docs) else [{}] * len(docs)
        distances = res["distances"][0] if res["distances"] and len(res["distances"][0]) == len(docs) else [float('inf')] * len(docs)
        
        for doc_text, meta_info, distance in zip(docs, metas, distances):
            if tech_id:
                # For technology documents, use filename from metadata
                source_doc_name = meta_info.get('source', f'Tech {tech_id} Document')
            else:
                source_doc_name = "Glossário TRL"
            
            section_name = meta_info.get('section', 'N/A')
            if not tech_id and meta_info.get('type') == 'glossary_chunk':
                section_name = f"Termo(s): {meta_info.get('terms', 'N/A')}"
            
            results.append({
                "text": doc_text,
                "metadata": meta_info,
                "source_document": source_doc_name,
                "source_section": section_name,
                "distance": distance
            })
    return results

def _process_collection_results(res, tech_id: str = None) -> List[Dict]:
    """Process ChromaDB query results into standardized format (backward compatibility)."""
    results = []
    if res and res["documents"] and len(res["documents"][0]) > 0:
        docs = res["documents"][0]
        metas = res["metadatas"][0] if res["metadatas"] and len(res["metadatas"][0]) == len(docs) else [{}] * len(docs)
        for doc_text, meta_info in zip(docs, metas):
            if tech_id:
                # For technology documents, use filename from metadata
                source_doc_name = meta_info.get('source', f'Tech {tech_id} Document')
            else:
                source_doc_name = "Glossário TRL"
            
            section_name = meta_info.get('section', 'N/A')
            if not tech_id and meta_info.get('type') == 'glossary_chunk':
                section_name = f"Termo(s): {meta_info.get('terms', 'N/A')}"
            
            results.append({
                "text": doc_text,
                "metadata": meta_info,
                "source_document": source_doc_name,
                "source_section": section_name
            })
    return results

def trim_for_ctx(passages: List[Dict], limit: int = 3500) -> str:
    """
    Builds a context string from passages, prefixing each with its source. 
    Trims the context to a token limit if necessary."""
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
        formatted_source_prefix = f"Fonte: {source_doc}, Seção: {source_sec}\n"
        full_passage_text_with_source = formatted_source_prefix + text
        passage_tokens = len(tokenizer.encode(full_passage_text_with_source))
        if total_tokens + passage_tokens <= limit:
            selected_context_parts.append(full_passage_text_with_source)
            total_tokens += passage_tokens
        else:
            if not selected_context_parts:
                token_ids = tokenizer.encode(full_passage_text_with_source)
                truncated_token_ids = token_ids[:limit]
                truncated_text = tokenizer.decode(truncated_token_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
                selected_context_parts.append(truncated_text)
                total_tokens = len(tokenizer.encode(truncated_text))
                logger.info(f"Context will consist of one truncated passage with {total_tokens} tokens.")
            else:
                logger.info(f"Context limit reached. Not including further passage from {source_doc}, {source_sec} ({passage_tokens} tokens). Current total: {total_tokens}.")
            break
    final_context_str = "\n\n---\n\n".join(selected_context_parts)
    logger.info(f"Final trimmed context to {total_tokens} tokens. Number of selected passages/parts: {len(selected_context_parts)}.")
    if not final_context_str.strip() and passages:
        logger.warning("Context string is empty after trimming, but passages were provided. This might be due to a very small token limit or issues with the first passage.")
        return "Contexto fornecido era muito grande para o limite de tokens e não pôde ser incluído."
    return final_context_str if final_context_str.strip() else "Nenhum contexto específico pôde ser preparado dentro do limite de tokens." 