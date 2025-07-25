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
    logger.info(f"First 500 chars of text: {repr(text[:500])}")

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
        'methodology':r'(?i)^\s*(?:\d+\.?\s*)?(?:methodology|methods|materials and methods|metodologia|materiais e métodos|desenvolvimento)\b',
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
    logger.info(f"First 3 paragraphs: {[p[:100] + '...' if len(p) > 100 else p for p in paragraphs[:3]]}")
    logger.info(f"Paragraph lengths: {[len(p) for p in paragraphs[:10]]}")
    
    # Also try splitting by single newlines if we have very few paragraphs
    if len(paragraphs) < 20:
        alt_paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        logger.info(f"Alternative split by single newlines: {len(alt_paragraphs)} parts")
        logger.info(f"First 5 alt parts: {[p[:50] + '...' if len(p) > 50 else p for p in alt_paragraphs[:5]]}")
        
        # Use alternative split if it gives us more reasonable sections
        if len(alt_paragraphs) > len(paragraphs) * 3:
            paragraphs = alt_paragraphs
            logger.info(f"Using alternative paragraph split with {len(paragraphs)} parts")
    
    # Track paragraph index to restrict abstract detection to early paragraphs
    for para_idx, para in enumerate(paragraphs):
        para_strip = para.strip()
        if not para_strip:
            current_section_texts_buffer.append(para)
            continue
        matched_section = False
        logger.debug(f"Checking paragraph: '{para_strip[:100]}...'")
        
        # Check each line in the paragraph for section headers
        lines = para_strip.split('\n')
        for line_idx, line in enumerate(lines):
            line_strip = line.strip()
            for section_key, pattern in section_headers.items():
                if re.match(pattern, line_strip):
                    logger.info(f"MATCHED section '{section_key}' with pattern '{pattern}' in line: '{line_strip}' (paragraph {para_idx})")
                    if current_section_texts_buffer:
                        sections_map[current_section_key].append("\n\n".join(current_section_texts_buffer))
                        current_section_texts_buffer = []
                    current_section_key = section_key
                    
                    # Add remaining lines after the header to buffer
                    remaining_lines = lines[line_idx + 1:]
                    if remaining_lines:
                        remaining_content = '\n'.join(remaining_lines).strip()
                        if remaining_content:
                            current_section_texts_buffer.append(remaining_content)
                    
                    matched_section = True
                    logger.info(f"Current section is now: '{current_section_key}'")
                    break
            if matched_section:
                break
                
        if not matched_section:
            logger.debug(f"No section match found for paragraph: '{para_strip[:50]}...'")
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
    
    # Log final section distribution
    section_counts = {}
    for chunk in final_chunks:
        section = chunk.get('section', 'unknown')
        section_counts[section] = section_counts.get(section, 0) + 1
    logger.info(f"Final section distribution: {section_counts}")
    
    return final_chunks 