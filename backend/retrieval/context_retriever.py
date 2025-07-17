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