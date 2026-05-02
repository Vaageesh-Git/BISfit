import argparse
import json
import time
import logging
from src.pipeline.rag import RAGPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="BIS Standards RAG Inference")
    parser.add_argument("--input", type=str, required=True, help="Path to input JSON file")
    parser.add_argument("--output", type=str, required=True, help="Path to output JSON file")
    args = parser.parse_args()

    # Load input queries
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return

    # Initialize pipeline
    try:
        rag = RAGPipeline(index_path="data/faiss_index.bin", metadata_path="data/chunk_metadata.json")
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        return

    results = []
    
    for item in input_data:
        item_id = item.get("id", "unknown")
        query = item.get("query", "")
        
        logger.info(f"Processing query ID: {item_id}")
        
        # Sleep to avoid hitting Groq's Free Tier Requests-Per-Minute limit during bulk evaluation.
        # This prevents the Groq client from sleeping *during* the query and inflating the latency.
        time.sleep(3)
        
        start_time = time.time()
        
        try:
            res = rag.process_query(query, top_k=5)
            retrieved_standards = res["retrieved_standards"]
            response_text = res["response"]
        except Exception as e:
            logger.error(f"Error processing query {item_id}: {e}")
            retrieved_standards = []
            response_text = "Error processing query."
            
        latency = time.time() - start_time
        
        output_item = {
            "id": item_id,
            "query": query,
            "expected_standards": item.get("expected_standards", []),
            "retrieved_standards": retrieved_standards,
            "response": response_text,
            "latency_seconds": round(latency, 4)
        }
        results.append(output_item)

    # Write output
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        logger.info(f"Results successfully written to {args.output}")
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")

if __name__ == "__main__":
    main()
