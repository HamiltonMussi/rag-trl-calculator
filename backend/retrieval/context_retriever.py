"""Context retrieval service with improved architecture."""

from typing import List, Dict
import logging

from processing.indexer import is_processing
from services.chromadb_service import ChromaDBService
from utils.hf_models import get_hf_embeddings, get_just_tokenizer
from config import LOCAL_LLM_MODEL_ID

logger = logging.getLogger(__name__)

# Initialize service
chromadb_service = ChromaDBService()

def get_cached_search(question: str, tech_id: str, k: int) -> List[Dict]:
    """Search for relevant context from technology and TRL collections."""
    logger.info(f"Searching for question: '{question[:100]}...', tech_id: '{tech_id}', k: {k}")
    
    if is_processing(tech_id):
        logger.warning(f"Technology '{tech_id}' is still processing")
        raise ValueError("Document is still being processed. Please wait.")
    
    # Generate query embedding
    query_embedding = get_hf_embeddings([question])[0]
    all_candidates = []
    
    # Search technology-specific collection
    tech_results = chromadb_service.query_collection(
        f"tech_{tech_id}", query_embedding, n_results=k * 2
    )
    tech_candidates = _process_collection_results_with_scores(tech_results, tech_id=tech_id)
    all_candidates.extend(tech_candidates)
    
    # Search TRL glossary collection
    trl_results = chromadb_service.query_collection(
        "trl", query_embedding, n_results=k * 2
    )
    trl_candidates = _process_collection_results_with_scores(trl_results, tech_id=None)
    all_candidates.extend(trl_candidates)
    
    # Sort by similarity and take top k results
    all_candidates.sort(key=lambda x: x['distance'])
    results = all_candidates[:k]
    
    # Log results summary
    _log_search_results(results)
    
    return results

def _process_collection_results_with_scores(res: Dict, tech_id: str = None) -> List[Dict]:
    """Process ChromaDB query results with similarity scores."""
    results = []
    
    if not res or not res.get("documents") or not res["documents"][0]:
        return results
    
    docs = res["documents"][0]
    metas = res.get("metadatas", [[]])[0] or [{}] * len(docs)
    distances = res.get("distances", [[]])[0] or [float('inf')] * len(docs)
    
    # Ensure all arrays have the same length
    min_length = min(len(docs), len(metas), len(distances))
    
    for i in range(min_length):
        doc_text = docs[i]
        meta_info = metas[i] if i < len(metas) else {}
        distance = distances[i] if i < len(distances) else float('inf')
        
        # Determine source document name
        if tech_id:
            source_doc_name = meta_info.get('source', f'Tech {tech_id} Document')
        else:
            source_doc_name = "Glossário TRL"
        
        # Determine section name
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


def trim_for_ctx(passages: List[Dict], limit: int = 3500) -> str:
    """Build context string from passages, trimming to token limit."""
    if not passages:
        logger.warning("No passages provided for context")
        return "Nenhum contexto específico encontrado."
    
    tokenizer = get_just_tokenizer(LOCAL_LLM_MODEL_ID)
    context_builder = ContextBuilder(tokenizer, limit)
    
    return context_builder.build_context(passages)


class ContextBuilder:
    """Builds context strings from passages with token limit awareness."""
    
    def __init__(self, tokenizer, token_limit: int):
        """Initialize context builder."""
        self.tokenizer = tokenizer
        self.token_limit = token_limit
    
    def build_context(self, passages: List[Dict]) -> str:
        """Build trimmed context string from passages."""
        selected_parts = []
        total_tokens = 0
        
        for passage in passages:
            text = passage.get("text", "")
            source_doc = passage.get("source_document", "Fonte Desconhecida")
            source_sec = passage.get("source_section", "Seção Desconhecida")
            
            # Format passage with source information
            formatted_passage = f"Fonte: {source_doc}, Seção: {source_sec}\n{text}"
            passage_tokens = len(self.tokenizer.encode(formatted_passage))
            
            if total_tokens + passage_tokens <= self.token_limit:
                selected_parts.append(formatted_passage)
                total_tokens += passage_tokens
            else:
                # If no parts selected yet, truncate this passage
                if not selected_parts:
                    truncated = self._truncate_passage(formatted_passage)
                    selected_parts.append(truncated)
                    total_tokens = len(self.tokenizer.encode(truncated))
                    logger.info(f"Context consists of one truncated passage with {total_tokens} tokens")
                else:
                    logger.info(f"Token limit reached. Excluded passage from {source_doc}, {source_sec}")
                break
        
        final_context = "\n\n---\n\n".join(selected_parts)
        logger.info(f"Built context with {total_tokens} tokens from {len(selected_parts)} passages")
        
        if not final_context.strip():
            return self._get_fallback_message(passages)
        
        return final_context
    
    def _truncate_passage(self, passage: str) -> str:
        """Truncate a passage to fit within token limit."""
        token_ids = self.tokenizer.encode(passage)
        truncated_ids = token_ids[:self.token_limit]
        return self.tokenizer.decode(truncated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)
    
    def _get_fallback_message(self, passages: List[Dict]) -> str:
        """Get fallback message when context cannot be built."""
        if passages:
            return "Contexto fornecido era muito grande para o limite de tokens e não pôde ser incluído."
        return "Nenhum contexto específico pôde ser preparado dentro do limite de tokens."


def _log_search_results(results: List[Dict]) -> None:
    """Log search results summary."""
    tech_count = sum(1 for r in results if r['source_document'] != 'Glossário TRL')
    trl_count = len(results) - tech_count
    
    logger.info(f"Selected {len(results)} results: {tech_count} from tech, {trl_count} from TRL")
    
    if results:
        best = results[0]
        logger.info(f"Best result: text='{best['text'][:50]}...', "
                   f"source='{best['source_document']}', distance={best['distance']:.4f}") 