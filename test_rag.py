"""
Test script for RAG system
Demonstrates indexing and querying functionality
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag import EmbeddingGenerator, VectorStore, DocumentIndexer, QueryEngine
from app.database import SessionLocal


def test_indexing():
    """Test indexing all data sources"""
    print("\n" + "="*70)
    print("TESTING RAG INDEXING")
    print("="*70)
    
    try:
        # Initialize components
        print("\nInitializing RAG components...")
        embedder = EmbeddingGenerator()
        vector_store = VectorStore()
        db = SessionLocal()
        
        # Create indexer
        indexer = DocumentIndexer(embedder, vector_store, db)
        
        # Index all data
        print("\nStarting indexing process...")
        counts = indexer.index_all()
        
        print("\n" + "="*70)
        print("INDEXING COMPLETE")
        print("="*70)
        print(f"Total documents indexed: {sum(counts.values())}")
        for source, count in counts.items():
            print(f"  - {source}: {count}")
        
        # Get stats
        stats = vector_store.get_stats()
        print(f"\nVector store stats:")
        print(f"  - Collection: {stats['collection_name']}")
        print(f"  - Total documents: {stats['total_documents']}")
        print(f"  - Location: {stats['persist_directory']}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Indexing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_queries():
    """Test various queries"""
    print("\n" + "="*70)
    print("TESTING RAG QUERIES")
    print("="*70)
    
    try:
        # Initialize components
        embedder = EmbeddingGenerator()
        vector_store = VectorStore()
        query_engine = QueryEngine(embedder, vector_store)
        
        # Test queries
        test_questions = [
            "What shopping behaviors were observed?",
            "What were the emotional states of customers?",
            "Which zones had the longest dwell times?",
            "What alerts were generated?",
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'='*70}")
            print(f"QUERY {i}: {question}")
            print('='*70)
            
            try:
                result = query_engine.query(question, n_results=3)
                
                print(f"\n📊 ANSWER:")
                print(result['answer'])
                
                print(f"\n📚 SOURCES ({result['retrieved_docs']} documents):")
                for source in result['sources'][:3]:  # Show first 3
                    print(f"  - [{source['source_number']}] {source['type']}")
                    print(f"    Timestamp: {source['timestamp']}")
                    print(f"    Relevance: {source['relevance_score']:.2%}")
                
            except Exception as e:
                print(f"❌ Query failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Query testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filtered_query():
    """Test query with metadata filters"""
    print("\n" + "="*70)
    print("TESTING FILTERED QUERIES")
    print("="*70)
    
    try:
        embedder = EmbeddingGenerator()
        vector_store = VectorStore()
        query_engine = QueryEngine(embedder, vector_store)
        
        # Test with filter
        print("\nQuerying with filter (source: gemini_report)...")
        result = query_engine.query(
            "What did the analysis reveal?",
            n_results=3,
            filters={"source": "gemini_report"}
        )
        
        print(f"\n📊 FILTERED ANSWER:")
        print(result['answer'])
        
        print(f"\n📚 SOURCES (filtered):")
        for source in result['sources']:
            print(f"  - {source['type']} at {source['timestamp']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Filtered query failed: {e}")
        return False


def test_conversation():
    """Test conversational queries"""
    print("\n" + "="*70)
    print("TESTING CONVERSATIONAL QUERIES")
    print("="*70)
    
    try:
        embedder = EmbeddingGenerator()
        vector_store = VectorStore()
        query_engine = QueryEngine(embedder, vector_store)
        
        conversation_history = []
        
        questions = [
            "Who were the customers in the store?",
            "What were their emotional states?",
            "Did any show purchase intent?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'='*50}")
            print(f"TURN {i}: {question}")
            print('='*50)
            
            result = query_engine.get_conversation_response(
                question=question,
                conversation_history=conversation_history,
                n_results=2
            )
            
            print(f"\n🤖 RESPONSE:")
            print(result['answer'])
            
            # Add to history
            conversation_history.append({
                "question": question,
                "answer": result['answer']
            })
        
        return True
        
    except Exception as e:
        print(f"\n❌ Conversation test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("RAG SYSTEM TEST SUITE")
    print("="*70)
    
    # Check if data exists
    if not os.path.exists("./data/analysis_results/reports"):
        print("\n⚠️  Warning: No Gemini reports found at ./data/analysis_results/reports")
        print("The indexing will still run but may have limited data.")
    
    # Run tests
    results = {
        "Indexing": test_indexing(),
        "Basic Queries": test_queries(),
        "Filtered Queries": test_filtered_query(),
        "Conversational Queries": test_conversation()
    }
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
