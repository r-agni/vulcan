"""
Embedding generation using Gemini API
"""

from google import genai
from typing import List, Union
import os
from dotenv import load_dotenv

load_dotenv()


class EmbeddingGenerator:
    """Generate embeddings using Gemini's text-embedding model"""

    def __init__(self, api_key: str = None):
        """
        Initialize embedding generator
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not provided and GEMINI_API_KEY not set in environment")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "models/text-embedding-004"

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of float values representing the embedding
        """
        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=text
            )
            # Access the embedding from the response object
            # The response has embeddings in a list
            if hasattr(result, 'embeddings') and len(result.embeddings) > 0:
                return result.embeddings[0].values
            elif hasattr(result, 'embedding'):
                return result.embedding
            else:
                # Fallback: try to get the values directly
                return list(result.values)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        try:
            embeddings = []
            # Process in batches to avoid rate limits
            batch_size = 100
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                for text in batch:
                    result = self.client.models.embed_content(
                        model=self.model,
                        contents=text
                    )
                    # Access the embedding from the response object
                    if hasattr(result, 'embeddings') and len(result.embeddings) > 0:
                        embeddings.append(result.embeddings[0].values)
                    elif hasattr(result, 'embedding'):
                        embeddings.append(result.embedding)
                    else:
                        embeddings.append(list(result.values))
            
            return embeddings
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            raise

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query (same as embed_text, but semantically clear)
        
        Args:
            query: Query text to embed
            
        Returns:
            List of float values representing the query embedding
        """
        return self.embed_text(query)
