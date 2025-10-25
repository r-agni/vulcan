## RAG (Retrieval Augmented Generation) System

A powerful question-answering system that combines vector search with Gemini AI to query your video analytics and behavioral analysis data.

## Overview

This RAG system indexes and makes searchable:
- **Gemini Analysis Reports** - AI-generated behavioral insights, shopping patterns, emotional states
- **Dwell Time Analytics** - Time spent in zones, engagement scores
- **Queue Metrics** - Wait times, queue lengths, customer satisfaction
- **Alert Logs** - System alerts and notifications
- **Occupancy Data** - Zone occupancy and traffic patterns

## Architecture

```
rag/
├── __init__.py              # Package initialization
├── embeddings.py            # Gemini text-embedding-004 integration
├── vector_store.py          # ChromaDB vector database
├── document_indexer.py      # Index Gemini reports + analytics
├── query_engine.py          # Query processing & answer generation
├── rag_api.py              # FastAPI endpoints
└── README.md               # This file
```

## Quick Start

### 1. Index Your Data

First, index all your Gemini reports and analytics data:

```python
from rag import EmbeddingGenerator, VectorStore, DocumentIndexer
from app.database import SessionLocal

# Initialize components
embedder = EmbeddingGenerator()
vector_store = VectorStore()
db = SessionLocal()

# Create indexer and index all data
indexer = DocumentIndexer(embedder, vector_store, db)
counts = indexer.index_all()

print(f"Indexed {sum(counts.values())} documents")
```

### 2. Query the System

```python
from rag import QueryEngine

# Initialize query engine
query_engine = QueryEngine(embedder, vector_store)

# Ask questions
result = query_engine.query(
    "What shopping behaviors were observed in the checkout zone?"
)

print(result['answer'])
print(f"Sources: {len(result['sources'])}")
```

## API Usage

### Start the API Server

```bash
python -m rag.rag_api
```

The API will be available at `http://localhost:8001`

### API Endpoints

#### 1. Query (Ask Questions)

```bash
curl -X POST "http://localhost:8001/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were the emotional states of customers?",
    "n_results": 5
  }'
```

**With Filters:**
```bash
curl -X POST "http://localhost:8001/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What happened in zone 1?",
    "n_results": 5,
    "filters": {"zone_id": 1}
  }'
```

#### 2. Index Data

```bash
curl -X POST "http://localhost:8001/rag/index" \
  -H "Content-Type: application/json" \
  -d '{
    "reports_directory": "./data/analysis_results/reports",
    "reset": false
  }'
```

#### 3. Get Statistics

```bash
curl -X GET "http://localhost:8001/rag/stats"
```

#### 4. Conversational Query

```bash
curl -X POST "http://localhost:8001/rag/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What about their emotional states?",
    "conversation_history": [
      {
        "question": "Who was in the store?",
        "answer": "Several customers were observed..."
      }
    ]
  }'
```

#### 5. Generate Summary

```bash
curl -X POST "http://localhost:8001/rag/summary" \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": 1
  }'
```

#### 6. Reset Vector Store

```bash
curl -X DELETE "http://localhost:8001/rag/reset"
```

## Example Queries

### Customer Behavior
```python
result = query_engine.query(
    "What shopping behaviors were observed today?"
)
```

### Zone Analysis
```python
result = query_engine.query(
    "Which zones had the longest dwell times?",
    filters={"source": "dwell_time"}
)
```

### Emotional States
```python
result = query_engine.query(
    "What emotional states were observed in the checkout queue?"
)
```

### Movement Patterns
```python
result = query_engine.query(
    "Describe the movement patterns of customers in the store"
)
```

### Product Interest
```python
result = query_engine.query(
    "Which products or areas received the most attention?"
)
```

### Alert Analysis
```python
result = query_engine.query(
    "What alerts were generated and why?",
    filters={"source": "alert"}
)
```

## Python API Reference

### EmbeddingGenerator

```python
from rag import EmbeddingGenerator

embedder = EmbeddingGenerator(api_key="your_api_key")

# Single text
embedding = embedder.embed_text("Customer entered the store")

# Batch
embeddings = embedder.embed_batch(["Text 1", "Text 2", "Text 3"])
```

### VectorStore

```python
from rag import VectorStore

store = VectorStore(persist_directory="./data/chroma_db")

# Add documents
store.add_documents(
    documents=["doc1", "doc2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    metadatas=[{"source": "gemini"}, {"source": "analytics"}],
    ids=["doc1", "doc2"]
)

# Query
results = store.query(
    query_embedding=[0.1, 0.2, ...],
    n_results=5,
    where={"zone_id": 1}
)

# Stats
stats = store.get_stats()
print(f"Total documents: {stats['total_documents']}")
```

### DocumentIndexer

```python
from rag import DocumentIndexer

indexer = DocumentIndexer(embedder, vector_store, db_session)

# Index specific sources
indexer.index_gemini_reports()
indexer.index_behavior_analysis()
indexer.index_dwell_times()
indexer.index_queue_metrics()
indexer.index_alerts()

# Index everything
counts = indexer.index_all()
```

### QueryEngine

```python
from rag import QueryEngine

engine = QueryEngine(embedder, vector_store)

# Simple query
result = engine.query("What happened today?")

# With filters
result = engine.query(
    "Zone activity?",
    filters={"zone_id": 1}
)

# Conversational
result = engine.get_conversation_response(
    question="And what about their emotions?",
    conversation_history=[
        {"question": "Who was there?", "answer": "3 customers..."}
    ]
)

# Summary
summary = engine.summarize_insights(zone_id=1)
```

## Filters and Metadata

### Available Metadata Fields

**Gemini Reports:**
- `source`: "gemini_report"
- `filename`: Report filename
- `timestamp`: ISO format timestamp
- `chunk_index`: Chunk number

**Behavior Analysis:**
- `source`: "behavior_analysis"
- `person_id`: Person ID
- `analysis_type`: Type of analysis
- `timestamp`: ISO format timestamp

**Dwell Times:**
- `source`: "dwell_time"
- `person_id`: Person ID
- `zone_id`: Zone ID
- `zone_name`: Zone name
- `duration_seconds`: Duration
- `engagement_score`: Score (0-1)

**Queue Metrics:**
- `source`: "queue_metrics"
- `zone_id`: Zone ID
- `zone_name`: Zone name
- `queue_length`: Number in queue
- `avg_wait_time`: Average wait (seconds)

**Alerts:**
- `source`: "alert"
- `priority`: "low", "medium", "high", "critical"
- `category`: Alert category
- `status`: Alert status
- `zone_id`: Zone ID

### Filter Examples

```python
# By source type
filters = {"source": "dwell_time"}

# By zone
filters = {"zone_id": 1}

# By person
filters = {"person_id": 5}

# Multiple filters
filters = {"source": "alert", "priority": "high"}
```

## Integration with Main App

To add RAG endpoints to your main FastAPI app:

```python
from rag.rag_api import create_rag_router
from fastapi import FastAPI

app = FastAPI()

# Add RAG router
rag_router = create_rag_router()
app.include_router(rag_router)
```

## Performance Tips

1. **Batch Indexing** - Index in batches to avoid API rate limits
2. **Chunk Size** - Default 1000 tokens works well for most documents
3. **n_results** - Retrieve 3-5 documents for focused answers, 10+ for comprehensive analysis
4. **Filters** - Use metadata filters to narrow searches and improve speed
5. **Persistent Storage** - ChromaDB persists to disk, no need to re-index on restart

## Troubleshooting

### No documents found
- Ensure you've run indexing: `POST /rag/index`
- Check stats: `GET /rag/stats`
- Verify data exists in database and reports directory

### Slow queries
- Reduce `n_results` parameter
- Use metadata filters to narrow search
- Check ChromaDB persist directory isn't on slow storage

### Embedding errors
- Verify `GEMINI_API_KEY` is set in environment
- Check API quota and rate limits
- Ensure text isn't too long (max ~30,000 characters)

### Import errors
- Install dependencies: `pip install chromadb google-generativeai`
- Ensure PYTHONPATH includes project root

## Advanced Features

### Custom Prompts

```python
# Modify the query engine's prompt
result = engine.generate_answer(
    query="Your question",
    context_documents=docs,
    context_metadatas=metas
)
```

### Re-indexing Strategy

```python
# Clear and rebuild
store.reset()
indexer.index_all()

# Add new data incrementally
indexer.index_gemini_reports(reports_directory="./new_reports")
```

### Conversation Memory

```python
history = []
questions = ["Who was in the store?", "What were they doing?", "Any purchase intent?"]

for question in questions:
    result = engine.get_conversation_response(
        question=question,
        conversation_history=history
    )
    history.append({
        "question": question,
        "answer": result['answer']
    })
```

## API Documentation

Full API documentation available at: `http://localhost:8001/docs` when server is running.

## License

Part of the Video AI Analytics System
