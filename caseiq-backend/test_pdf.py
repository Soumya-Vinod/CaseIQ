import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from services.pdf_ingestion.extractor import PDFExtractor

# Test with BNS first
pdf_path = r"media\law_pdfs\source\BNS 2023.pdf"

print(f"Testing extraction on: {pdf_path}")
print("=" * 60)

extractor = PDFExtractor()
sections = extractor.extract(pdf_path)

print(f"\n✓ Extracted {len(sections)} sections")

if sections:
    print("\n" + "=" * 60)
    print("First 3 sections:")
    print("=" * 60)
    for i, section in enumerate(sections[:3], 1):
        print(f"\n{i}. Section {section['section_number']}")
        print(f"   Title: {section['title'][:80]}...")
        print(f"   Description: {section['description'][:150]}...")
        print(f"   Cognizable: {section['cognizable']}")
        print(f"   Bailable: {section['bailable']}")
else:
    print("\n⚠ No sections extracted! The PDF format may need a custom parser.")