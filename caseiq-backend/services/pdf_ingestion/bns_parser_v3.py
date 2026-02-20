"""
Production-Ready BNS PDF Parser
Extracts law sections from Bharatiya Nyaya Sanhita (BNS) 2023
"""
import pdfplumber
import re
from typing import List, Dict


def parse_bns_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract all sections from BNS PDF with proper content.
    
    Returns:
        List of dicts with section data
    """
    sections = []
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        
        # Extract all text
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Split by section numbers
        # Pattern: newline followed by number, period, space
        parts = re.split(r'\n(\d+)\.\s+', full_text)
        
        # parts[0] is preamble, then alternating section_num, content
        i = 1
        while i < len(parts) - 1:
            section_num = parts[i].strip()
            content = parts[i+1].strip()
            
            # Skip if section number too large (likely page number)
            if int(section_num) > 400:
                i += 2
                continue
            
            # Extract title - often ends with a period on same line
            # e.g., "A man is said to commit "rape" if he— Rape."
            #  or   "Theft in a dwelling house..."
            
            first_line = content.split('\n')[0]
            
            # Title is either:
            # 1. Everything before first period
            # 2. Or just the first line if short
            title_match = re.match(r'^([^\.]+)', first_line)
            if title_match:
                title = title_match.group(1).strip()
                # Remove the title from content
                remaining = content[len(title_match.group(1)):].lstrip('. ')
            else:
                title = first_line
                remaining = content[len(first_line):].strip()
            
            # Clean title
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Clean description
            description = re.sub(r'\s+', ' ', remaining).strip()
            description = description[:3000]  # Limit
            
            # Extract attributes
            punishment = extract_punishment(description)
            cognizable = is_cognizable(description)
            bailable = is_bailable(description)
            compoundable = is_compoundable(description)
            
            sections.append({
                'section_number': section_num,
                'title': title[:300],
                'description': description,
                'punishment': punishment,
                'cognizable': cognizable,
                'bailable': bailable,
                'compoundable': compoundable
            })
            
            i += 2
        
        return sections


def extract_punishment(text: str) -> str:
    """Extract punishment information"""
    patterns = [
        r'shall be punished with [^\.]{20,500}\.',
        r'punishable with [^\.]{20,500}\.',
        r'imprisonment [^\.]{20,300}\.',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()[:500]
    
    return ""


def is_cognizable(text: str) -> bool:
    return bool(re.search(r'\bcognizable\b', text, re.I))


def is_bailable(text: str) -> bool:
    if re.search(r'\b(non-bailable|not bailable)\b', text, re.I):
        return False
    return bool(re.search(r'\bbailable\b', text, re.I))


def is_compoundable(text: str) -> bool:
    return bool(re.search(r'\bcompoundable\b', text, re.I))


if __name__ == "__main__":
    import json
    
    print("Parsing BNS 2023 PDF...")
    sections = parse_bns_pdf("/mnt/user-data/uploads/BNS_2023.pdf")
    
    print(f"✓ Extracted {len(sections)} sections\n")
    
    # Test some key sections
    test_sections = {
        '63': 'Rape',
        '99': 'Murder',
        '301': 'Theft',
        '307': 'Robbery'
    }
    
    print("="*70)
    print("Key Criminal Sections:")
    print("="*70)
    
    for num, expected_title in test_sections.items():
        for s in sections:
            if s['section_number'] == num:
                print(f"\nSection {s['section_number']}: {s['title']}")
                print(f"Description ({len(s['description'])} chars): {s['description'][:250]}...")
                if s['punishment']:
                    print(f"Punishment: {s['punishment'][:150]}...")
                print(f"Cognizable: {s['cognizable']} | Bailable: {s['bailable']}")
                break
    
    # Save
    output = "/tmp/bns_sections_final.json"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(sections)} sections to {output}")
    print("✓ Ready to import into CaseIQ!")