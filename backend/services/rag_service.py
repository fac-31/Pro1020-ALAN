"""
RAG Service - Enhanced RAG engine with better error handling and configuration
"""

import logging
import os
import gc
from typing import List, Dict, Optional, Any
import faiss
import numpy as np
import json
import pickle
from datetime import datetime
from openai import OpenAI

from core.config import settings
from core.exceptions import RAGServiceError, create_rag_search_error

logger = logging.getLogger(__name__)


class RAGService:
    """Enhanced RAG service with better error handling and configuration management"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Initialize the RAG service with FAISS
        
        Args:
            persist_directory: Directory to persist FAISS data (defaults to settings)
        """
        try:
            self.persist_directory = persist_directory or settings.rag_persist_directory
            self.openai_api_key = settings.openai_api_key
            
            if not self.openai_api_key:
                raise RAGServiceError(
                    message="OpenAI API key not configured",
                    error_code="OPENAI_API_KEY_MISSING"
                )
            
            # Initialize OpenAI client for embeddings
            self.client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize FAISS index (1536 dimensions for text-embedding-3-small)
            self.dimension = 1536
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine similarity)
            
            # Store document metadata
            self.documents = []
            self.metadata = []
            
            # Load existing data if available
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
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI with enhanced error handling"""
        try:
            response = self.client.embeddings.create(
                model=settings.rag_embedding_model,
                input=text
            )
            vec = np.array(response.data[0].embedding, dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / (norm if norm > 0 else 1.0)
        except Exception as e:
            logger.error(f"Failed to get embedding for text: {e}")
            raise RAGServiceError(
                message=f"Failed to generate embedding: {str(e)}",
                error_code="EMBEDDING_GENERATION_FAILED",
                details={"text_length": len(text)}
            )
    
    def _load_data(self):
        """Load existing FAISS index and metadata with memory optimization"""
        try:
            index_path = f"{self.persist_directory}/faiss_index.bin"
            metadata_path = f"{self.persist_directory}/metadata.json"
            
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                # Check file size before loading (memory optimization)
                index_size = os.path.getsize(index_path)
                max_recommended_size = settings.rag_max_index_size * self.dimension * 4  # 4 bytes per float32
                
                if index_size > max_recommended_size * 2:  # Allow some overhead
                    logger.warning(f"Index file size ({index_size / 1024 / 1024:.2f}MB) is large. Consider reducing index size.")
                
                # Load FAISS index
                # Note: FAISS doesn't support direct memory mapping via read_index,
                # but we can optimize by checking index size before loading
                self.index = faiss.read_index(index_path)
                
                # Verify index size doesn't exceed limit
                if self.index.ntotal > settings.rag_max_index_size:
                    logger.warning(f"Loaded index has {self.index.ntotal} vectors, exceeding limit of {settings.rag_max_index_size}")
                
                # Load metadata
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', [])
                    self.metadata = data.get('metadata', [])
                
                # Ensure metadata matches index size
                if len(self.documents) != self.index.ntotal:
                    logger.warning(f"Document count ({len(self.documents)}) doesn't match index size ({self.index.ntotal})")
                    # Truncate to match index
                    self.documents = self.documents[:self.index.ntotal]
                    self.metadata = self.metadata[:self.index.ntotal]
                
                logger.info(f"Loaded {len(self.documents)} documents from {self.persist_directory}")
            else:
                logger.info("No existing data found, starting with empty index")
                
        except Exception as e:
            logger.warning(f"Failed to load existing data: {e}")
            # Continue with empty index
            self.documents = []
            self.metadata = []
    
    def _save_data(self):
        """Save FAISS index and metadata"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Save FAISS index
            index_path = f"{self.persist_directory}/faiss_index.bin"
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            metadata_path = f"{self.persist_directory}/metadata.json"
            data = {
                'documents': self.documents,
                'metadata': self.metadata,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.documents)} documents to {self.persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise RAGServiceError(
                message=f"Failed to save RAG data: {str(e)}",
                error_code="RAG_SAVE_FAILED"
            )
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add multiple documents to the knowledge base with batch processing"""
        try:
            if not documents:
                logger.warning("No documents provided to add")
                return False
            
            # Check if we've reached the maximum index size
            current_size = self.index.ntotal
            max_size = settings.rag_max_index_size
            if current_size >= max_size:
                logger.warning(f"FAISS index has reached maximum size ({max_size}). Cannot add more documents.")
                return False
            
            # Calculate how many documents we can add
            remaining_slots = max_size - current_size
            documents_to_process = documents[:remaining_slots]
            
            if len(documents) > remaining_slots:
                logger.warning(f"Only processing {remaining_slots} of {len(documents)} documents due to index size limit")
            
            batch_size = settings.rag_batch_size
            total_added = 0
            
            # Process documents in batches
            for batch_start in range(0, len(documents_to_process), batch_size):
                batch = documents_to_process[batch_start:batch_start + batch_size]
                batch_embeddings = []
                batch_docs = []
                batch_metadata = []
                
                for doc in batch:
                    content = doc.get('content', '')
                    if not content.strip():
                        logger.warning("Skipping document with empty content")
                        continue
                    
                    # Get embedding
                    embedding = self._get_embedding(content)
                    batch_embeddings.append(embedding)
                    
                    # Store document and metadata
                    batch_docs.append(content)
                    batch_metadata.append({
                        'title': doc.get('title', ''),
                        'topics': doc.get('topics', []),
                        'source': doc.get('source', 'manual'),
                        'url': doc.get('url'),
                        'added_at': datetime.now().isoformat()
                    })
                
                if not batch_embeddings:
                    continue
                
                # Add batch to FAISS index
                batch_embeddings_array = np.vstack(batch_embeddings).astype(np.float32)
                self.index.add(batch_embeddings_array)
                
                # Update document storage
                self.documents.extend(batch_docs)
                self.metadata.extend(batch_metadata)
                
                total_added += len(batch_docs)
                
                # Clear batch embeddings to free memory
                del batch_embeddings
                del batch_embeddings_array
                
                # Force garbage collection between batches for memory efficiency
                if settings.low_memory_mode:
                    gc.collect()
            
            if total_added == 0:
                logger.warning("No valid documents to add")
                return False
            
            # Save data
            self._save_data()
            
            logger.info(f"Successfully added {total_added} documents to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise RAGServiceError(
                message=f"Failed to add documents: {str(e)}",
                error_code="ADD_DOCUMENTS_FAILED",
                details={"document_count": len(documents)}
            )
    
    def search_documents(self, query: str, n_results: int = None) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        try:
            if not query.strip():
                raise RAGServiceError(
                    message="Search query cannot be empty",
                    error_code="EMPTY_SEARCH_QUERY"
                )
            
            n_results = n_results or settings.rag_max_results
            
            if len(self.documents) == 0:
                logger.info("No documents in knowledge base")
                return []
            
            # Get query embedding
            query_embedding = self._get_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Search FAISS index
            scores, indices = self.index.search(query_embedding, min(n_results, len(self.documents)))
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.documents):
                    results.append({
                        'content': self.documents[idx],
                        'score': float(score),
                        'metadata': self.metadata[idx] if idx < len(self.metadata) else {}
                    })
            
            logger.info(f"Found {len(results)} relevant documents for query: {query[:50]}...")
            return results
            
        except RAGServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            raise create_rag_search_error(f"Document search failed: {str(e)}")
    
    def get_context_for_query(
        self,
        query: str,
        user_interests: List[str] = None,
        n_results: int = None
    ) -> str:
        """Get context for a query"""
        try:
            results = self.search_documents(query, n_results=n_results)
            
            if not results:
                return "No relevant information found in the knowledge base."
            
            # Filter by user interests if provided
            if user_interests:
                filtered_results = []
                for result in results:
                    result_topics = result['metadata'].get('topics', [])
                    if any(interest.lower() in [topic.lower() for topic in result_topics] for interest in user_interests):
                        filtered_results.append(result)
                
                if filtered_results:
                    results = filtered_results
            
            # Combine top results
            context_parts = []
            for i, result in enumerate(results[:3]):  # Top 3 results
                content = result['content'][:500]  # Limit content length
                context_parts.append(f"Context {i+1}: {content}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get context for query: {e}")
            return "Error retrieving context from knowledge base."
    
    def add_news_article(
        self,
        title: str,
        content: str,
        topics: List[str],
        url: str,
        source: str = "news"
    ) -> bool:
        """Add a news article to the knowledge base, splitting into chunks first"""
        try:
            # Chunk the full article text into smaller pieces
            from chunk_modules.hybrid_chunker import HybridChunker

            full_text = f"{title}\n\n{content}"
            # honor global setting for semantic merging to avoid import errors
            chunker = HybridChunker(use_semantic_merger=settings.use_semantic_merger)
            chunks = chunker.chunk_document(
                full_text,
                metadata={
                    'title': title,
                    'topics': topics,
                    'source': source,
                    'url': url
                }
            )
            # Prepare docs for FAISS: each chunk is one document entry
            documents = [
                {'content': chunk['text'], **chunk['metadata']}
                for chunk in chunks
            ]
            return self.add_documents(documents)
        except Exception as e:
            logger.error(f"Failed to add news article: {e}")
            raise RAGServiceError(
                message=f"Failed to add news article: {str(e)}",
                error_code="ADD_NEWS_ARTICLE_FAILED",
                details={"title": title, "source": source}
            )
    
    def add_user_document(self, content: str, title: str = "", topics: List[str] = None) -> bool:
        """Add a user document to the knowledge base"""
        try:
            document = {
                'content': content,
                'title': title or "User Document",
                'topics': topics or [],
                'source': 'user'
            }
            
            return self.add_documents([document])
            
        except Exception as e:
            logger.error(f"Failed to add user document: {e}")
            raise RAGServiceError(
                message=f"Failed to add user document: {str(e)}",
                error_code="ADD_USER_DOCUMENT_FAILED",
                details={"title": title}
            )
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            topics = set()
            for meta in self.metadata:
                topics.update(meta.get('topics', []))
            
            return {
                'total_documents': len(self.documents),
                'unique_topics': len(topics),
                'topics': list(topics),
                'last_updated': self.metadata[-1].get('added_at') if self.metadata else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base stats: {e}")
            return {
                'total_documents': 0,
                'unique_topics': 0,
                'topics': [],
                'last_updated': None,
                'error': str(e)
            }
    
    def clear_knowledge_base(self) -> bool:
        """Clear all documents from the knowledge base"""
        try:
            # Reset FAISS index
            self.index = faiss.IndexFlatIP(self.dimension)
            
            # Clear document storage
            self.documents = []
            self.metadata = []
            
            # Save empty state
            self._save_data()
            
            logger.info("Knowledge base cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            raise RAGServiceError(
                message=f"Failed to clear knowledge base: {str(e)}",
                error_code="CLEAR_KNOWLEDGE_BASE_FAILED"
            )
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get RAG service status"""
        try:
            stats = self.get_knowledge_base_stats()
            return {
                "status": "healthy",
                "total_documents": stats['total_documents'],
                "unique_topics": stats['unique_topics'],
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
