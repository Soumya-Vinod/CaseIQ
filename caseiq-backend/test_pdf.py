from services.pdf_ingestion.extractor import PDFExtractor

# Replace with your actual PDF path
pdf_path = r"D:\path\to\your\BNS.pdf"

extractor = PDFExtractor()
sections = extractor.extract(pdf_path)

print(f"✓ Extracted {len(sections)} sections")
print("\nFirst 3 sections:")
for i, section in enumerate(sections[:3], 1):
    print(f"\n{i}. Section {section['section_number']}")
    print(f"   Title: {section['title']}")
    print(f"   Description: {section['description'][:200]}...")