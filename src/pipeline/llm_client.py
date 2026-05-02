import os
import json
import logging
import random
from groq import Groq
from typing import List, Dict, Any
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # Collect all API keys that start with GROQ_API_KEY exclusively from the .env file
        self.api_keys = []
        env_vars = dotenv_values(".env")
        for key, value in env_vars.items():
            if key.startswith("GROQ_API_KEY") and value:
                self.api_keys.append(value)
                
        if not self.api_keys:
            logger.warning("No GROQ_API_KEY found in the .env file.")
            
        self.current_key_idx = 0
        self.model = "llama-3.3-70b-versatile"
        
    def _get_client(self):
        """Returns a Groq client using round-robin API key rotation to bypass rate limits."""
        if not self.api_keys:
            return Groq(api_key="dummy_key") # Will fail but prevents crash on init
            
        key = self.api_keys[self.current_key_idx]
        # Move to next key for the next request
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        return Groq(api_key=key)

    def reformulate_query(self, query: str) -> List[str]:
        """
        Layer 2: Converts a raw user query into 2-3 precise technical search queries optimized for FAISS retrieval.
        """
        system_prompt = (
            "You are a BIS (Bureau of Indian Standards) technical query specialist. "
            "Convert the user's raw query into 2 precise technical search queries "
            "optimized for a vector database containing ONLY Indian Standards (IS codes). "
            "NEVER mention ASTM, ISO, EN, or BS standards. Always focus on Indian Standard keywords, material types, and grades. "
            "Return ONLY a JSON object with a 'queries' key containing an array of strings, e.g., {\"queries\": [\"query 1\", \"query 2\"]}."
        )
        
        try:
            client = self._get_client()
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                # Use the fast active model
                model="llama-3.1-8b-instant",
                max_tokens=200,
                response_format={"type": "json_object"} # We will parse it manually if it fails
            )
            response_text = chat_completion.choices[0].message.content
            # Safely parse the JSON response
            try:
                queries = json.loads(response_text)
                if isinstance(queries, dict):
                    # Sometimes the model returns {"queries": [...]}
                    for k, v in queries.items():
                        if isinstance(v, list): return v
                elif isinstance(queries, list):
                    return queries
            except json.JSONDecodeError:
                pass
        except Exception as e:
            logger.error(f"Error reformulating query: {e}")
            
        return [query] # Fallback to original query
    def generate_and_extract(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combined Layer 3 & 4: Uses the LLM to read chunks, output the final narrative response, AND extract the top IS standards in one single call.
        """
        context = ""
        for i, chunk in enumerate(retrieved_chunks[:10]):
            context += f"Document {i+1}:\n{chunk.get('text', '')}\n\n"
            
        system_prompt = (
            "You are a BIS compliance evaluator. Your task is to answer the user's query based ONLY on the provided documents.\n"
            "If the documents do not contain the answer, explicitly state that.\n"
            "You must ALSO extract the EXACT Indian Standard (IS) codes that answer the query (e.g., 'IS 2185 (Part 2): 1983').\n"
            "You MUST output your response in strict JSON format matching exactly this schema:\n"
            "{\n"
            "  \"response\": \"Your detailed narrative answer here...\",\n"
            "  \"standards\": [\"IS XXXX\", \"IS YYYY\"]\n"
            "}"
        )
        
        try:
            client = self._get_client()
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}\n\nDocuments:\n{context}"}
                ],
                model=self.model,
                temperature=0.0,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            response_text = chat_completion.choices[0].message.content
            try:
                parsed = json.loads(response_text)
                return {
                    "response": parsed.get("response", "Could not generate response."),
                    "standards": parsed.get("standards", [])
                }
            except json.JSONDecodeError:
                pass
        except Exception as e:
            logger.error(f"Error generating and extracting: {e}")
            
        return {"response": "Error generating response.", "standards": []}

if __name__ == "__main__":
    # Test
    client = LLMClient()
    print(client.generate_response("What is the strength of 53 grade OPC?", [{"standard_code": "IS 12269", "text": "The minimum 28-day compressive strength of 53 grade OPC is 53 MPa."}]))
