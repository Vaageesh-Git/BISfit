import fitz  # PyMuPDF
import re
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex pattern for clause headings: e.g., "4.2 Physical Requirements", "1 SCOPE"
CLAUSE_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\s+([A-Z][A-Za-z\s]+)", re.MULTILINE)

def determine_section_type(clause_number_str: str, title: str) -> str:
    title_lower = title.lower()
    
    if "test" in title_lower and "method" in title_lower:
        return "test_methods"
    if "marking" in title_lower:
        return "marking"
    if "annex" in title_lower or "annexure" in title_lower:
        return "annexure"
        
    try:
        main_clause = int(clause_number_str.split('.')[0])
        if main_clause == 1:
            return "scope"
        elif main_clause in [2, 3]:
            return "definitions"
        elif main_clause >= 4:
            return "requirements"
    except ValueError:
        pass
        
    return "requirements"  # Default fallback

def parse_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text from a PDF, splits it by clauses, and returns a list of sections.
    """
    sections = []
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Failed to open PDF {pdf_path}: {e}")
        return sections
        
    current_clause_ref = None
    current_section_type = None
    current_text = []
    current_pages = set()
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        
        # Check if page is potentially scanned/image-only
        if len(text.strip()) < 50:
            image_list = page.get_images()
            if image_list:
                logger.warning(f"Page {page_num} in {pdf_path} might be scanned/image-only. Flagging for manual review.")
        
        # We need to split text by clause pattern
        # Find all matches of the clause pattern
        matches = list(CLAUSE_PATTERN.finditer(text))
        
        if not matches:
            # Continue adding to the current section
            current_text.append(text)
            current_pages.add(page_num)
        else:
            last_idx = 0
            for match in matches:
                # Add text before the match to the current section
                before_text = text[last_idx:match.start()].strip()
                if before_text:
                    current_text.append(before_text)
                    current_pages.add(page_num)
                
                # Save the completed section
                if current_clause_ref and current_text:
                    sections.append({
                        "clause_reference": current_clause_ref,
                        "section_type": current_section_type,
                        "text": "\n".join(current_text).strip(),
                        "source_page_numbers": sorted(list(current_pages))
                    })
                
                # Start new section
                clause_num = match.group(1).strip()
                clause_title = match.group(2).strip()
                current_clause_ref = f"Clause {clause_num} — {clause_title}"
                current_section_type = determine_section_type(clause_num, clause_title)
                current_text = [match.group(0)]  # Include the heading itself
                current_pages = {page_num}
                last_idx = match.end()
                
            # Add any remaining text on the page after the last match
            remaining_text = text[last_idx:].strip()
            if remaining_text:
                current_text.append(remaining_text)
                current_pages.add(page_num)
                
    # Add the final section
    if current_clause_ref and current_text:
        sections.append({
            "clause_reference": current_clause_ref,
            "section_type": current_section_type,
            "text": "\n".join(current_text).strip(),
            "source_page_numbers": sorted(list(current_pages))
        })
        
    doc.close()
    return sections

if __name__ == "__main__":
    # Test block
    sections = parse_pdf("../../data/dataset.pdf")
    for sec in sections[:2]:
        print(sec['clause_reference'], sec['section_type'])
