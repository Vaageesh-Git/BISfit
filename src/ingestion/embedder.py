import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EmbedderFAISS:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine similarity since we normalize)
        self.metadata = []

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return
            
        texts = [chunk['text'] for chunk in chunks]
        logger.info(f"Encoding {len(texts)} chunks...")
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        
        logger.info("Adding embeddings to FAISS index...")
        self.index.add(embeddings)
        self.metadata.extend(chunks)

    def save(self, index_path: str, metadata_path: str):
        # Ensure directories exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        logger.info(f"Saving FAISS index to {index_path}")
        faiss.write_index(self.index, index_path)
        
        logger.info(f"Saving metadata to {metadata_path}")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, index_path: str, metadata_path: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        embedder = cls(model_name)
        embedder.index = faiss.read_index(index_path)
        with open(metadata_path, 'r', encoding='utf-8') as f:
            embedder.metadata = json.load(f)
        return embedder

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['score'] = float(dist)
                results.append(result)
        return results

if __name__ == "__main__":
    from parser import parse_pdf
    from chunker import process_sections
    
    pdf_path = "../../data/dataset.pdf"
    if os.path.exists(pdf_path):
        sections = parse_pdf(pdf_path)
        # Using a dummy standard code/title for now. In a real scenario, this would be inferred from the PDF name or content.
        chunks = process_sections(sections, "BIS_STANDARDS", "BIS Document")
        
        embedder = EmbedderFAISS()
        embedder.add_chunks(chunks)
        embedder.save("../../data/faiss_index.bin", "../../data/chunk_metadata.json")
    else:
        print(f"File not found: {pdf_path}")
