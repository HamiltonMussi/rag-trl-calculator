import re
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.hf_models import get_just_tokenizer

logger = logging.getLogger(__name__)

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
        'abstract': [], 'introduction': [], 'methodology': [], 
        'results': [], 'discussion': [], 'conclusion': [], 
        'references': [], 'appendices': [], 'other': []
    }
    section_headers = {
        'abstract':   r'(?i)^\s*(?:\d+\.?\s*)?(?:abstract|resumo|sumário executivo)\b',
        'introduction': r'(?i)^\s*(?:\d+\.?\s*)?(?:introduction|introdução)\b',
        'methodology':r'(?i)^\s*(?:\d+\.?\s*)?(?:methodology|methods|materials and methods|metodologia|materiais e métodos)\b',
        'results':    r'(?i)^\s*(?:\d+\.?\s*)?(?:results|resultados)\b',
        'discussion': r'(?i)^\s*(?:\d+\.?\s*)?(?:discussion|discussão)\b',
        'conclusion': r'(?i)^\s*(?:\d+\.?\s*)?(?:conclusion|conclusions|conclusão|conclusões)\b',
        'references': r'(?i)^\s*(?:\d+\.?\s*)?(?:references|referências|bibliografia)\b',
        'appendices': r'(?i)^\s*(?:\d+\.?\s*)?(?:appendix|appendices|anexo|anexos)\b'
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
    processed_text_overall = ""
    defined_section_keys = ['abstract', 'introduction', 'methodology', 'results', 'discussion', 'conclusion', 'references', 'appendices']
    for section_name in defined_section_keys:
        section_text_list = sections_map.get(section_name, [])
        full_section_text = "\n\n".join(section_text_list).strip()
        if not full_section_text:
            continue
        processed_text_overall += full_section_text + "\n\n"
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
    other_section_text_list = sections_map.get('other', [])
    full_other_text = "\n\n".join(other_section_text_list).strip()
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
    return final_chunks 