import json
from django.core.management.base import BaseCommand
from apps.laws.models import Act, LawSection
import os


class Command(BaseCommand):
    help = 'Import law sections from JSON files (BNS, IPC, etc.)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to law sections JSON file'
        )
        parser.add_argument(
            '--act-name',
            type=str,
            required=True,
            help='Full name of the Act (e.g., "Bharatiya Nyaya Sanhita")'
        )
        parser.add_argument(
            '--act-abbr',
            type=str,
            required=True,
            help='Abbreviation (e.g., "BNS", "IPC")'
        )
        parser.add_argument(
            '--year',
            type=int,
            required=True,
            help='Year of the Act (e.g., 2023, 1860)'
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Optional description of the Act'
        )
    
    def handle(self, *args, **options):
        json_file = options['json_file']
        
        # Validate file exists
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'❌ File not found: {json_file}'))
            return
        
        # Create or get Act
        act, created = Act.objects.get_or_create(
            abbreviation=options['act_abbr'],
            defaults={
                'name': options['act_name'],
                'year': options['year'],
                'description': options['description'],
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created Act: {act.name} ({act.year})'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Using existing Act: {act.name} ({act.year})'))
        
        # Load JSON
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                sections_data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to load JSON: {e}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {len(sections_data)} sections from JSON'))
        
        # Import sections
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for i, section_dict in enumerate(sections_data, 1):
            try:
                section, created = LawSection.objects.update_or_create(
                    act=act,
                    section_number=section_dict['section_number'],
                    defaults={
                        'title': section_dict.get('title', '')[:300],
                        'description': section_dict.get('description', '')[:3000],
                        'punishment': section_dict.get('punishment', '')[:500],
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
                
                # Progress update every 100 sections
                if i % 100 == 0:
                    self.stdout.write(f'  Progress: {i}/{len(sections_data)} sections...')
            
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Error importing section {section_dict.get("section_number", "?")}: {e}'
                    )
                )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS(f'✓ Import Complete for {act.abbreviation}'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS(f'  Created:  {created_count} sections'))
        self.stdout.write(self.style.SUCCESS(f'  Updated:  {updated_count} sections'))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'  Errors:   {error_count} sections'))
        
        # Next steps
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('⚠ Next Step: Generate embeddings'))
        self.stdout.write(self.style.WARNING('  Run: python manage.py generate_embeddings'))
