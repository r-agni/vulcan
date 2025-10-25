"""
Document indexer for Gemini reports and analytics data
"""

import os
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import (
    BehaviorAnalysis, PersonTrajectory, DwellTimeRecord, 
    Zone, LineCrossingEvent, OccupancyLog, QueueMetrics,
    ProductInteraction, AlertLog
)


class DocumentIndexer:
    """Index documents from Gemini reports and analytics database"""

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_store: VectorStore,
        db_session: Session
    ):
        """
        Initialize document indexer
        
        Args:
            embedding_generator: Instance of EmbeddingGenerator
            vector_store: Instance of VectorStore
            db_session: SQLAlchemy database session
        """
        self.embedder = embedding_generator
        self.vector_store = vector_store
        self.db = db_session

    def chunk_text(self, text: str, max_tokens: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk (approximate using words)
            overlap: Number of words to overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Simple word-based chunking (approximate tokens)
        words = text.split()
        chunks = []
        
        # Approximate 1 token = 0.75 words
        max_words = int(max_tokens * 0.75)
        overlap_words = int(overlap * 0.75)
        
        for i in range(0, len(words), max_words - overlap_words):
            chunk = ' '.join(words[i:i + max_words])
            if chunk:
                chunks.append(chunk)
        
        return chunks if chunks else [text]

    def index_gemini_reports(self, reports_directory: str = "./data/analysis_results/reports") -> int:
        """
        Index all Gemini analysis reports from text files
        
        Args:
            reports_directory: Directory containing report text files
            
        Returns:
            Number of documents indexed
        """
        print(f"Indexing Gemini reports from {reports_directory}...")
        
        # Find all .txt files
        report_files = glob.glob(os.path.join(reports_directory, "gemini_analysis_*.txt"))
        
        if not report_files:
            print("No Gemini report files found")
            return 0
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for file_path in report_files:
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract timestamp from filename (e.g., gemini_analysis_20251019_004446.txt)
                filename = os.path.basename(file_path)
                timestamp_str = filename.replace("gemini_analysis_", "").replace(".txt", "")
                
                # Parse timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                except:
                    timestamp = datetime.utcnow()
                
                # Chunk large documents
                chunks = self.chunk_text(content)
                
                for idx, chunk in enumerate(chunks):
                    doc_id = f"gemini_report_{timestamp_str}_chunk_{idx}"
                    
                    # Generate embedding
                    embedding = self.embedder.embed_text(chunk)
                    
                    documents.append(chunk)
                    embeddings.append(embedding)
                    metadatas.append({
                        "source": "gemini_report",
                        "file_path": file_path,
                        "filename": filename,
                        "timestamp": timestamp.isoformat(),
                        "chunk_index": idx,
                        "total_chunks": len(chunks)
                    })
                    ids.append(doc_id)
                
                print(f"Indexed {filename} ({len(chunks)} chunks)")
                
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")
                continue
        
        # Add to vector store
        if documents:
            self.vector_store.add_documents(documents, embeddings, metadatas, ids)
        
        return len(documents)

    def index_behavior_analysis(self, limit: Optional[int] = None) -> int:
        """
        Index behavior analysis records from database
        
        Args:
            limit: Maximum number of records to index (None = all)
            
        Returns:
            Number of documents indexed
        """
        print("Indexing behavior analysis from database...")
        
        query = self.db.query(BehaviorAnalysis)
        if limit:
            query = query.limit(limit)
        
        records = query.all()
        
        if not records:
            print("No behavior analysis records found")
            return 0
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for record in records:
            try:
                # Create searchable text
                text = f"""
                Behavior Analysis - {record.analysis_type}
                Person ID: {record.person_id}
                Timestamp: {record.timestamp}
                
                Analysis:
                {record.analysis_text}
                """
                
                # Generate embedding
                embedding = self.embedder.embed_text(text)
                
                documents.append(text)
                embeddings.append(embedding)
                metadatas.append({
                    "source": "behavior_analysis",
                    "analysis_id": record.id,
                    "person_id": record.person_id or 0,
                    "analysis_type": record.analysis_type,
                    "timestamp": record.timestamp.isoformat(),
                    "detection_event_id": record.detection_event_id
                })
                ids.append(f"behavior_{record.id}")
                
            except Exception as e:
                print(f"Error indexing behavior analysis {record.id}: {e}")
                continue
        
        if documents:
            self.vector_store.add_documents(documents, embeddings, metadatas, ids)
        
        print(f"Indexed {len(documents)} behavior analysis records")
        return len(documents)

    def index_dwell_times(self, limit: Optional[int] = None) -> int:
        """
        Index dwell time records with zone information
        
        Args:
            limit: Maximum number of records to index
            
        Returns:
            Number of documents indexed
        """
        print("Indexing dwell time records...")
        
        query = self.db.query(DwellTimeRecord).join(Zone, DwellTimeRecord.zone_id == Zone.id)
        if limit:
            query = query.limit(limit)
        
        records = query.all()
        
        if not records:
            print("No dwell time records found")
            return 0
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for record in records:
            try:
                zone = self.db.query(Zone).filter(Zone.id == record.zone_id).first()
                zone_name = zone.name if zone else "Unknown"
                
                text = f"""
                Dwell Time Record
                Person ID: {record.person_id}
                Zone: {zone_name} (ID: {record.zone_id})
                Entry: {record.entry_time}
                Exit: {record.exit_time}
                Duration: {record.duration_seconds} seconds ({record.duration_seconds / 60:.1f} minutes)
                Engagement Score: {record.engagement_score or 'N/A'}
                
                Summary: Customer spent {record.duration_seconds} seconds in {zone_name}.
                """
                
                embedding = self.embedder.embed_text(text)
                
                documents.append(text)
                embeddings.append(embedding)
                metadatas.append({
                    "source": "dwell_time",
                    "record_id": record.id,
                    "person_id": record.person_id,
                    "zone_id": record.zone_id,
                    "zone_name": zone_name,
                    "duration_seconds": record.duration_seconds,
                    "entry_time": record.entry_time.isoformat(),
                    "exit_time": record.exit_time.isoformat() if record.exit_time else None,
                    "engagement_score": record.engagement_score
                })
                ids.append(f"dwell_{record.id}")
                
            except Exception as e:
                print(f"Error indexing dwell time {record.id}: {e}")
                continue
        
        if documents:
            self.vector_store.add_documents(documents, embeddings, metadatas, ids)
        
        print(f"Indexed {len(documents)} dwell time records")
        return len(documents)

    def index_queue_metrics(self, limit: Optional[int] = None) -> int:
        """
        Index queue metrics from database
        
        Args:
            limit: Maximum number of records to index
            
        Returns:
            Number of documents indexed
        """
        print("Indexing queue metrics...")
        
        query = self.db.query(QueueMetrics)
        if limit:
            query = query.limit(limit)
        
        records = query.all()
        
        if not records:
            print("No queue metrics found")
            return 0
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for record in records:
            try:
                zone = self.db.query(Zone).filter(Zone.id == record.zone_id).first()
                zone_name = zone.name if zone else "Unknown"
                
                text = f"""
                Queue Metrics
                Zone: {zone_name} (ID: {record.zone_id})
                Timestamp: {record.timestamp}
                Queue Length: {record.queue_length} people
                Average Wait Time: {record.avg_wait_time_seconds or 'N/A'} seconds
                Max Wait Time: {record.max_wait_time_seconds or 'N/A'} seconds
                
                Summary: Queue at {zone_name} had {record.queue_length} people.
                """
                
                embedding = self.embedder.embed_text(text)
                
                documents.append(text)
                embeddings.append(embedding)
                metadatas.append({
                    "source": "queue_metrics",
                    "record_id": record.id,
                    "zone_id": record.zone_id,
                    "zone_name": zone_name,
                    "queue_length": record.queue_length,
                    "timestamp": record.timestamp.isoformat(),
                    "avg_wait_time": record.avg_wait_time_seconds,
                    "max_wait_time": record.max_wait_time_seconds
                })
                ids.append(f"queue_{record.id}")
                
            except Exception as e:
                print(f"Error indexing queue metrics {record.id}: {e}")
                continue
        
        if documents:
            self.vector_store.add_documents(documents, embeddings, metadatas, ids)
        
        print(f"Indexed {len(documents)} queue metrics records")
        return len(documents)

    def index_alerts(self, limit: Optional[int] = None) -> int:
        """
        Index alert logs from database
        
        Args:
            limit: Maximum number of records to index
            
        Returns:
            Number of documents indexed
        """
        print("Indexing alert logs...")
        
        try:
            query = self.db.query(AlertLog)
            if limit:
                query = query.limit(limit)
            
            records = query.all()
            
            if not records:
                print("No alert logs found")
                return 0
        except Exception as e:
            print(f"Alert logs table not found or error querying: {e}")
            print("Skipping alert indexing")
            return 0
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for record in records:
            try:
                text = f"""
                Alert: {record.title}
                Priority: {record.priority}
                Category: {record.category}
                Status: {record.status}
                Timestamp: {record.timestamp}
                Zone: {record.zone_name or 'N/A'}
                
                Message: {record.message}
                """
                
                embedding = self.embedder.embed_text(text)
                
                documents.append(text)
                embeddings.append(embedding)
                metadatas.append({
                    "source": "alert",
                    "alert_id": record.alert_id,
                    "title": record.title,
                    "priority": record.priority,
                    "category": record.category,
                    "status": record.status,
                    "timestamp": record.timestamp.isoformat(),
                    "zone_id": record.zone_id,
                    "zone_name": record.zone_name,
                    "person_id": record.person_id
                })
                ids.append(f"alert_{record.id}")
                
            except Exception as e:
                print(f"Error indexing alert {record.id}: {e}")
                continue
        
        if documents:
            self.vector_store.add_documents(documents, embeddings, metadatas, ids)
        
        print(f"Indexed {len(documents)} alert records")
        return len(documents)

    def index_all(self, reports_directory: str = "./data/analysis_results/reports") -> Dict[str, int]:
        """
        Index all data sources
        
        Args:
            reports_directory: Directory containing Gemini reports
            
        Returns:
            Dictionary with counts for each data source
        """
        print("\n" + "="*60)
        print("Starting comprehensive indexing...")
        print("="*60 + "\n")
        
        counts = {
            "gemini_reports": self.index_gemini_reports(reports_directory),
            "behavior_analysis": self.index_behavior_analysis(),
            "dwell_times": self.index_dwell_times(),
            "queue_metrics": self.index_queue_metrics(),
            "alerts": self.index_alerts()
        }
        
        total = sum(counts.values())
        
        print("\n" + "="*60)
        print(f"Indexing complete! Total documents: {total}")
        print("="*60)
        print(f"  Gemini Reports: {counts['gemini_reports']}")
        print(f"  Behavior Analysis: {counts['behavior_analysis']}")
        print(f"  Dwell Times: {counts['dwell_times']}")
        print(f"  Queue Metrics: {counts['queue_metrics']}")
        print(f"  Alerts: {counts['alerts']}")
        print("="*60 + "\n")
        
        return counts
