"""
Enhanced query engine using Claude with intelligent routing and visualization support
"""

from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore
from .claude_client import ClaudeClient
from .visualization import ChartGenerator
from .chat_session import ChatSession

load_dotenv()


class ClaudeQueryEngine:
    """Enhanced RAG query engine using Claude with intelligent routing"""

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_store: VectorStore,
        claude_api_key: str = None,
        metadata_collection: str = "metadata_collection",
        analysis_collection: str = "analysis_collection"
    ):
        """
        Initialize Claude-powered query engine

        Args:
            embedding_generator: Instance of EmbeddingGenerator
            vector_store: Instance of VectorStore
            claude_api_key: Anthropic API key
            metadata_collection: Name of metadata collection
            analysis_collection: Name of analysis collection
        """
        self.embedder = embedding_generator
        self.vector_store = vector_store
        self.metadata_collection = metadata_collection
        self.analysis_collection = analysis_collection

        # Initialize Claude client
        api_key = claude_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.claude = ClaudeClient(api_key=api_key)

        # Initialize chart generator
        self.chart_gen = ChartGenerator()

        # Ensure collections exist
        self.vector_store.get_or_create_collection(metadata_collection, "Structured metadata")
        self.vector_store.get_or_create_collection(analysis_collection, "Verbal analysis")

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine search strategy

        Args:
            query: User's question

        Returns:
            Dict with search strategy
        """
        return self.claude.analyze_query_intent(query)

    def search_collections(
        self,
        query: str,
        search_metadata: bool = True,
        search_analysis: bool = False,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search one or both collections

        Args:
            query: Search query
            search_metadata: Search metadata collection
            search_analysis: Search analysis collection
            n_results: Number of results per collection
            filters: Metadata filters

        Returns:
            Combined search results
        """
        query_embedding = self.embedder.embed_query(query)

        results = {
            "metadata_results": [],
            "analysis_results": [],
            "combined_documents": [],
            "combined_metadatas": []
        }

        # Search metadata collection (PRIMARY)
        if search_metadata:
            try:
                metadata_results = self.vector_store.query_collection(
                    self.metadata_collection,
                    query_embedding,
                    n_results=n_results,
                    where=filters
                )
                if metadata_results and metadata_results.get('documents'):
                    results["metadata_results"] = metadata_results
                    results["combined_documents"].extend(metadata_results['documents'][0])
                    results["combined_metadatas"].extend(metadata_results['metadatas'][0])
            except Exception as e:
                print(f"Error searching metadata collection: {e}")

        # Search analysis collection (SECONDARY)
        if search_analysis:
            try:
                analysis_results = self.vector_store.query_collection(
                    self.analysis_collection,
                    query_embedding,
                    n_results=n_results,
                    where=filters
                )
                if analysis_results and analysis_results.get('documents'):
                    results["analysis_results"] = analysis_results
                    results["combined_documents"].extend(analysis_results['documents'][0])
                    results["combined_metadatas"].extend(analysis_results['metadatas'][0])
            except Exception as e:
                print(f"Error searching analysis collection: {e}")

        return results

    def generate_answer(
        self,
        query: str,
        context_documents: List[str],
        context_metadatas: List[Dict[str, Any]],
        session: Optional[ChatSession] = None
    ) -> str:
        """
        Generate answer using Claude with retrieved context

        Args:
            query: User's question
            context_documents: Retrieved document texts
            context_metadatas: Metadata for each document
            session: Optional chat session for context

        Returns:
            Generated answer
        """
        # Build context string
        context_parts = []
        for idx, (doc, meta) in enumerate(zip(context_documents, context_metadatas), 1):
            source = meta.get('source', 'unknown')
            timestamp = meta.get('timestamp', 'N/A')

            source_info = f"[Source {idx}] {source} | {timestamp}"
            context_parts.append(f"{source_info}\n{doc}\n")

        context = "\n---\n".join(context_parts)

        # Build system prompt
        system = f"""You are an AI assistant analyzing retail store surveillance and analytics data.

Use the provided context to answer the user's question accurately and comprehensively.

IMPORTANT GUIDELINES:
- Cite sources using [Source X] notation
- Include specific metrics, timestamps, and data points
- If context is insufficient, clearly state what information is missing
- Be objective and data-driven
- Organize your answer clearly with sections if needed
- For numeric questions, provide exact numbers from the context"""

        # Build user prompt
        if session and len(session.messages) > 0:
            # Include conversation history
            messages = session.get_context_for_claude(max_messages=6)
            messages.append({
                "role": "user",
                "content": f"""CONTEXT:
{context}

QUESTION:
{query}

Please answer based on the context provided above."""
            })
        else:
            messages = [{
                "role": "user",
                "content": f"""CONTEXT:
{context}

QUESTION:
{query}

Please answer based on the context provided above."""
            }]

        # Generate answer
        try:
            answer = self.claude.generate(
                prompt=messages[0]["content"] if len(messages) == 1 else "",
                system=system,
                max_tokens=2048,
                temperature=0.7
            )

            if len(messages) > 1:
                # Use multi-turn conversation
                response = self.claude.generate_with_tools(
                    messages=messages[:-1] + [messages[-1]],
                    system=system,
                    max_tokens=2048,
                    temperature=0.7,
                    auto_execute_tools=False
                )
                answer = response.get("text", "Unable to generate response")

            return answer

        except Exception as e:
            error_msg = str(e)
            print(f"Error generating answer with Claude: {error_msg}")
            return f"⚠️ Error generating answer: {error_msg}"

    def query(
        self,
        question: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[ChatSession] = None
    ) -> Dict[str, Any]:
        """
        Complete query pipeline with intelligent routing

        Args:
            question: User's question
            n_results: Number of documents to retrieve
            filters: Metadata filters
            session: Optional chat session

        Returns:
            Dict with answer, sources, and metadata
        """
        import time
        start_time = time.time()

        print(f"\n[Claude RAG] Processing: {question}")

        # 1. Analyze query intent
        print("[Claude RAG] Analyzing query intent...")
        intent = self.analyze_query(question)
        search_metadata = intent.get("search_metadata", True)
        search_analysis = intent.get("search_analysis", False)
        needs_viz = intent.get("needs_visualization", False)
        viz_type = intent.get("visualization_type")

        print(f"[Claude RAG] Intent: metadata={search_metadata}, analysis={search_analysis}, viz={needs_viz}")

        # 2. Search collections
        print(f"[Claude RAG] Searching collections...")
        search_results = self.search_collections(
            question,
            search_metadata=search_metadata,
            search_analysis=search_analysis,
            n_results=n_results,
            filters=filters
        )

        documents = search_results["combined_documents"]
        metadatas = search_results["combined_metadatas"]

        if not documents:
            return {
                "question": question,
                "answer": "No relevant information found. Please try rephrasing your question or check if data has been indexed.",
                "sources": [],
                "visualization": None,
                "intent": intent
            }

        print(f"[Claude RAG] Retrieved {len(documents)} documents")

        # 3. Generate answer
        print("[Claude RAG] Generating answer with Claude...")
        answer = self.generate_answer(question, documents, metadatas, session)

        # 4. Generate visualization if needed
        visualization = None
        if needs_viz and viz_type:
            print(f"[Claude RAG] Generating {viz_type} visualization...")
            try:
                # Prepare data from metadatas for visualization
                viz_data = self._prepare_viz_data(metadatas)
                if viz_data:
                    if viz_type == "line":
                        visualization = self.chart_gen.generate_line_chart(
                            viz_data,
                            x_key="timestamp",
                            y_key=self._get_numeric_field(viz_data),
                            title=f"Analysis: {question[:50]}..."
                        )
                    elif viz_type == "bar":
                        visualization = self.chart_gen.generate_bar_chart(
                            viz_data,
                            x_key=self._get_categorical_field(viz_data),
                            y_key=self._get_numeric_field(viz_data),
                            title=f"Analysis: {question[:50]}..."
                        )
                    elif viz_type == "pie":
                        viz_data_agg = self._aggregate_for_pie(viz_data)
                        if viz_data_agg:
                            visualization = self.chart_gen.generate_pie_chart(
                                viz_data_agg,
                                labels_key="labels",
                                values_key="values",
                                title=f"Distribution: {question[:50]}..."
                            )
                    elif viz_type == "timeline":
                        visualization = self.chart_gen.generate_timeline(
                            viz_data,
                            time_key="timestamp",
                            value_key=self._get_numeric_field(viz_data),
                            title=f"Timeline: {question[:50]}..."
                        )
            except Exception as e:
                print(f"Error generating visualization: {e}")

        # Format sources
        sources = []
        for idx, (meta, doc) in enumerate(zip(metadatas, documents), 1):
            sources.append({
                "source_number": idx,
                "type": meta.get('source', 'unknown'),
                "timestamp": meta.get('timestamp', 'N/A'),
                "preview": doc[:200] + "..." if len(doc) > 200 else doc,
                "metadata": meta
            })

        total_time = time.time() - start_time
        print(f"[Claude RAG] Query completed in {total_time:.2f}s")

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "visualization": visualization,
            "intent": intent,
            "retrieved_docs": len(documents),
            "performance": {
                "total_time": round(total_time, 2)
            }
        }

    def _prepare_viz_data(self, metadatas: List[Dict[str, Any]]) -> Dict[str, List]:
        """Prepare data from metadatas for visualization"""
        data = {}
        for meta in metadatas:
            for key, value in meta.items():
                if key not in data:
                    data[key] = []
                data[key].append(value)
        return data

    def _get_numeric_field(self, data: Dict[str, List]) -> str:
        """Get first numeric field from data"""
        for key, values in data.items():
            if key != 'timestamp' and values and isinstance(values[0], (int, float)):
                return key
        return list(data.keys())[1] if len(data) > 1 else list(data.keys())[0]

    def _get_categorical_field(self, data: Dict[str, List]) -> str:
        """Get first categorical field from data"""
        for key, values in data.items():
            if key != 'timestamp' and values and isinstance(values[0], str):
                return key
        return list(data.keys())[0]

    def _aggregate_for_pie(self, data: Dict[str, List]) -> Optional[Dict[str, List]]:
        """Aggregate data for pie chart"""
        # Find a categorical field to group by
        cat_field = self._get_categorical_field(data)
        if not cat_field:
            return None

        # Count occurrences
        from collections import Counter
        counts = Counter(data[cat_field])

        return {
            "labels": list(counts.keys()),
            "values": list(counts.values())
        }
