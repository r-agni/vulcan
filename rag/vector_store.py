"""
Vector store management using ChromaDB
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import os
from datetime import datetime


class VectorStore:
    """Manage vector database using ChromaDB"""

    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """
        Initialize ChromaDB vector store
        
        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = persist_directory
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection_name = "videoai_analytics"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Video AI analytics and Gemini analysis data"}
        )

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add documents with embeddings to the vector store
        
        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts for each document
            ids: List of unique IDs for each document
        """
        try:
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            print(f"Error adding documents to vector store: {e}")
            raise

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents
        
        Args:
            query_embedding: Query vector embedding
            n_results: Number of results to return
            where: Metadata filter (e.g., {"zone_id": 1})
            where_document: Document content filter
            
        Returns:
            Dictionary with ids, documents, metadatas, and distances
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            print(f"Error querying vector store: {e}")
            raise

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID
        
        Args:
            document_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            result = self.collection.get(ids=[document_id])
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0],
                    'metadata': result['metadatas'][0]
                }
            return None
        except Exception as e:
            print(f"Error getting document: {e}")
            return None

    def delete_documents(self, ids: List[str]):
        """
        Delete documents by IDs
        
        Args:
            ids: List of document IDs to delete
        """
        try:
            self.collection.delete(ids=ids)
            print(f"Deleted {len(ids)} documents from vector store")
        except Exception as e:
            print(f"Error deleting documents: {e}")
            raise

    def update_document(
        self,
        document_id: str,
        document: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update a document in the vector store
        
        Args:
            document_id: ID of document to update
            document: New document text (optional)
            embedding: New embedding (optional)
            metadata: New metadata (optional)
        """
        try:
            update_data = {"ids": [document_id]}
            if document:
                update_data["documents"] = [document]
            if embedding:
                update_data["embeddings"] = [embedding]
            if metadata:
                update_data["metadatas"] = [metadata]
            
            self.collection.update(**update_data)
            print(f"Updated document {document_id}")
        except Exception as e:
            print(f"Error updating document: {e}")
            raise

    def count_documents(self) -> int:
        """
        Get total number of documents in the collection
        
        Returns:
            Count of documents
        """
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error counting documents: {e}")
            return 0

    def reset(self):
        """
        Delete all documents and reset the collection
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Video AI analytics and Gemini analysis data"}
            )
            print("Vector store reset successfully")
        except Exception as e:
            print(f"Error resetting vector store: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store
        
        Returns:
            Dictionary with stats
        """
        return {
            "collection_name": self.collection_name,
            "total_documents": self.count_documents(),
            "persist_directory": self.persist_directory,
            "last_updated": datetime.utcnow().isoformat()
        }

    def peek(self, limit: int = 10) -> Dict[str, Any]:
        """
        Peek at the first few documents in the collection
        
        Args:
            limit: Number of documents to peek at
            
        Returns:
            Dictionary with documents
        """
        try:
            result = self.collection.peek(limit=limit)
            return result
        except Exception as e:
            print(f"Error peeking at documents: {e}")
            return {}
