from django.core.management.base import BaseCommand
from apps.laws.models import LawSection
from services.llm.factory import get_llm_provider
from sentence_transformers import SentenceTransformer
import time


class Command(BaseCommand):
    help = 'Generate embeddings for all law sections without embeddings'
    
    def handle(self, *args, **options):
        # Get sections without embeddings
        sections = LawSection.objects.filter(
            embedding__isnull=True,
            is_active=True
        ).select_related('act')
        
        total = sections.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ All sections already have embeddings!'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Generating embeddings for {total} sections...'))
        
        # Load sentence transformer model
        self.stdout.write('Loading embedding model...')
        model = SentenceTransformer("all-MiniLM-L6-v2")
        
        generated_count = 0
        error_count = 0
        start_time = time.time()
        
        for i, section in enumerate(sections, 1):
            try:
                # Create text to embed
                text = f"{section.title}. {section.description}"
                
                # Generate embedding
                embedding = model.encode(text)
                
                # Save to database
                section.embedding = embedding.tolist()
                section.save(update_fields=['embedding'])
                
                generated_count += 1
                
                # Progress every 50 sections
                if i % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = i / elapsed
                    remaining = (total - i) / rate
                    self.stdout.write(
                        f'  Progress: {i}/{total} ({i*100//total}%) - '
                        f'ETA: {int(remaining)}s'
                    )
            
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Error on section {section.section_number}: {e}'
                    )
                )
        
        # Summary
        elapsed = time.time() - start_time
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('✓ Embedding Generation Complete'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS(f'  Generated:  {generated_count} embeddings'))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'  Errors:     {error_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Time:       {int(elapsed)}s'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ CaseIQ is ready to answer legal queries!'))