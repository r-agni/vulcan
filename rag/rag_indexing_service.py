"""
RAG Indexing Service
Handles automatic and scheduled indexing of merged logs into RAG vector store
"""

import threading
import time
import queue
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .embeddings import EmbeddingGenerator
from .vector_store import VectorStore
from .document_indexer import DocumentIndexer


class RAGIndexingService:
    """
    Background service for indexing merged logs into RAG vector store

    Features:
    - Incremental indexing of new snapshots
    - Periodic full re-indexing
    - Queue-based processing to avoid blocking
    """

    def __init__(
        self,
        embedder: EmbeddingGenerator,
        vector_store: VectorStore,
        db_session_factory,
        batch_size: int = 10,
        batch_interval: float = 30.0,
        full_reindex_interval: float = 3600.0  # 1 hour
    ):
        """
        Initialize RAG indexing service

        Args:
            embedder: Embedding generator instance
            vector_store: Vector store instance
            db_session_factory: Factory function to create DB sessions
            batch_size: Number of snapshots to batch before indexing
            batch_interval: Seconds to wait before indexing a batch
            full_reindex_interval: Seconds between full re-indexes (0 = never)
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.db_session_factory = db_session_factory
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.full_reindex_interval = full_reindex_interval

        self.snapshot_queue: queue.Queue = queue.Queue()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.reindex_thread: Optional[threading.Thread] = None

        self.stats = {
            "snapshots_indexed": 0,
            "batches_processed": 0,
            "full_reindexes": 0,
            "errors": 0,
            "last_indexed_id": None,
            "last_full_reindex": None
        }

    def start(self):
        """Start the indexing service"""
        if self.running:
            print("⚠️ RAG indexing service already running")
            return

        self.running = True

        # Start worker thread for incremental indexing
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="RAGIndexingWorker"
        )
        self.worker_thread.start()

        # Start periodic full re-indexing thread if enabled
        if self.full_reindex_interval > 0:
            self.reindex_thread = threading.Thread(
                target=self._reindex_loop,
                daemon=True,
                name="RAGReindexer"
            )
            self.reindex_thread.start()

        print(f"✓ RAG indexing service started (batch: {self.batch_size}, interval: {self.batch_interval}s)")

    def stop(self):
        """Stop the indexing service"""
        self.running = False
        print("✗ RAG indexing service stopped")

    def queue_snapshot(self, snapshot_id: int):
        """
        Queue a snapshot for indexing

        Args:
            snapshot_id: ID of the camera_room record to index
        """
        try:
            self.snapshot_queue.put(snapshot_id, block=False)
        except queue.Full:
            self.stats["errors"] += 1
            print(f"⚠️ RAG indexing queue full, dropping snapshot {snapshot_id}")

    def _worker_loop(self):
        """Worker loop that processes queued snapshots in batches"""
        batch = []
        last_batch_time = time.time()

        while self.running:
            try:
                # Try to get snapshot from queue (with timeout)
                try:
                    snapshot_id = self.snapshot_queue.get(timeout=1.0)
                    batch.append(snapshot_id)
                except queue.Empty:
                    pass

                current_time = time.time()
                time_since_batch = current_time - last_batch_time

                # Process batch if:
                # 1. Batch is full, OR
                # 2. Batch has items and interval elapsed
                should_process = (
                    len(batch) >= self.batch_size or
                    (len(batch) > 0 and time_since_batch >= self.batch_interval)
                )

                if should_process:
                    self._process_batch(batch)
                    batch = []
                    last_batch_time = current_time

            except Exception as e:
                print(f"❌ Error in RAG indexing worker: {e}")
                self.stats["errors"] += 1
                time.sleep(1)

    def _process_batch(self, snapshot_ids: list):
        """
        Process a batch of snapshot IDs

        Args:
            snapshot_ids: List of camera_room IDs to index
        """
        if not snapshot_ids:
            return

        try:
            db = self.db_session_factory()
            indexer = DocumentIndexer(self.embedder, self.vector_store, db)

            total_metadata = 0
            total_analysis = 0

            for snapshot_id in snapshot_ids:
                try:
                    counts = indexer.index_single_snapshot(snapshot_id)
                    total_metadata += counts.get("metadata", 0)
                    total_analysis += counts.get("analysis", 0)
                    self.stats["last_indexed_id"] = snapshot_id
                except Exception as e:
                    print(f"❌ Error indexing snapshot {snapshot_id}: {e}")
                    self.stats["errors"] += 1

            self.stats["snapshots_indexed"] += len(snapshot_ids)
            self.stats["batches_processed"] += 1

            if total_metadata > 0 or total_analysis > 0:
                print(f"✓ RAG indexed {len(snapshot_ids)} snapshots: {total_metadata} metadata, {total_analysis} analysis docs")

            db.close()

        except Exception as e:
            print(f"❌ Error processing RAG batch: {e}")
            self.stats["errors"] += 1

    def _reindex_loop(self):
        """Periodic full re-indexing loop"""
        while self.running:
            try:
                time.sleep(self.full_reindex_interval)

                if not self.running:
                    break

                print(f"🔄 Starting periodic RAG full re-index...")
                self._full_reindex()

            except Exception as e:
                print(f"❌ Error in RAG reindex loop: {e}")
                self.stats["errors"] += 1
                time.sleep(60)  # Wait a minute before retrying

    def _full_reindex(self):
        """Perform a full re-index of recent data"""
        try:
            db = self.db_session_factory()
            indexer = DocumentIndexer(self.embedder, self.vector_store, db)

            # Index last 1000 records (configurable)
            counts = indexer.index_merged_logs(limit=1000)

            self.stats["full_reindexes"] += 1
            self.stats["last_full_reindex"] = datetime.now().isoformat()

            print(f"✓ RAG full re-index complete: {counts}")

            db.close()

        except Exception as e:
            print(f"❌ Error in RAG full reindex: {e}")
            self.stats["errors"] += 1

    def get_stats(self) -> dict:
        """Get indexing service statistics"""
        return {
            **self.stats,
            "running": self.running,
            "queue_size": self.snapshot_queue.qsize()
        }

    def trigger_full_reindex(self):
        """Manually trigger a full re-index (non-blocking)"""
        if not self.running:
            print("⚠️ RAG indexing service not running")
            return

        thread = threading.Thread(
            target=self._full_reindex,
            daemon=True,
            name="RAGManualReindex"
        )
        thread.start()
        print("🔄 Manual RAG re-index triggered")


# Global service instance
_rag_indexing_service: Optional[RAGIndexingService] = None


def get_rag_indexing_service() -> Optional[RAGIndexingService]:
    """Get the global RAG indexing service instance"""
    return _rag_indexing_service


def initialize_rag_indexing_service(
    embedder: EmbeddingGenerator,
    vector_store: VectorStore,
    db_session_factory,
    batch_size: int = 10,
    batch_interval: float = 30.0,
    full_reindex_interval: float = 3600.0
) -> RAGIndexingService:
    """
    Initialize and start the global RAG indexing service

    Args:
        embedder: Embedding generator instance
        vector_store: Vector store instance
        db_session_factory: Factory function to create DB sessions
        batch_size: Number of snapshots to batch before indexing
        batch_interval: Seconds to wait before indexing a batch
        full_reindex_interval: Seconds between full re-indexes (0 = never)

    Returns:
        RAGIndexingService instance
    """
    global _rag_indexing_service

    if _rag_indexing_service is not None:
        print("⚠️ RAG indexing service already initialized")
        return _rag_indexing_service

    _rag_indexing_service = RAGIndexingService(
        embedder,
        vector_store,
        db_session_factory,
        batch_size,
        batch_interval,
        full_reindex_interval
    )

    _rag_indexing_service.start()

    return _rag_indexing_service
