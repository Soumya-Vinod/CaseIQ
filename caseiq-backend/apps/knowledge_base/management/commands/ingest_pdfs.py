import re
import pdfplumber
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.legal_query.models import BNSSSection
from apps.knowledge_base.models import LegalCategory, LegalProvision
import os

BASE_DIR = settings.BASE_DIR

PDF_CONFIG = {
    'BNS': {
        'path': BASE_DIR / 'documents' / 'BNS_2023.pdf',
        'act': 'BNS',
        'full_name': 'Bharatiya Nyaya Sanhita, 2023',
        'category': 'Criminal Law',
    },
    'BNSS': {
        'path': BASE_DIR / 'documents' / 'BNSS_2023.pdf',
        'act': 'BNSS',
        'full_name': 'Bharatiya Nagarik Suraksha Sanhita, 2023',
        'category': 'Criminal Procedure',
    },
    'BSA': {
        'path': BASE_DIR / 'documents' / 'BSA_2023.pdf',
        'act': 'BSA',
        'full_name': 'Bharatiya Sakshya Adhiniyam, 2023',
        'category': 'Evidence Law',
    },
    'IPC': {
        'path': BASE_DIR / 'documents' / 'IPC_1860.pdf',
        'act': 'IPC',
        'full_name': 'Indian Penal Code, 1860',
        'category': 'Criminal Law (Legacy)',
    },
    'CrPC': {
        'path': BASE_DIR / 'documents' / 'CrPC_1973.pdf',
        'act': 'CrPC',
        'full_name': 'Code of Criminal Procedure, 1973',
        'category': 'Criminal Procedure (Legacy)',
    },
}


class Command(BaseCommand):
    help = 'Ingest legal PDFs into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--act',
            type=str,
            help='Specific act to ingest (BNS, BNSS, BSA, IPC, CrPC). Ingests all if not specified.',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing records before ingesting',
        )

    def handle(self, *args, **options):
        act_filter = options.get('act')
        clear = options.get('clear')

        acts_to_process = [act_filter] if act_filter else list(PDF_CONFIG.keys())

        for act in acts_to_process:
            if act not in PDF_CONFIG:
                self.stdout.write(self.style.ERROR(f'Unknown act: {act}'))
                continue
            self.ingest_act(act, PDF_CONFIG[act], clear)

    def ingest_act(self, act_code, config, clear):
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(f'Processing: {config["full_name"]}')
        self.stdout.write(f'{"="*60}')

        pdf_path = config['path']
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f'PDF not found: {pdf_path}'))
            self.stdout.write(self.style.WARNING(f'Please place the PDF at: {pdf_path}'))
            return

        # Get or create category
        category, _ = LegalCategory.objects.get_or_create(
            name=config['category'],
            defaults={
                'slug': config['category'].lower().replace(' ', '-').replace('(', '').replace(')', ''),
                'description': f'Laws under {config["full_name"]}',
            }
        )

        if clear:
            count = BNSSSection.objects.filter(act=act_code).count()
            BNSSSection.objects.filter(act=act_code).delete()
            LegalProvision.objects.filter(act_name=act_code).delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing records for {act_code}'))

        # Extract text from PDF
        self.stdout.write(f'Extracting text from PDF...')
        full_text = self.extract_pdf_text(pdf_path)

        if not full_text:
            self.stdout.write(self.style.ERROR('Could not extract text from PDF'))
            return

        self.stdout.write(f'Extracted {len(full_text)} characters')

        # Parse sections
        sections = self.parse_sections(full_text, act_code)
        self.stdout.write(f'Found {len(sections)} sections')

        if not sections:
            self.stdout.write(self.style.WARNING('No sections parsed. Trying fallback method...'))
            sections = self.parse_sections_fallback(full_text, act_code)
            self.stdout.write(f'Fallback found {len(sections)} sections')

        # Save to database
        saved = 0
        skipped = 0
        for section_data in sections:
            try:
                obj, created = BNSSSection.objects.get_or_create(
                    act=act_code,
                    section_number=section_data['section_number'],
                    defaults={
                        'section_title': section_data['title'][:500],
                        'section_text': section_data['text'],
                        'simplified_text': '',
                        'keywords': section_data.get('keywords', []),
                        'category': section_data.get('category', ''),
                        'is_active': True,
                    }
                )
                if created:
                    saved += 1
                    # Also save to LegalProvision
                    LegalProvision.objects.get_or_create(
                        act_name=act_code,
                        section_reference=section_data['section_number'],
                        defaults={
                            'category': category,
                            'title': section_data['title'][:500],
                            'full_text': section_data['text'],
                            'simplified_text': section_data['text'][:500],
                            'plain_language_summary': '',
                            'keywords': section_data.get('keywords', []),
                            'is_verified': True,
                            'is_active': True,
                        }
                    )
                else:
                    skipped += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error saving section {section_data.get("section_number")}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'✓ {act_code}: Saved {saved} new sections, skipped {skipped} existing'
        ))

    def extract_pdf_text(self, pdf_path):
        text = ''
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                self.stdout.write(f'Total pages: {total_pages}')
                for i, page in enumerate(pdf.pages):
                    if i % 50 == 0:
                        self.stdout.write(f'  Processing page {i+1}/{total_pages}...')
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'PDF extraction error: {e}'))
        return text

    def parse_sections(self, text, act_code):
        sections = []
        # Pattern for numbered sections like "1.", "2.", "100." etc with optional title
        # Handles formats: "1. Short title." or "1. (1) When..."
        pattern = r'(?:^|\n)\s*(\d{1,3}[A-Z]?)\.\s+(?:\(1\)\s+)?([^\n]{5,200})'
        matches = list(re.finditer(pattern, text, re.MULTILINE))

        for i, match in enumerate(matches):
            section_num = match.group(1).strip()
            title_line = match.group(2).strip()

            # Get section text (from this match to next match)
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()

            # Clean up text
            section_text = re.sub(r'\s+', ' ', section_text)
            title_line = re.sub(r'\s+', ' ', title_line)

            # Extract keywords from title
            keywords = self.extract_keywords(title_line + ' ' + section_text[:200])

            if len(section_text) > 20:
                sections.append({
                    'section_number': section_num,
                    'title': title_line[:500],
                    'text': section_text[:5000],
                    'keywords': keywords[:10],
                    'category': self.categorize_section(title_line, act_code),
                })

        return sections

    def parse_sections_fallback(self, text, act_code):
        sections = []
        # Simpler fallback: split by "Section X" or just numbered paragraphs
        lines = text.split('\n')
        current_section = None
        current_text = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts a new section
            sec_match = re.match(r'^(\d{1,3}[A-Z]?)\.\s+(.+)', line)
            if sec_match:
                # Save previous section
                if current_section and current_text:
                    full_text = ' '.join(current_text)
                    sections.append({
                        'section_number': current_section['num'],
                        'title': current_section['title'][:500],
                        'text': full_text[:5000],
                        'keywords': self.extract_keywords(full_text[:300]),
                        'category': self.categorize_section(current_section['title'], act_code),
                    })
                current_section = {
                    'num': sec_match.group(1),
                    'title': sec_match.group(2)[:500],
                }
                current_text = [line]
            elif current_section:
                current_text.append(line)

        # Save last section
        if current_section and current_text:
            full_text = ' '.join(current_text)
            sections.append({
                'section_number': current_section['num'],
                'title': current_section['title'][:500],
                'text': full_text[:5000],
                'keywords': self.extract_keywords(full_text[:300]),
                'category': self.categorize_section(current_section['title'], act_code),
            })

        return sections

    def extract_keywords(self, text):
        legal_terms = [
            'murder', 'theft', 'assault', 'rape', 'kidnapping', 'fraud',
            'cheating', 'forgery', 'robbery', 'dacoity', 'abetment',
            'conspiracy', 'bail', 'arrest', 'warrant', 'fir', 'complaint',
            'evidence', 'witness', 'confession', 'punishment', 'imprisonment',
            'fine', 'death', 'life', 'property', 'document', 'court',
            'magistrate', 'police', 'investigation', 'trial', 'appeal',
            'hurt', 'grievous', 'wrongful', 'criminal', 'offence', 'penalty',
            'dowry', 'cruelty', 'defamation', 'obscene', 'nuisance',
        ]
        text_lower = text.lower()
        found = [term for term in legal_terms if term in text_lower]
        return list(set(found))

    def categorize_section(self, title, act_code):
        title_lower = title.lower()
        if any(w in title_lower for w in ['murder', 'hurt', 'assault', 'rape', 'kidnap']):
            return 'Offences Against Person'
        if any(w in title_lower for w in ['theft', 'robbery', 'dacoity', 'property', 'fraud', 'cheat']):
            return 'Offences Against Property'
        if any(w in title_lower for w in ['bail', 'arrest', 'warrant', 'remand', 'custody']):
            return 'Arrest and Bail'
        if any(w in title_lower for w in ['evidence', 'witness', 'proof', 'confession']):
            return 'Evidence and Proof'
        if any(w in title_lower for w in ['fir', 'complaint', 'investigation', 'inquiry']):
            return 'Investigation and Complaints'
        if any(w in title_lower for w in ['trial', 'court', 'magistrate', 'session']):
            return 'Trial Procedure'
        if any(w in title_lower for w in ['punishment', 'sentence', 'fine', 'imprisonment']):
            return 'Punishment'
        return 'General'