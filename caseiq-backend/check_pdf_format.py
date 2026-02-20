import pdfplumber

pdf_path = r"media\law_pdfs\source\BNS 2023.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")
    
    # Check multiple pages to find section format
    for page_num in [15, 20, 25]:
        print("=" * 60)
        print(f"Page {page_num} content:")
        print("=" * 60)
        text = pdf.pages[page_num].extract_text()
        # Just show first 800 chars
        print(text[:800])
        print("\n")