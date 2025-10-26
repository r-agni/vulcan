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
from app.core.database import (
    BehaviorAnalysis, PersonTrajectory, DwellTimeRecord,
    Zone, LineCrossingEvent, OccupancyLog, QueueMetrics,
    ProductInteraction, AlertLog
)
import sqlite3


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

    def index_merged_logs(
        self,
        db_path: str = "./merged_logs.db",
        metadata_collection: str = "metadata_collection",
        analysis_collection: str = "analysis_collection",
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Index merged_logs.db data into separate collections for metadata and analysis

        Args:
            db_path: Path to merged_logs.db
            metadata_collection: Name for metadata vector collection
            analysis_collection: Name for analysis vector collection
            limit: Maximum number of records to index (None = all)

        Returns:
            Dictionary with counts for each collection
        """
        print("\n" + "="*60)
        print(f"Indexing merged_logs from {db_path}...")
        print("="*60 + "\n")

        # Create collections
        self.vector_store.get_or_create_collection(
            metadata_collection,
            "Structured metadata from camera_room table"
        )
        self.vector_store.get_or_create_collection(
            analysis_collection,
            "Gemini verbal analysis from camera_room table"
        )

        # Connect to merged_logs.db
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query camera_room table
        query = "SELECT * FROM camera_room ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        records = cursor.fetchall()

        if not records:
            print("No records found in merged_logs.db")
            conn.close()
            return {"metadata": 0, "analysis": 0}

        metadata_docs = []
        metadata_embeddings = []
        metadata_metadatas = []
        metadata_ids = []

        analysis_docs = []
        analysis_embeddings = []
        analysis_metadatas = []
        analysis_ids = []

        for idx, record in enumerate(records):
            try:
                record_dict = dict(record)
                record_id = record_dict.get('id', idx)
                timestamp = record_dict.get('timestamp', '')

                # 1. Index METADATA (all columns except gemini_analysis_text)
                metadata_fields = {
                    'id': record_dict.get('id'),
                    'timestamp': timestamp,
                    'camera_name': record_dict.get('camera_name'),
                    'room_name': record_dict.get('room_name'),
                    'occupancy': record_dict.get('occupancy'),
                    'peak_today': record_dict.get('peak_today'),
                    'avg_dwell_time': record_dict.get('avg_dwell_time'),
                    'active_trajectories': record_dict.get('active_trajectories'),
                    'total_entries': record_dict.get('total_entries'),
                    'detection_count': record_dict.get('detection_count'),
                    'face_detection_count': record_dict.get('face_detection_count'),
                    'session_count': record_dict.get('session_count'),
                    'line_crossings_in': record_dict.get('line_crossings_in'),
                    'line_crossings_out': record_dict.get('line_crossings_out'),
                    'max_dwell_time_current': record_dict.get('max_dwell_time_current'),
                    'queue_count': record_dict.get('queue_count'),
                    'max_queue_length': record_dict.get('max_queue_length'),
                    'interaction_count': record_dict.get('interaction_count'),
                    'gaze_fixation_count': record_dict.get('gaze_fixation_count'),
                    'crowd_density': record_dict.get('crowd_density'),
                    'energy_level': record_dict.get('energy_level'),
                    'event_count': record_dict.get('event_count'),
                    'alert_count': record_dict.get('alert_count')
                }

                # Create searchable text from metadata
                metadata_text = f"""
Timestamp: {timestamp}
Camera: {record_dict.get('camera_name')} in {record_dict.get('room_name')}
Occupancy: {record_dict.get('occupancy')} (Peak today: {record_dict.get('peak_today')})
Average Dwell Time: {record_dict.get('avg_dwell_time')} seconds
Active Trajectories: {record_dict.get('active_trajectories')}
Total Entries: {record_dict.get('total_entries')}
Detections: {record_dict.get('detection_count')} total, {record_dict.get('face_detection_count')} faces
Sessions: {record_dict.get('session_count')}
Line Crossings: {record_dict.get('line_crossings_in')} in, {record_dict.get('line_crossings_out')} out
Queue: {record_dict.get('queue_count')} queues, max length {record_dict.get('max_queue_length')}
Interactions: {record_dict.get('interaction_count')}
Gaze Fixations: {record_dict.get('gaze_fixation_count')}
Crowd Density: {record_dict.get('crowd_density')}
Energy Level: {record_dict.get('energy_level')}
Events: {record_dict.get('event_count')}
Alerts: {record_dict.get('alert_count')}
"""

                # Parse JSON fields for additional context
                try:
                    zones = json.loads(record_dict.get('zones', '[]') or '[]')
                    if zones:
                        zone_names = [z.get('name', '') for z in zones if isinstance(z, dict)]
                        metadata_text += f"\nZones: {', '.join(zone_names)}"
                        metadata_fields['zones'] = zone_names
                except:
                    pass

                try:
                    zone_occupancy = json.loads(record_dict.get('zone_occupancy', '{}') or '{}')
                    if zone_occupancy:
                        metadata_text += f"\nZone Occupancy: {zone_occupancy}"
                except:
                    pass

                # Generate embedding for metadata
                metadata_embedding = self.embedder.embed_text(metadata_text)

                metadata_docs.append(metadata_text)
                metadata_embeddings.append(metadata_embedding)
                metadata_metadatas.append({
                    "source": "merged_logs_metadata",
                    "record_id": record_id,
                    "timestamp": timestamp,
                    **{k: v for k, v in metadata_fields.items() if v is not None}
                })
                metadata_ids.append(f"metadata_{record_id}")

                # 2. Index ANALYSIS (gemini_analysis_text only)
                gemini_analysis = record_dict.get('gemini_analysis_text')
                if gemini_analysis and gemini_analysis.strip():
                    analysis_text = f"""
Timestamp: {timestamp}
Camera: {record_dict.get('camera_name')} in {record_dict.get('room_name')}

Gemini Analysis:
{gemini_analysis}
"""

                    analysis_embedding = self.embedder.embed_text(analysis_text)

                    analysis_docs.append(analysis_text)
                    analysis_embeddings.append(analysis_embedding)
                    analysis_metadatas.append({
                        "source": "merged_logs_analysis",
                        "record_id": record_id,
                        "timestamp": timestamp,
                        "camera_name": record_dict.get('camera_name'),
                        "room_name": record_dict.get('room_name')
                    })
                    analysis_ids.append(f"analysis_{record_id}")

                if (idx + 1) % 10 == 0:
                    print(f"Processed {idx + 1}/{len(records)} records...")

            except Exception as e:
                print(f"Error indexing record {record_id}: {e}")
                continue

        # Add to vector store
        if metadata_docs:
            self.vector_store.add_documents_to_collection(
                metadata_collection,
                metadata_docs,
                metadata_embeddings,
                metadata_metadatas,
                metadata_ids
            )

        if analysis_docs:
            self.vector_store.add_documents_to_collection(
                analysis_collection,
                analysis_docs,
                analysis_embeddings,
                analysis_metadatas,
                analysis_ids
            )

        conn.close()

        print("\n" + "="*60)
        print("Merged logs indexing complete!")
        print(f"  Metadata documents: {len(metadata_docs)}")
        print(f"  Analysis documents: {len(analysis_docs)}")
        print("="*60 + "\n")

        return {
            "metadata": len(metadata_docs),
            "analysis": len(analysis_docs)
        }

    def index_single_snapshot(
        self,
        snapshot_id: int,
        db_path: str = "./merged_logs.db",
        metadata_collection: str = "metadata_collection",
        analysis_collection: str = "analysis_collection"
    ) -> Dict[str, int]:
        """
        Index a single snapshot from merged_logs.db (for incremental updates)

        Args:
            snapshot_id: ID of the camera_room record to index
            db_path: Path to merged_logs.db
            metadata_collection: Name for metadata vector collection
            analysis_collection: Name for analysis vector collection

        Returns:
            Dictionary with counts for each collection
        """
        # Create collections if they don't exist
        self.vector_store.get_or_create_collection(
            metadata_collection,
            "Structured metadata from camera_room table"
        )
        self.vector_store.get_or_create_collection(
            analysis_collection,
            "Gemini verbal analysis from camera_room table"
        )

        # Connect to merged_logs.db
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query specific snapshot
        cursor.execute("SELECT * FROM camera_room WHERE id = ?", (snapshot_id,))
        record = cursor.fetchone()

        if not record:
            conn.close()
            return {"metadata": 0, "analysis": 0}

        metadata_count = 0
        analysis_count = 0

        try:
            record_dict = dict(record)
            record_id = record_dict.get('id')
            timestamp = record_dict.get('timestamp', '')

            # 1. Index METADATA
            metadata_fields = {
                'id': record_dict.get('id'),
                'timestamp': timestamp,
                'camera_name': record_dict.get('camera_name'),
                'room_name': record_dict.get('room_name'),
                'occupancy': record_dict.get('occupancy'),
                'peak_today': record_dict.get('peak_today'),
                'avg_dwell_time': record_dict.get('avg_dwell_time'),
                'active_trajectories': record_dict.get('active_trajectories'),
                'total_entries': record_dict.get('total_entries'),
                'detection_count': record_dict.get('detection_count'),
                'face_detection_count': record_dict.get('face_detection_count'),
                'session_count': record_dict.get('session_count'),
                'line_crossings_in': record_dict.get('line_crossings_in'),
                'line_crossings_out': record_dict.get('line_crossings_out'),
                'queue_count': record_dict.get('queue_count'),
                'interaction_count': record_dict.get('interaction_count'),
                'gaze_fixation_count': record_dict.get('gaze_fixation_count'),
                'crowd_density': record_dict.get('crowd_density'),
                'energy_level': record_dict.get('energy_level'),
                'event_count': record_dict.get('event_count'),
                'alert_count': record_dict.get('alert_count')
            }

            metadata_text = f"""
Timestamp: {timestamp}
Camera: {record_dict.get('camera_name')} in {record_dict.get('room_name')}
Occupancy: {record_dict.get('occupancy')} (Peak: {record_dict.get('peak_today')})
Avg Dwell Time: {record_dict.get('avg_dwell_time')}s
Trajectories: {record_dict.get('active_trajectories')}
Entries: {record_dict.get('total_entries')}
Detections: {record_dict.get('detection_count')}
Line Crossings: {record_dict.get('line_crossings_in')} in / {record_dict.get('line_crossings_out')} out
Queue Count: {record_dict.get('queue_count')}
Interactions: {record_dict.get('interaction_count')}
Alerts: {record_dict.get('alert_count')}
"""

            metadata_embedding = self.embedder.embed_text(metadata_text)

            self.vector_store.add_documents_to_collection(
                metadata_collection,
                [metadata_text],
                [metadata_embedding],
                [{
                    "source": "merged_logs_metadata",
                    "record_id": record_id,
                    "timestamp": timestamp,
                    **{k: v for k, v in metadata_fields.items() if v is not None}
                }],
                [f"metadata_{record_id}"]
            )
            metadata_count = 1

            # 2. Index ANALYSIS if present
            gemini_analysis = record_dict.get('gemini_analysis_text')
            if gemini_analysis and gemini_analysis.strip():
                analysis_text = f"""
Timestamp: {timestamp}
Camera: {record_dict.get('camera_name')}

Gemini AI Analysis:
{gemini_analysis}
"""

                analysis_embedding = self.embedder.embed_text(analysis_text)

                self.vector_store.add_documents_to_collection(
                    analysis_collection,
                    [analysis_text],
                    [analysis_embedding],
                    [{
                        "source": "merged_logs_analysis",
                        "record_id": record_id,
                        "timestamp": timestamp,
                        "camera_name": record_dict.get('camera_name'),
                        "room_name": record_dict.get('room_name')
                    }],
                    [f"analysis_{record_id}"]
                )
                analysis_count = 1

        except Exception as e:
            print(f"Error indexing snapshot {snapshot_id}: {e}")

        conn.close()

        return {
            "metadata": metadata_count,
            "analysis": analysis_count
        }

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
