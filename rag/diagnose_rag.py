"""
RAG System Diagnostic Tool
Check if RAG system is properly configured and populated
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def diagnose_rag_system():
    """Run diagnostics on RAG system"""
    print("=" * 60)
    print("RAG SYSTEM DIAGNOSTICS")
    print("=" * 60)

    # Check 1: API Key
    print("\n[1/5] Checking Gemini API Key...")
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print(f"✓ API Key found (length: {len(api_key)})")
    else:
        print("✗ API Key NOT found in environment")
        print("  Please set GEMINI_API_KEY in .env file")
        return False

    # Check 2: Import modules
    print("\n[2/5] Checking RAG modules...")
    try:
        from rag.embeddings import EmbeddingGenerator
        from rag.vector_store import VectorStore
        from rag.query_engine import QueryEngine
        print("✓ All RAG modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import modules: {e}")
        return False

    # Check 3: Vector Store
    print("\n[3/5] Checking Vector Store...")
    try:
        vector_store = VectorStore()
        doc_count = vector_store.count_documents()
        print(f"✓ Vector store initialized")
        print(f"  Documents in store: {doc_count}")

        if doc_count == 0:
            print("  ⚠️  WARNING: No documents found in vector store!")
            print("  Please index data using: POST /rag/index")
        else:
            # Peek at some documents
            peek_result = vector_store.peek(limit=3)
            if peek_result and 'ids' in peek_result:
                print(f"  Sample document IDs: {peek_result['ids'][:3]}")
    except Exception as e:
        print(f"✗ Vector store error: {e}")
        return False

    # Check 4: Embedding Generator
    print("\n[4/5] Checking Embedding Generator...")
    try:
        embedder = EmbeddingGenerator()
        test_text = "This is a test"
        embedding = embedder.embed_text(test_text)
        print(f"✓ Embedding generator working")
        print(f"  Embedding dimension: {len(embedding)}")
    except Exception as e:
        print(f"✗ Embedding error: {e}")
        print("  This might be an API key or network issue")
        return False

    # Check 5: Query Engine
    print("\n[5/5] Testing Query Engine...")
    if doc_count > 0:
        try:
            query_engine = QueryEngine(embedder, vector_store)
            test_query = "What happened today?"
            print(f"  Testing query: '{test_query}'")

            result = query_engine.query(test_query, n_results=2)

            if result.get('answer'):
                print("✓ Query engine working")
                print(f"  Retrieved {result.get('retrieved_docs', 0)} documents")
                if 'performance' in result:
                    perf = result['performance']
                    print(f"  Performance: {perf.get('total_time', 'N/A')}s total")
            else:
                print("⚠️  Query completed but no answer generated")
        except Exception as e:
            print(f"✗ Query engine error: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("⚠️  Skipping query test (no documents in store)")

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    if doc_count == 0:
        print("Status: ⚠️  NEEDS INDEXING")
        print("\nNext steps:")
        print("1. Start your FastAPI server")
        print("2. Index data with: curl -X POST http://localhost:8000/rag/index")
        print("3. Or use the API docs: http://localhost:8000/docs")
    else:
        print("Status: ✓ READY")
        print(f"\nVector store has {doc_count} documents indexed")
        print("RAG system is ready to answer queries!")

    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = diagnose_rag_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
