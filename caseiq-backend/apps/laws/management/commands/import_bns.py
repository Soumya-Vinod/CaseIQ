import json
from django.core.management.base import BaseCommand
from apps.laws.models import Act, LawSection
from services.llm.factory import get_llm_provider
import os


class Command(BaseCommand):
    help = 'Import BNS sections from JSON file'
    
    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to BNS sections JSON file')
    
    def handle(self, *args, **options):
        json_file = options['json_file']
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
            return
        
        # Create or get BNS Act
        act, created = Act.objects.get_or_create(
            abbreviation="BNS",
            defaults={
                'name': 'Bharatiya Nyaya Sanhita',
                'year': 2023,
                'description': 'Indian criminal code that replaced the IPC on July 1, 2024',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created Act: {act.name}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Using existing Act: {act.name}'))
        
        # Load JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            sections_data = json.load(f)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {len(sections_data)} sections from JSON'))
        
        # Import sections
        created_count = 0
        updated_count = 0
        
        for section_dict in sections_data:
            section, created = LawSection.objects.update_or_create(
                act=act,
                section_number=section_dict['section_number'],
                defaults={
                    'title': section_dict['title'],
                    'description': section_dict.get('description', ''),
                    'punishment': section_dict.get('punishment', ''),
                    'cognizable': section_dict.get('cognizable', False),
                    'bailable': section_dict.get('bailable', True),
                    'compoundable': section_dict.get('compoundable', False),
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            if (created_count + updated_count) % 50 == 0:
                self.stdout.write(f'  Processed {created_count + updated_count} sections...')
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Import complete: {created_count} created, {updated_count} updated'
        ))
        self.stdout.write(self.style.WARNING(
            '\n⚠ Embeddings not generated yet. Run: python manage.py generate_embeddings'
        ))