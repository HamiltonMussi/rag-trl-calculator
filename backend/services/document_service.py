"""Document processing service for text chunking and analysis."""

import logging
import re
from typing import List, Dict, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.hf_models import get_just_tokenizer

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Handles document chunking with semantic section awareness."""
    
    def __init__(self, chunk_size_tokens: int = 450, chunk_overlap_tokens: int = 50):
        """
        Initialize the document chunker.
        
        Args:
            chunk_size_tokens: Target size of each chunk in tokens
            chunk_overlap_tokens: Number of tokens to overlap between chunks
        """
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.tokenizer = get_just_tokenizer()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size_tokens,
            chunk_overlap=chunk_overlap_tokens,
            length_function=lambda x: len(self.tokenizer.encode(x)),
            is_separator_regex=False,
        )
        
        # Section headers for academic documents
        self.section_headers = {
            'abstract': r'(?i)^\s*(?:\d+\.?\s*)?(?:abstract|resumo|sumário executivo)\b',
            'introduction': r'(?i)^\s*(?:\d+\.?\s*)?(?:introduction|introdução)\b',
            'methodology': r'(?i)^\s*(?:\d+\.?\s*)?(?:methodology|methods|materials and methods|metodologia|materiais e métodos|desenvolvimento)\b',
            'results': r'(?i)^\s*(?:\d+\.?\s*)?(?:results|resultados)\b',
            'discussion': r'(?i)^\s*(?:\d+\.?\s*)?(?:discussion|discussão)\b',
            'conclusion': r'(?i)^\s*(?:\d+\.?\s*)?(?:conclusion|conclusions|conclusão|conclusões)\b',
            'references': r'(?i)^\s*(?:\d+\.?\s*)?(?:references|referências|bibliografia)\b',
            'appendices': r'(?i)^\s*(?:\d+\.?\s*)?(?:appendix|appendices|anexo|anexos)\b'
        }
    
    def create_semantic_chunks(self, text: str) -> List[Dict]:
        """
        Create semantic chunks from text with section awareness.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of chunk dictionaries with text, section, and metadata
        """
        logger.info(f"Creating semantic chunks. Text length: {len(text)} chars. "
                   f"Target chunk size: {self.chunk_size_tokens} tokens")
        
        # Parse text into sections
        sections_map = self._parse_document_sections(text)
        
        # Process each section
        final_chunks = []
        section_order = ['abstract', 'introduction', 'methodology', 'results', 
                        'discussion', 'conclusion', 'references', 'appendices']
        
        # Process defined sections first
        for section_name in section_order:
            chunks = self._process_section(section_name, sections_map.get(section_name, []))
            final_chunks.extend(chunks)
        
        # Process 'other' section
        other_chunks = self._process_section('other', sections_map.get('other', []))
        final_chunks.extend(other_chunks)
        
        # Log section distribution
        self._log_section_distribution(final_chunks)
        
        return final_chunks
    
    def _parse_document_sections(self, text: str) -> Dict[str, List[str]]:
        """Parse document into sections based on headers."""
        sections_map = {
            'abstract': [], 'introduction': [], 'methodology': [], 
            'results': [], 'discussion': [], 'conclusion': [], 
            'references': [], 'appendices': [], 'other': []
        }
        
        current_section_key = 'other'
        current_section_buffer = []
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        
        # Use alternative splitting if we have very few paragraphs
        if len(paragraphs) < 20:
            alt_paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            if len(alt_paragraphs) > len(paragraphs) * 3:
                paragraphs = alt_paragraphs
                logger.info(f"Using alternative paragraph split with {len(paragraphs)} parts")
        
        logger.info(f"Split into {len(paragraphs)} paragraphs for section detection")
        
        # Process each paragraph
        for para_idx, para in enumerate(paragraphs):
            para_strip = para.strip()
            if not para_strip:
                current_section_buffer.append(para)
                continue
            
            # Check for section headers
            section_found = self._check_section_headers(para_strip, para_idx)
            
            if section_found:
                # Save current section buffer
                if current_section_buffer:
                    sections_map[current_section_key].append("\n\n".join(current_section_buffer))
                    current_section_buffer = []
                
                current_section_key = section_found['section']
                
                # Add remaining content after header
                if section_found['remaining_content']:
                    current_section_buffer.append(section_found['remaining_content'])
                    
                logger.info(f"Switched to section: '{current_section_key}'")
            else:
                current_section_buffer.append(para)
        
        # Add final buffer
        if current_section_buffer:
            sections_map[current_section_key].append("\n\n".join(current_section_buffer))
        
        return sections_map
    
    def _check_section_headers(self, para_strip: str, para_idx: int) -> Dict:
        """Check if paragraph contains section headers."""
        lines = para_strip.split('\n')
        
        for line_idx, line in enumerate(lines):
            line_strip = line.strip()
            
            for section_key, pattern in self.section_headers.items():
                if re.match(pattern, line_strip):
                    logger.info(f"Matched section '{section_key}' in line: '{line_strip}' (paragraph {para_idx})")
                    
                    # Get remaining content after header
                    remaining_lines = lines[line_idx + 1:]
                    remaining_content = '\n'.join(remaining_lines).strip() if remaining_lines else None
                    
                    return {
                        'section': section_key,
                        'remaining_content': remaining_content
                    }
        
        return None
    
    def _process_section(self, section_name: str, section_texts: List[str]) -> List[Dict]:
        """Process a single section into chunks."""
        if not section_texts:
            return []
        
        full_section_text = "\n\n".join(section_texts).strip()
        if not full_section_text:
            return []
        
        logger.info(f"Processing section '{section_name}' (length: {len(full_section_text)} chars)")
        
        # Split section into chunks
        chunk_texts = self.text_splitter.split_text(full_section_text)
        chunks = []
        
        for i, chunk_text in enumerate(chunk_texts):
            token_count = len(self.tokenizer.encode(chunk_text))
            chunks.append({
                'text': chunk_text,
                'section': section_name,
                'metadata': {
                    'section': section_name,
                    'chunk_in_section': i + 1,
                    'char_length': len(chunk_text),
                    'token_count': token_count
                }
            })
        
        logger.info(f"Section '{section_name}' yielded {len(chunks)} chunks")
        return chunks
    
    def _log_section_distribution(self, chunks: List[Dict]) -> None:
        """Log the distribution of chunks across sections."""
        section_counts = {}
        for chunk in chunks:
            section = chunk.get('section', 'unknown')
            section_counts[section] = section_counts.get(section, 0) + 1
        
        logger.info(f"Final section distribution: {section_counts}")


class DocumentProcessor:
    """Main document processing service."""
    
    def __init__(self):
        """Initialize the document processor."""
        self.chunker = DocumentChunker()
    
    def process_document(self, text: str, filename: str) -> Tuple[bool, List[Dict], str]:
        """
        Process a document into chunks with metadata.
        
        Args:
            text: Document text content
            filename: Name of the source file
            
        Returns:
            Tuple of (success, chunks_list, error_message)
        """
        try:
            if not text.strip():
                return False, [], "No text content to process"
            
            # Create semantic chunks
            chunks = self.chunker.create_semantic_chunks(text)
            
            if not chunks:
                return False, [], "No chunks created from document"
            
            # Add source filename to metadata
            for chunk in chunks:
                chunk['metadata']['source'] = filename
            
            logger.info(f"Successfully processed document '{filename}' into {len(chunks)} chunks")
            return True, chunks, ""
            
        except Exception as e:
            logger.error(f"Error processing document '{filename}': {e}", exc_info=True)
            return False, [], str(e)