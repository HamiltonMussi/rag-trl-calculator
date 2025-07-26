"""File handling utilities for the RAG-TRL backend."""

import pathlib
import logging
from typing import Optional, Tuple
import PyPDF2

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles file reading and text extraction."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md'}
    
    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        """Check if file extension is supported."""
        extension = pathlib.Path(file_path).suffix.lower()
        return extension in cls.SUPPORTED_EXTENSIONS
    
    @classmethod
    def extract_text(cls, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Extract text content from supported file types.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (success, text_content, error_message)
        """
        try:
            file_path_obj = pathlib.Path(file_path)
            extension = file_path_obj.suffix.lower()
            
            if not cls.is_supported_file(file_path):
                return False, "", f"Unsupported file type: {extension}"
            
            if extension == '.pdf':
                return cls._extract_pdf_text(file_path)
            elif extension in ['.txt', '.md']:
                return cls._extract_text_file(file_path)
            
        except Exception as e:
            logger.error(f"Unexpected error extracting text from {file_path}: {e}", exc_info=True)
            return False, "", str(e)
        
        return False, "", "Unknown file processing error"
    
    @classmethod
    def _extract_pdf_text(cls, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """Extract text from PDF file."""
        try:
            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                extracted_pages = []
                
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    extracted_pages.append(page.extract_text() or "")
                
                text_content = "\n".join(extracted_pages)
                
                if not text_content.strip():
                    return False, "", "No text content found in PDF"
                
                logger.info(f"Successfully extracted {len(text_content)} characters from PDF: {file_path}")
                return True, text_content, None
                
        except Exception as e:
            logger.error(f"Error extracting PDF text from {file_path}: {e}", exc_info=True)
            return False, "", str(e)
    
    @classmethod
    def _extract_text_file(cls, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """Extract text from plain text files."""
        try:
            # Try UTF-8 first
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                    return True, text_content, None
            except UnicodeDecodeError:
                # Fallback to latin-1
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        text_content = f.read() 
                        logger.warning(f"UTF-8 decode failed for {file_path}; used latin-1")
                        return True, text_content, None
                except UnicodeDecodeError:
                    # Last resort: binary with replacement
                    with open(file_path, "rb") as f:
                        raw = f.read()
                    text_content = raw.decode("utf-8", errors="replace")
                    logger.warning(f"Both UTF-8 and latin-1 failed for {file_path}; used replacement chars")
                    return True, text_content, None
                    
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}", exc_info=True)
            return False, "", str(e)


def create_safe_filename(filename: str) -> str:
    """Create a safe filename for use in IDs by replacing problematic characters."""
    return filename.replace('.', '_').replace('-', '_')


def generate_unique_chunk_ids(tech_id: str, filename: str, chunk_count: int) -> list[str]:
    """Generate unique IDs for document chunks."""
    safe_filename = create_safe_filename(filename)
    return [f"{tech_id}_{safe_filename}_{i}" for i in range(chunk_count)]