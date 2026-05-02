import os
import sys
import logging
import re
from typing import Dict, Any

# Add src to path to import ingestion modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__name__), 'src')))

from ingestion.embedder import EmbedderFAISS
from pipeline.llm_client import LLMClient

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, index_path: str = "data/faiss_index.bin", metadata_path: str = "data/chunk_metadata.json"):
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            logger.error(f"Index or metadata not found at {index_path}, {metadata_path}")
            raise FileNotFoundError("FAISS index or metadata missing. Run ingestion first.")
            
        logger.info("Loading FAISS Embedder...")
        self.embedder = EmbedderFAISS.load(index_path, metadata_path)
        logger.info("Initializing LLM Client...")
        self.llm_client = LLMClient()
        
    def process_query(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        Runs the full RAG pipeline for a given query.
        Returns retrieved standard codes and the generated response.
        """
        logger.info(f"Reformulating query: {query}")
        search_queries = self.llm_client.reformulate_query(query)
        if query not in search_queries:
            search_queries.append(query)
        logger.info(f"Reformulated into: {search_queries}")
        
        all_retrieved_chunks = []
        chunk_ids_seen = set()
        
        for sq in search_queries:
            chunks = self.embedder.search(sq, top_k=top_k)
            for chunk in chunks:
                if chunk['chunk_id'] not in chunk_ids_seen:
                    all_retrieved_chunks.append(chunk)
                    chunk_ids_seen.add(chunk['chunk_id'])
                    
        # Sort by score descending and take top_k
        all_retrieved_chunks = sorted(all_retrieved_chunks, key=lambda x: x.get('score', 0), reverse=True)[:top_k]
        
        logger.info(f"Using LLM to generate response and extract standards...")
        result = self.llm_client.generate_and_extract(query, all_retrieved_chunks)
        response_text = result.get("response", "Could not generate response.")
        llm_extracted_standards = result.get("standards", [])
        
        if llm_extracted_standards:
            standard_codes = []
            for code in llm_extracted_standards:
                normalized_code = re.sub(r'\s*([:-])\s*', r'\1', code).strip()
                normalized_code = re.sub(r'\s+', ' ', normalized_code).upper()
                if normalized_code not in standard_codes:
                    standard_codes.append(normalized_code)
        else:
            # Fallback to Regex
            code_counts = {}
            for chunk in all_retrieved_chunks:
                text = chunk.get("text", "")
                matches = re.findall(r'IS\s*\d+(?:\s*\(\s*Part\s*\d+\s*\))?(?:\s*[:\-]\s*\d{4})?', text, re.IGNORECASE)
                meta_code = chunk.get("standard_code", "")
                if meta_code and meta_code != "BIS_STANDARDS":
                    matches.append(meta_code)
                unique_matches_in_chunk = set()
                for code in matches:
                    normalized_code = re.sub(r'\s*([:-])\s*', r'\1', code).strip()
                    normalized_code = re.sub(r'\s+', ' ', normalized_code).upper()
                    if normalized_code != "BIS_STANDARDS":
                        unique_matches_in_chunk.add(normalized_code)
                for nc in unique_matches_in_chunk:
                    code_counts[nc] = code_counts.get(nc, 0) + 1
            standard_codes = [code for code, count in sorted(code_counts.items(), key=lambda x: x[1], reverse=True)]
                
        return {
            "retrieved_standards": standard_codes,
            "response": response_text
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rag = RAGPipeline("../../data/faiss_index.bin", "../../data/chunk_metadata.json")
    res = rag.process_query("What are the strength requirements for 53 grade cement?", top_k=3)
    print(res)
