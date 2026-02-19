import pdfplumber
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extracts law sections from government PDF files.
    
    Supports PDF formats from India Code and official government sources.
    """
    
    def extract(self, pdf_path: str) -> List[Dict]:
        """
        Extract all sections from a law PDF.
        
        Returns:
            List of dicts with keys: section_number, title, description, punishment, etc.
        """
        sections = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Processing PDF: {pdf_path} ({len(pdf.pages)} pages)")
                
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                
                # Parse sections from text
                sections = self._parse_sections(full_text)
                
                logger.info(f"Extracted {len(sections)} sections from PDF")
        
        except Exception as e:
            logger.exception(f"Failed to extract PDF {pdf_path}: {e}")
            raise
        
        return sections
    
    def _parse_sections(self, text: str) -> List[Dict]:
        """
        Parse sections from extracted PDF text.
        
        This is a basic parser - you'll need to customize based on your PDF format.
        """
        sections = []
        
        # Pattern: "Section 123. Title of section"
        # Adjust this regex based on your actual PDF format
        section_pattern = r'(?:Section|Sec\.|§)\s*(\d+[A-Z]?)\.\s*([^\n]+)'
        
        matches = re.finditer(section_pattern, text, re.MULTILINE | re.IGNORECASE)
        
        for match in matches:
            section_num = match.group(1).strip()
            title = match.group(2).strip()
            
            # Extract description (text until next section or end)
            start_pos = match.end()
            next_match = re.search(section_pattern, text[start_pos:])
            
            if next_match:
                description = text[start_pos:start_pos + next_match.start()].strip()
            else:
                description = text[start_pos:start_pos + 1000].strip()  # Take next 1000 chars
            
            # Basic cleanup
            description = re.sub(r'\s+', ' ', description)
            description = description[:2000]  # Limit length
            
            # Try to extract punishment info
            punishment = self._extract_punishment(description)
            
            sections.append({
                'section_number': section_num,
                'title': title,
                'description': description,
                'punishment': punishment,
                'cognizable': self._is_cognizable(description),
                'bailable': self._is_bailable(description),
                'compoundable': self._is_compoundable(description),
            })
        
        return sections
    
    def _extract_punishment(self, text: str) -> str:
        """Extract punishment details from section text."""
        punishment_keywords = ['imprisonment', 'fine', 'death', 'life', 'years', 'months']
        
        # Look for punishment-related sentences
        sentences = text.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in punishment_keywords):
                return sentence.strip()[:500]
        
        return ""
    
    def _is_cognizable(self, text: str) -> bool:
        """Determine if offense is cognizable."""
        return bool(re.search(r'\bcognizable\b', text, re.IGNORECASE))
    
    def _is_bailable(self, text: str) -> bool:
        """Determine if offense is bailable."""
        bailable_match = re.search(r'\b(non-bailable|not bailable)\b', text, re.IGNORECASE)
        if bailable_match:
            return False
        return bool(re.search(r'\bbailable\b', text, re.IGNORECASE))
    
    def _is_compoundable(self, text: str) -> bool:
        """Determine if offense is compoundable."""
        return bool(re.search(r'\bcompoundable\b', text, re.IGNORECASE))