"""
RAG Service - Enhanced RAG engine with better error handling and configuration
Now supports article_id + chunk_id metadata grouping for correct digest behavior.
"""

import logging
import os
import gc
from typing import List, Dict, Optional, Any
import faiss
import numpy as np
import json
from datetime import datetime
from openai import OpenAI

from core.config import settings
from core.exceptions import RAGServiceError, create_rag_search_error

logger = logging.getLogger(__name__)


class RAGService:
    """Enhanced RAG service with better error handling and configuration management"""

    def __init__(self, persist_directory: Optional[str] = None):
        try:
            self.persist_directory = persist_directory or settings.rag_persist_directory
            self.openai_api_key = settings.openai_api_key

            if not self.openai_api_key:
                raise RAGServiceError(
                    message="OpenAI API key not configured",
                    error_code="OPENAI_API_KEY_MISSING"
                )

            self.client = OpenAI(api_key=self.openai_api_key)

            # 1536 dimensions for text-embedding-3-small
            self.dimension = 1536
            self.index = faiss.IndexFlatIP(self.dimension)

            # Storage
            self.documents: List[str] = []
            self.metadata: List[Dict[str, Any]] = []

            self._load_data()
            logger.info(f"RAG Service initialized with FAISS at {self.persist_directory}")

        except RAGServiceError:
            raise
        except Exception as e:
            raise RAGServiceError(
                message=f"Failed to initialize RAG service: {str(e)}",
                error_code="RAG_SERVICE_INIT_FAILED",
                details={"original_error": str(e)}
            )

    # -----------------------------
    # INTERNALS
    # -----------------------------
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding and normalize"""
        try:
            response = self.client.embeddings.create(
                model=settings.rag_embedding_model,
                input=text
            )
            vec = np.array(response.data[0].embedding, dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / (norm if norm > 0 else 1.0)
        except Exception as e:
            logger.error(f"Failed embedding: {e}")
            raise RAGServiceError(
                message="Failed to generate embedding",
                error_code="EMBEDDING_GENERATION_FAILED",
                details={"text_length": len(text)}
            )

    def _load_data(self):
        """Load index + metadata"""
        try:
            index_path = f"{self.persist_directory}/faiss_index.bin"
            metadata_path = f"{self.persist_directory}/metadata.json"

            if os.path.exists(index_path) and os.path.exists(metadata_path):
                self.index = faiss.read_index(index_path)

                with open(metadata_path, "r") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.metadata = data.get("metadata", [])

                # Sanity check
                if len(self.documents) != self.index.ntotal:
                    logger.warning("Metadata/docs count mismatch; truncating.")
                    min_len = min(len(self.documents), self.index.ntotal)
                    self.documents = self.documents[:min_len]
                    self.metadata = self.metadata[:min_len]

                logger.info(f"Loaded {len(self.documents)} documents.")
            else:
                logger.info("No existing data found, starting fresh.")

        except Exception as e:
            logger.error(f"Failed to load existing FAISS data: {e}")
            self.documents = []
            self.metadata = []

    def _save_data(self):
        """Persist index + metadata"""
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            faiss.write_index(self.index, f"{self.persist_directory}/faiss_index.bin")

            out = {
                "documents": self.documents,
                "metadata": self.metadata,
                "last_updated": datetime.now().isoformat(),
            }

            with open(f"{self.persist_directory}/metadata.json", "w") as f:
                json.dump(out, f, indent=2)

            logger.info("Saved RAG index + metadata")

        except Exception as e:
            logger.error(f"Failed to save RAG data: {e}")
            raise RAGServiceError(
                message="Failed to save index/metadata",
                error_code="RAG_SAVE_FAILED"
            )

    # -----------------------------
    # ADDING DOCUMENTS
    # -----------------------------
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Add chunk-level documents to FAISS. Expects documents with:
            - content
            - article_id
            - chunk_id
            - title
            - topics
            - source
            - url
        """
        try:
            if not documents:
                logger.warning("No documents to add")
                return False

            max_size = settings.rag_max_index_size
            if self.index.ntotal >= max_size:
                logger.warning("Index full")
                return False

            remaining_slots = max_size - self.index.ntotal
            documents = documents[:remaining_slots]

            batch_size = settings.rag_batch_size
            added = 0

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                embeddings = []
                batch_docs = []
                batch_meta = []

                for doc in batch:
                    content = doc.get("content", "")
                    if not content.strip():
                        continue

                    embedding = self._get_embedding(content)
                    embeddings.append(embedding)

                    batch_docs.append(content)

                    batch_meta.append({
                        "article_id": doc.get("article_id"),
                        "chunk_id": doc.get("chunk_id"),
                        "title": doc.get("title"),
                        "topics": doc.get("topics"),
                        "source": doc.get("source"),
                        "url": doc.get("url"),
                        "added_at": datetime.now().isoformat()
                    })

                if embeddings:
                    arr = np.vstack(embeddings).astype(np.float32)
                    self.index.add(arr)

                    self.documents.extend(batch_docs)
                    self.metadata.extend(batch_meta)
                    added += len(batch_docs)

                if settings.low_memory_mode:
                    gc.collect()

            if added > 0:
                self._save_data()

            return added > 0

        except Exception as e:
            logger.error(f"Add documents failed: {e}")
            raise RAGServiceError(
                message="Add documents failed",
                error_code="ADD_DOCUMENTS_FAILED",
                details={"error": str(e)}
            )

    # -----------------------------
    # SEARCH
    # -----------------------------
    def search_documents(self, query: str, n_results: int = None) -> List[Dict[str, Any]]:
        try:
            if not query.strip():
                raise RAGServiceError("Empty query", "EMPTY_SEARCH_QUERY")

            n_results = n_results or settings.rag_max_results

            if len(self.documents) == 0:
                return []

            query_emb = self._get_embedding(query).reshape(1, -1)
            scores, indices = self.index.search(query_emb, min(n_results, len(self.documents)))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    results.append({
                        "content": self.documents[idx],
                        "score": float(score),
                        "metadata": self.metadata[idx]
                    })

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise create_rag_search_error(f"Search failed: {str(e)}")

    # -----------------------------
    # CONTEXT RETRIEVAL
    # -----------------------------
    def get_context_for_query(
        self,
        query: str,
        user_interests: List[str] = None,
        n_results: int = None
    ) -> str:
        """
        Deterministic and stable context constructor for digest/summary engines.
        """
        try:
            results = self.search_documents(query, n_results)

            if not results:
                return "No relevant information found."

            # Optional filtering
            if user_interests:
                results = [
                    r for r in results
                    if any(topic.lower() in [t.lower() for t in r["metadata"].get("topics", [])]
                        for topic in user_interests)
                ] or results  # fall back to original results

            # Group by article_id
            grouped = {}
            for r in results:
                aid = r["metadata"].get("article_id")
                if not aid:
                    continue
                grouped.setdefault(aid, []).append(r)

            # Sort groups by max score of any chunk — deterministic and stable
            sorted_groups = sorted(
                grouped.items(),
                key=lambda pair: max(c["score"] for c in pair[1]),
                reverse=True
            )

            # Format final output with strict deterministic template
            context_blocks = []
            for article_id, chunks in sorted_groups[:3]:
                # Stable chunk ordering within article
                chunks.sort(key=lambda x: x["metadata"]["chunk_id"])

                combined = ""
                for c in chunks:
                    # respect boundaries — don’t split mid-sentence
                    section = c["content"]
                    if len(section) > 500:
                        # find sentence end
                        end = section.rfind(".", 0, 500)
                        section = section[:end + 1] if end != -1 else section[:500]
                    combined += section + "\n\n"

                # strict formatting
                meta = chunks[0]["metadata"]
                context_blocks.append(
                    f"=== Article ===\n"
                    f"Title: {meta.get('title')}\n"
                    f"Source: {meta.get('source')}\n"
                    f"URL: {meta.get('url')}\n"
                    f"Topics: {', '.join(meta.get('topics', []))}\n"
                    f"--- Content ---\n"
                    f"{combined.strip()}\n"
                )

            return "\n".join(context_blocks).strip()

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return "Error retrieving context."


    # -----------------------------
    # NEWS ARTICLE INGESTION
    # -----------------------------
    def add_news_article(self, title: str, content: str, topics: List[str], url: str, source: str = "news") -> bool:
        """
        Ingest a full article:
        - chunk into semantic chunks
        - assign shared article_id
        - assign chunk_id
        """
        try:
            from chunk_modules.hybrid_chunker import HybridChunker

            chunker = HybridChunker(use_semantic_merger=settings.use_semantic_merger)

            full_text = f"{title}\n\n{content}"
            chunks = chunker.chunk_document(
                full_text,
                metadata={"title": title, "topics": topics, "source": source, "url": url}
            )

            # Generate stable article_id
            article_id = str(abs(hash(title + url + ",".join(topics))))

            documents = []
            for idx, ch in enumerate(chunks):
                documents.append({
                    "content": ch["text"],
                    "title": title,
                    "topics": topics,
                    "source": source,
                    "url": url,
                    "article_id": article_id,
                    "chunk_id": idx,
                })

            return self.add_documents(documents)

        except Exception as e:
            logger.error(f"Add news article failed: {e}")
            raise RAGServiceError(
                message="Add news article failed",
                error_code="ADD_NEWS_ARTICLE_FAILED",
                details={"title": title}
            )

    # -----------------------------
    # USER DOCS
    # -----------------------------
    def add_user_document(self, content: str, title: str = "", topics: List[str] = None) -> bool:
        try:
            article_id = str(abs(hash(content + title)))

            doc = {
                "content": content,
                "title": title or "User Document",
                "topics": topics or [],
                "source": "user",
                "url": None,
                "article_id": article_id,
                "chunk_id": 0,
            }

            return self.add_documents([doc])

        except Exception as e:
            logger.error(f"Add user doc failed: {e}")
            raise RAGServiceError(
                message="Add user document failed",
                error_code="ADD_USER_DOCUMENT_FAILED"
            )

    # -----------------------------
    # STATS
    # -----------------------------
    def get_knowledge_base_stats(self):
        try:
            topics = set()
            for m in self.metadata:
                topics.update(m.get("topics", []))

            return {
                "total_documents": len(self.documents),
                "unique_topics": len(topics),
                "topics": list(topics),
                "last_updated": self.metadata[-1]["added_at"] if self.metadata else None
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {
                "error": str(e)
            }

    def clear_knowledge_base(self) -> bool:
        try:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.documents = []
            self.metadata = []
            self._save_data()
            return True
        except Exception as e:
            logger.error(f"Clear failed: {e}")
            raise RAGServiceError("Clear KB failed", "CLEAR_KNOWLEDGE_BASE_FAILED")

    def get_service_status(self):
        try:
            stats = self.get_knowledge_base_stats()
            return {
                "status": "healthy",
                "total_documents": stats.get("total_documents", 0),
                "unique_topics": stats.get("unique_topics", 0),
                "embedding_model": settings.rag_embedding_model,
                "persist_directory": self.persist_directory,
                "index_size": self.index.ntotal
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "embedding_model": settings.rag_embedding_model,
                "persist_directory": self.persist_directory
            }
