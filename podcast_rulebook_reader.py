"""PDF Rulebook Reader Module for Podcast Generation"""
import os
import logging

# Try to import scheduler for logger, fallback to basic logging
try:
    import scheduler
    logger = scheduler.logger
except ImportError:
    logger = logging.getLogger(__name__)

# Try to import PDF reading libraries
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available. Install pdfplumber to read rulebook PDF.")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# Cache for rulebook text
_rulebook_text_cache = None


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF rulebook.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF, or empty string if extraction fails
    """
    global _rulebook_text_cache
    
    # Return cached text if available
    if _rulebook_text_cache is not None:
        return _rulebook_text_cache
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return ""
    
    text = ""
    
    # Try pdfplumber first (better text extraction)
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Successfully extracted text from PDF using pdfplumber ({len(text)} characters)")
            _rulebook_text_cache = text
            return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}. Trying PyPDF2...")
    
    # Fallback to PyPDF2
    if PYPDF2_AVAILABLE:
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Successfully extracted text from PDF using PyPDF2 ({len(text)} characters)")
            _rulebook_text_cache = text
            return text
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""
    
    logger.error("No PDF reading library available. Install pdfplumber or PyPDF2.")
    return ""


def get_rulebook_text(rulebook_path=None):
    """
    Get rulebook text, using default path if not provided.
    
    Args:
        rulebook_path: Optional path to rulebook PDF. Defaults to "Official Cascade Rulebook.pdf"
        
    Returns:
        str: Rulebook text
    """
    if rulebook_path is None:
        # Default to rulebook in project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        rulebook_path = os.path.join(script_dir, "Official Cascade Rulebook.pdf")
    
    return extract_text_from_pdf(rulebook_path)


def clear_cache():
    """Clear the cached rulebook text (useful for testing or if rulebook is updated)."""
    global _rulebook_text_cache
    _rulebook_text_cache = None


