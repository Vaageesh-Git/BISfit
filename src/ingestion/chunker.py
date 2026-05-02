import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def extract_standard_code(text: str) -> str:
    match = re.search(r"IS\s*\n*\s*\d+(?:\s*[:\-]\s*\d{4})?", text)
    if match:
        # Clean up newlines and extra spaces
        cleaned = re.sub(r'\s+', ' ', match.group(0)).strip()
        return cleaned
    return ""

def chunk_text(text: str, max_words: int = 450) -> List[str]:
    """
    Split text into chunks of roughly max_words, breaking at paragraphs.
    We use words as a proxy for tokens (approx 1.3 tokens per word).
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for para in paragraphs:
        # Replace single newlines with space to clean up formatting within paragraphs
        clean_para = para.replace('\n', ' ').strip()
        if not clean_para:
            continue
            
        words = clean_para.split()
        para_word_count = len(words)
        
        if current_word_count + para_word_count > max_words and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_word_count = 0
            
        current_chunk.append(clean_para)
        current_word_count += para_word_count
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def process_sections(sections: List[Dict[str, Any]], default_code: str = "UNKNOWN", standard_title: str = "BIS Document") -> List[Dict[str, Any]]:
    """
    Takes parsed sections and converts them to chunks with metadata.
    """
    chunks_with_metadata = []
    current_standard_code = default_code
    
    for section in sections:
        clause_ref = section.get('clause_reference', 'Unknown Clause')
        section_type = section.get('section_type', 'requirements')
        text = section.get('text', '')
        
        # Split long sections into chunks
        text_chunks = chunk_text(text)
        
        for idx, chunk_text_content in enumerate(text_chunks):
            # Try to find standard code in this chunk
            found_code = extract_standard_code(chunk_text_content)
            if found_code:
                current_standard_code = found_code
                
            # Prepend metadata to text
            prefix = f"[{current_standard_code} | {clause_ref}] "
            full_text = prefix + chunk_text_content
            
            chunk_metadata = {
                "chunk_id": f"{current_standard_code.replace(' ', '')}-{clause_ref.replace(' ', '')}-{idx}",
                "standard_code": current_standard_code,
                "standard_title": standard_title,
                "clause_reference": clause_ref,
                "section_type": section_type,
                "text": full_text
            }
            chunks_with_metadata.append(chunk_metadata)
            
    return chunks_with_metadata

if __name__ == "__main__":
    # Test block
    from parser import parse_pdf
    sections = parse_pdf("../../data/dataset.pdf")
    chunks = process_sections(sections, "IS 12269:2013", "Ordinary Portland Cement")
    print(f"Generated {len(chunks)} chunks.")
    if chunks:
        print("Sample Chunk:", chunks[0])
