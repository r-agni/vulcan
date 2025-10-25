"""
FastAPI endpoints for RAG system
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore
from .document_indexer import DocumentIndexer
from .query_engine import QueryEngine

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import get_db

load_dotenv()

# Initialize RAG components
embedder = EmbeddingGenerator()
vector_store = VectorStore()

# Pydantic models for API
class QueryRequest(BaseModel):
    query: str = Field(..., description="Question to ask")
    n_results: int = Field(5, description="Number of documents to retrieve", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieved_docs: int
    filters_applied: Optional[Dict[str, Any]] = None

class IndexRequest(BaseModel):
    reports_directory: Optional[str] = Field("./data/analysis_results/reports", description="Reports directory")
    reset: bool = Field(False, description="Reset vector store before indexing")

class IndexResponse(BaseModel):
    status: str
    counts: Dict[str, int]
    total_documents: int

class StatsResponse(BaseModel):
    collection_name: str
    total_documents: int
    persist_directory: str
    last_updated: str

class ConversationRequest(BaseModel):
    question: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    n_results: int = Field(5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None

class SummaryRequest(BaseModel):
    time_range: Optional[str] = None
    zone_id: Optional[int] = None


# Create router
def create_rag_router():
    """Create RAG API router"""
    from fastapi import APIRouter
    router = APIRouter(prefix="/rag", tags=["RAG"])

    @router.post("/query", response_model=QueryResponse)
    async def query(request: QueryRequest):
        """
        Query the RAG system with a question
        
        Returns answer based on indexed Gemini reports and analytics data
        """
        try:
            query_engine = QueryEngine(embedder, vector_store)
            result = query_engine.query(
                question=request.query,
                n_results=request.n_results,
                filters=request.filters
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    @router.post("/index", response_model=IndexResponse)
    async def index_all(request: IndexRequest, db: Session = Depends(get_db)):
        """
        Index all data sources (Gemini reports and analytics)
        
        This will embed and store all documents in the vector database
        """
        try:
            if request.reset:
                vector_store.reset()
                print("Vector store reset")
            
            indexer = DocumentIndexer(embedder, vector_store, db)
            counts = indexer.index_all(reports_directory=request.reports_directory)
            total = sum(counts.values())
            
            return {
                "status": "success",
                "counts": counts,
                "total_documents": total
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    @router.post("/index/new")
    async def index_new(db: Session = Depends(get_db)):
        """
        Index only new documents (not yet implemented - returns full index)
        """
        # For now, just do full index - can optimize later to track indexed docs
        return await index_all(IndexRequest(), db)

    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """
        Get statistics about the vector database
        """
        try:
            stats = vector_store.get_stats()
            return stats
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

    @router.delete("/reset")
    async def reset_store():
        """
        Reset the vector store (delete all documents)
        """
        try:
            vector_store.reset()
            return {"status": "success", "message": "Vector store reset successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

    @router.post("/conversation")
    async def conversation_query(request: ConversationRequest):
        """
        Query with conversation context for multi-turn dialogues
        """
        try:
            query_engine = QueryEngine(embedder, vector_store)
            result = query_engine.get_conversation_response(
                question=request.question,
                conversation_history=request.conversation_history,
                n_results=request.n_results,
                filters=request.filters
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Conversation query failed: {str(e)}")

    @router.post("/summary")
    async def generate_summary(request: SummaryRequest):
        """
        Generate summary insights from indexed data
        """
        try:
            query_engine = QueryEngine(embedder, vector_store)
            summary = query_engine.summarize_insights(
                time_range=request.time_range,
                zone_id=request.zone_id
            )
            return {"summary": summary}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

    @router.get("/peek")
    async def peek_documents(limit: int = 10):
        """
        Peek at the first few documents in the vector store
        """
        try:
            result = vector_store.peek(limit=limit)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Peek failed: {str(e)}")

    return router


# Standalone app for testing
if __name__ == "__main__":
    import uvicorn
    
    app = FastAPI(
        title="Video AI RAG System",
        description="Retrieval Augmented Generation API for querying video analytics and Gemini analysis",
        version="1.0.0"
    )
    
    # Add RAG router
    router = create_rag_router()
    app.include_router(router)
    
    @app.get("/")
    async def root():
        return {
            "message": "Video AI RAG System API",
            "docs": "/docs",
            "endpoints": {
                "query": "POST /rag/query - Ask questions",
                "index": "POST /rag/index - Index all data",
                "stats": "GET /rag/stats - Get statistics",
                "reset": "DELETE /rag/reset - Reset vector store"
            }
        }
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8001)
