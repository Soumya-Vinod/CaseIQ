import logging
from typing import List, Dict
from apps.laws.models import Act, LawSection
from services.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


class LawLoader:
    """
    Loads extracted law sections into the database and generates embeddings.
    """
    
    def __init__(self):
        self.llm = get_llm_provider()
    
    def load(self, sections_data: List[Dict], act: Act):
        """
        Load sections into database for a given Act.
        
        Args:
            sections_data: List of section dicts from PDFExtractor
            act: The Act these sections belong to
        """
        created_count = 0
        updated_count = 0
        
        for section_dict in sections_data:
            try:
                section_number = section_dict['section_number']
                
                # Check if section already exists
                section, created = LawSection.objects.update_or_create(
                    act=act,
                    section_number=section_number,
                    defaults={
                        'title': section_dict['title'],
                        'description': section_dict['description'],
                        'punishment': section_dict.get('punishment', ''),
                        'cognizable': section_dict.get('cognizable', False),
                        'bailable': section_dict.get('bailable', True),
                        'compoundable': section_dict.get('compoundable', False),
                        'is_active': True,
                    }
                )
                
                # Generate embedding
                text = f"{section.title}. {section.description}"
                section.embedding = self.llm.generate_embedding(text)
                section.save(update_fields=['embedding'])
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                if (created_count + updated_count) % 10 == 0:
                    logger.info(f"Loaded {created_count + updated_count} sections...")
            
            except Exception as e:
                logger.error(f"Failed to load section {section_dict.get('section_number')}: {e}")
        
        logger.info(f"Completed: {created_count} created, {updated_count} updated")