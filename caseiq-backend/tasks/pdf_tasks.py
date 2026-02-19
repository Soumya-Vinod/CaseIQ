from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def process_law_pdf(self, pdf_id: int):
    """
    Async task: Parse a government PDF and load sections into the DB.
    
    This is triggered when an admin uploads a law PDF.
    """
    from apps.laws.models import LawPDF
    from services.pdf_ingestion.extractor import PDFExtractor
    from services.pdf_ingestion.loader import LawLoader
    from django.utils import timezone
    
    try:
        pdf_record = LawPDF.objects.get(id=pdf_id)
        logger.info(f"Processing PDF {pdf_id}: {pdf_record.file.name}")
        
        # Extract sections from PDF
        extractor = PDFExtractor()
        sections_data = extractor.extract(pdf_record.file.path)
        
        logger.info(f"Extracted {len(sections_data)} sections from PDF {pdf_id}")
        
        # Load sections into database
        loader = LawLoader()
        loader.load(sections_data, act=pdf_record.act)
        
        # Mark as processed
        pdf_record.processed = True
        pdf_record.sections_extracted = len(sections_data)
        pdf_record.processed_at = timezone.now()
        pdf_record.save()
        
        logger.info(f"Successfully processed PDF {pdf_id}")
        
    except LawPDF.DoesNotExist:
        logger.error(f"PDF {pdf_id} not found")
    except Exception as exc:
        logger.exception(f"PDF {pdf_id} processing failed: {exc}")
        
        # Save error message
        pdf_record = LawPDF.objects.filter(id=pdf_id).first()
        if pdf_record:
            pdf_record.processing_error = str(exc)[:500]
            pdf_record.save()
        
        raise self.retry(exc=exc)