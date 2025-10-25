"""
Query engine for RAG-based Q&A
"""

from google import genai
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore

load_dotenv()


class QueryEngine:
    """Handle queries and generate answers using RAG"""

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_store: VectorStore,
        gemini_api_key: str = None
    ):
        """
        Initialize query engine
        
        Args:
            embedding_generator: Instance of EmbeddingGenerator
            vector_store: Instance of VectorStore
            gemini_api_key: Gemini API key for answer generation
        """
        self.embedder = embedding_generator
        self.vector_store = vector_store
        
        # Initialize Gemini client for answer generation
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key required for answer generation")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            n_results: Number of results to return
            filters: Metadata filters (e.g., {"zone_id": 1})
            
        Returns:
            Dictionary with search results
        """
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Search vector store
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=filters
        )
        
        return results

    def generate_answer(
        self,
        query: str,
        context_documents: List[str],
        context_metadatas: List[Dict[str, Any]]
    ) -> str:
        """
        Generate answer using Gemini with retrieved context
        
        Args:
            query: User's question
            context_documents: Retrieved document texts
            context_metadatas: Metadata for each document
            
        Returns:
            Generated answer
        """
        # Build context string with citations
        context_parts = []
        for idx, (doc, meta) in enumerate(zip(context_documents, context_metadatas), 1):
            source = meta.get('source', 'unknown')
            timestamp = meta.get('timestamp', 'N/A')
            
            # Format source information
            if source == 'gemini_report':
                source_info = f"Gemini Report ({meta.get('filename', 'unknown')}, {timestamp})"
            elif source == 'behavior_analysis':
                source_info = f"Behavior Analysis (Person {meta.get('person_id', 'N/A')}, {timestamp})"
            elif source == 'dwell_time':
                source_info = f"Dwell Time ({meta.get('zone_name', 'N/A')}, {timestamp})"
            elif source == 'queue_metrics':
                source_info = f"Queue Metrics ({meta.get('zone_name', 'N/A')}, {timestamp})"
            elif source == 'alert':
                source_info = f"Alert ({meta.get('title', 'N/A')}, {timestamp})"
            else:
                source_info = f"{source} ({timestamp})"
            
            context_parts.append(f"[Source {idx}] {source_info}\n{doc}\n")
        
        context = "\n---\n".join(context_parts)
        
        # Create prompt for Gemini
        prompt = f"""You are an AI assistant analyzing retail store data, including video surveillance analysis and analytics.

Use the following context to answer the user's question. Be specific and cite your sources using [Source X] references.

CONTEXT:
{context}

USER QUESTION:
{query}

INSTRUCTIONS:
- Provide a comprehensive, well-structured answer
- Cite specific sources using [Source X] notation
- Include relevant timestamps, person IDs, zone names, and metrics
- If the context doesn't contain enough information, say so clearly
- Be objective and fact-based
- Organize your answer with clear sections if answering multiple aspects

ANSWER:"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def query(
        self,
        question: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete query pipeline: search + answer generation
        
        Args:
            question: User's question
            n_results: Number of documents to retrieve
            filters: Metadata filters
            
        Returns:
            Dictionary with answer and sources
        """
        print(f"\nProcessing query: {question}")
        print(f"Retrieving top {n_results} relevant documents...")
        
        # Search for relevant documents
        search_results = self.search(question, n_results, filters)
        
        # Extract results
        documents = search_results['documents'][0] if search_results['documents'] else []
        metadatas = search_results['metadatas'][0] if search_results['metadatas'] else []
        distances = search_results['distances'][0] if search_results['distances'] else []
        
        if not documents:
            return {
                "question": question,
                "answer": "No relevant information found in the database. Please try rephrasing your question or check if data has been indexed.",
                "sources": [],
                "retrieved_docs": 0
            }
        
        print(f"Retrieved {len(documents)} documents")
        print("Generating answer with Gemini...")
        
        # Generate answer
        answer = self.generate_answer(question, documents, metadatas)
        
        # Format sources for response
        sources = []
        for idx, (meta, distance) in enumerate(zip(metadatas, distances), 1):
            sources.append({
                "source_number": idx,
                "type": meta.get('source', 'unknown'),
                "timestamp": meta.get('timestamp', 'N/A'),
                "relevance_score": float(1 - distance),  # Convert distance to similarity
                "metadata": meta
            })
        
        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "retrieved_docs": len(documents),
            "filters_applied": filters
        }

    def batch_query(self, questions: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Process multiple questions
        
        Args:
            questions: List of questions
            **kwargs: Additional arguments for query()
            
        Returns:
            List of query results
        """
        results = []
        for question in questions:
            result = self.query(question, **kwargs)
            results.append(result)
        return results

    def get_conversation_response(
        self,
        question: str,
        conversation_history: List[Dict[str, str]] = None,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate response with conversation context
        
        Args:
            question: Current question
            conversation_history: Previous Q&A pairs [{"question": "...", "answer": "..."}]
            n_results: Number of documents to retrieve
            filters: Metadata filters
            
        Returns:
            Query result with conversational context
        """
        # Build context-aware query
        if conversation_history:
            conversation_context = "\n".join([
                f"Previous Q: {item['question']}\nPrevious A: {item['answer']}"
                for item in conversation_history[-3:]  # Last 3 exchanges
            ])
            enhanced_query = f"Given this conversation:\n{conversation_context}\n\nNew question: {question}"
        else:
            enhanced_query = question
        
        # Process query
        result = self.query(enhanced_query, n_results, filters)
        result['original_question'] = question
        
        return result

    def summarize_insights(
        self,
        time_range: Optional[str] = None,
        zone_id: Optional[int] = None
    ) -> str:
        """
        Generate summary insights from indexed data
        
        Args:
            time_range: Time range filter (e.g., "today", "this week")
            zone_id: Specific zone to summarize
            
        Returns:
            Summary text
        """
        filters = {}
        if zone_id:
            filters['zone_id'] = zone_id
        
        # Query for general insights
        questions = [
            "What are the key customer behavior patterns?",
            "What zones had the highest engagement?",
            "Were there any notable alerts or issues?",
            "What were the queue and wait time statistics?"
        ]
        
        insights = []
        for question in questions:
            result = self.query(question, n_results=3, filters=filters)
            insights.append(f"**{question}**\n{result['answer']}\n")
        
        summary = "\n".join(insights)
        
        return summary
