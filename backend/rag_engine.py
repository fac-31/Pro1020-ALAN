import os
import logging
from typing import List, Dict, Optional, Any
import faiss
import numpy as np
import json
import pickle
from datetime import datetime
from openai import OpenAI
from core.config import settings
from chunk_modules.hybrid_chunker import HybridChunker # Import HybridChunker

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, persist_directory: str = "./faiss_db"):
        """
        Initialize the RAG engine with FAISS
        
        Args:
            persist_directory: Directory to persist FAISS data
        """
        self.persist_directory = persist_directory
        self.openai_api_key = settings.openai_api_key
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
        
        # Initialize OpenAI client for embeddings
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Initialize FAISS index (1536 dimensions for text-embedding-3-small)
        self.dimension = 1536
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine similarity)
        
        # Store document metadata
        self.documents = []
        self.metadata = []
        
        # Initialize HybridChunker with configurable parameters
        self.chunker = HybridChunker(
            recursive_chunk_size=settings.chunking_recursive_chunk_size,
            recursive_overlap=settings.chunking_recursive_overlap,
            sentence_overlap=settings.chunking_sentence_overlap,
            semantic_embedding_model_name=settings.chunking_semantic_embedding_model_name,
            semantic_max_chunk_tokens=settings.chunking_semantic_max_chunk_tokens,
            semantic_similarity_threshold=settings.chunking_semantic_similarity_threshold,
            semantic_threshold_type=settings.chunking_semantic_threshold_type,
            semantic_threshold_percentile=settings.chunking_semantic_threshold_percentile,
            semantic_overlap=settings.chunking_semantic_overlap
        )
        
        # Load existing data if available
        self._load_data()
        
        logger.info(f"RAG Engine initialized with FAISS at {persist_directory}")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def _load_data(self):
        """Load existing FAISS index and metadata"""
        try:
            index_path = os.path.join(self.persist_directory, "faiss_index.bin")
            metadata_path = os.path.join(self.persist_directory, "metadata.json")
            
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                # Load FAISS index
                self.index = faiss.read_index(index_path)
                
                # Load metadata
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', [])
                    self.metadata = data.get('metadata', [])
                
                logger.info(f"Loaded existing data: {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def _save_data(self):
        """Save FAISS index and metadata"""
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Save FAISS index
            index_path = os.path.join(self.persist_directory, "faiss_index.bin")
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            metadata_path = os.path.join(self.persist_directory, "metadata.json")
            data = {
                'documents': self.documents,
                'metadata': self.metadata
            }
            with open(metadata_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved data: {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Add documents to the knowledge base after chunking them.
        
        Args:
            documents: List of documents with 'content', 'metadata', and 'id' fields.
                       The 'content' will be chunked.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            all_chunk_embeddings = []
            all_chunk_contents = []
            all_chunk_metadata = []
            
            for doc in documents:
                original_doc_id = doc.get('id', f"doc_{hash(doc['content']) % 10000}")
                original_metadata = doc.get('metadata', {})
                
                # Chunk the document content
                processed_chunks = self.chunker.chunk_document(
                    text=doc['content'],
                    metadata=original_metadata
                )
                
                for i, chunk in enumerate(processed_chunks):
                    chunk_content = chunk['text']
                    chunk_metadata = chunk['metadata']
                    
                    # Generate a unique ID for each chunk
                    chunk_id = f"{original_doc_id}_chunk_{i}"
                    
                    # Get embedding for chunk content
                    embedding = self._get_embedding(chunk_content)
                    all_chunk_embeddings.append(embedding)
                    
                    # Store chunk content and metadata
                    all_chunk_contents.append(chunk_content)
                    all_chunk_metadata.append({
                        **chunk_metadata,
                        'original_doc_id': original_doc_id,
                        'chunk_id': chunk_id,
                        'added_at': datetime.now().isoformat()
                    })
            
            if not all_chunk_embeddings:
                logger.info("No chunks generated from provided documents.")
                return True

            # Convert to numpy array and normalize for cosine similarity
            embeddings_array = np.array(all_chunk_embeddings)
            faiss.normalize_L2(embeddings_array)
            
            # Add to FAISS index
            self.index.add(embeddings_array)
            
            # Update local storage
            self.documents.extend(all_chunk_contents)
            self.metadata.extend(all_chunk_metadata)
            
            # Save to disk
            self._save_data()
            
            logger.info(f"Added {len(all_chunk_contents)} chunks from {len(documents)} documents to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def search_documents(self, query: str, n_results: int = 5, 
                        filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Search for relevant documents using semantic similarity
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters (not implemented in this simple version)
            
        Returns:
            List of relevant document chunks with metadata
        """
        try:
            if len(self.documents) == 0:
                return []
            
            # Get embedding for query
            query_embedding = self._get_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            scores, indices = self.index.search(query_embedding, min(n_results, len(self.documents)))
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.documents):
                    results.append({
                        'content': self.documents[idx],
                        'metadata': self.metadata[idx],
                        'distance': float(score),
                        'id': f"doc_{idx}"
                    })
            
            logger.info(f"Found {len(results)} relevant documents for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def get_context_for_query(self, query: str, user_interests: List[str] = None, 
                            n_results: int = 5) -> str:
        """
        Get relevant context for a query, optionally filtered by user interests
        
        Args:
            query: User's query
            user_interests: Optional list of user interests to filter by
            n_results: Number of results to include
            
        Returns:
            Formatted context string for LLM
        """
        try:
            # Search for relevant documents
            results = self.search_documents(query, n_results)
            
            if not results:
                return "No relevant information found in the knowledge base."
            
            # Format context
            context_parts = []
            for i, result in enumerate(results, 1):
                content = result['content']
                metadata = result['metadata']
                
                # Add source information if available
                source_info = ""
                if 'title' in metadata:
                    source_info = f" (Source: {metadata['title']})"
                elif 'filename' in metadata:
                    source_info = f" (Source: {metadata['filename']})"
                
                context_parts.append(f"{i}. {content}{source_info}")
            
            context = "\n\n".join(context_parts)
            
            logger.info(f"Generated context with {len(results)} relevant chunks")
            return context
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return "Error retrieving context from knowledge base."
    
    def add_news_article(self, title: str, content: str, url: str = "", 
                        topics: List[str] = None) -> bool:
        """
        Add a news article to the knowledge base
        
        Args:
            title: Article title
            content: Article content
            url: Article URL
            topics: List of topics/categories
            
        Returns:
            True if successful, False otherwise
        """
        try:
            article_id = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title) % 10000}"
            
            document = {
                'id': article_id,
                'content': f"Title: {title}\n\n{content}",
                'metadata': {
                    'type': 'news_article',
                    'title': title,
                    'url': url,
                    'topics': topics or [],
                    'added_at': datetime.now().isoformat()
                }
            }
            
            return self.add_documents([document])
            
        except Exception as e:
            logger.error(f"Error adding news article: {e}")
            return False
    
    def add_user_document(self, content: str, filename: str, user_email: str, 
                         topics: List[str] = None) -> bool:
        """
        Add a user-uploaded document to the knowledge base
        
        Args:
            content: Document content
            filename: Original filename
            user_email: User who uploaded the document
            topics: List of topics/categories
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_id = f"user_doc_{hash(filename + user_email) % 10000}"
            
            document = {
                'id': doc_id,
                'content': content,
                'metadata': {
                    'type': 'user_document',
                    'filename': filename,
                    'user_email': user_email,
                    'topics': topics or [],
                    'added_at': datetime.now().isoformat()
                }
            }
            
            return self.add_documents([document])
            
        except Exception as e:
            logger.error(f"Error adding user document: {e}")
            return False
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base
        
        Returns:
            Dictionary with knowledge base statistics
        """
        try:
            topics = set()
            doc_types = set()
            
            for metadata in self.metadata:
                if 'topics' in metadata:
                    topics.update(metadata['topics'])
                if 'type' in metadata:
                    doc_types.add(metadata['type'])
            
            return {
                'total_documents': len(self.documents),
                'unique_topics': list(topics),
                'document_types': list(doc_types),
                'index_size': self.index.ntotal
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {e}")
            return {'error': str(e)}
    
    def clear_knowledge_base(self) -> bool:
        """
        Clear all documents from the knowledge base
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Recreate FAISS index
            self.index = faiss.IndexFlatIP(self.dimension)
            
            # Clear local storage
            self.documents = []
            self.metadata = []
            
            # Save empty state
            self._save_data()
            
            logger.info("Knowledge base cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {e}")
            return False
