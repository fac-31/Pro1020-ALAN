from typing import List, Dict, Optional
import numpy as np
import gc
from nltk import sent_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import tiktoken # Import tiktoken

from .base_chunker import BaseChunker

class SemanticChunker(BaseChunker):
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        model_size: str = "small",
        max_chunk_tokens: int = 500,
        similarity_threshold: float = 0.75, # Fixed threshold
        threshold_type: str = "fixed", # New: "fixed" or "percentile"
        threshold_percentile: float = 75.0, # New: for percentile thresholding
        overlap: int = 1,
        unload_model_after_use: bool = False,
        embedding_batch_size: int = 32
    ):
        # Store model name but don't load yet
        self.embedding_model_name = self._select_model(embedding_model_name, model_size)
        self.model = None  # Will be loaded lazily
        self.max_chunk_tokens = max_chunk_tokens
        self.fixed_similarity_threshold = similarity_threshold # Renamed
        self.threshold_type = threshold_type
        self.threshold_percentile = threshold_percentile
        self.overlap = overlap
        self.unload_model_after_use = unload_model_after_use
        self.embedding_batch_size = embedding_batch_size
        self.tokenizer = tiktoken.get_encoding("cl100k_base") # Initialize tiktoken

    def _select_model(self, model_name: str, model_size: str) -> str:
        """Select appropriate model based on size preference"""
        if model_size == "small":
            # Use smaller variants or default to smallest
            if "L6" not in model_name and "L12" not in model_name:
                return model_name
            # Prefer L6 models for small size
            return model_name.replace("L12", "L6") if "L12" in model_name else model_name
        elif model_size == "medium":
            # Use medium-sized models
            return model_name.replace("L6", "L12") if "L6" in model_name else model_name
        else:  # large
            # Use original or larger models
            return model_name

    def _get_model(self):
        """Lazy load the SentenceTransformer model"""
        if self.model is None:
            self.model = SentenceTransformer(self.embedding_model_name)
        return self.model

    def unload_model(self):
        """Unload the model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
            gc.collect()

    def _calculate_token_length(self, text: str) -> int:
        """Calculate token length using tiktoken."""
        return len(self.tokenizer.encode(text))

    def chunk(
        self, 
        text: str, 
        metadata: Optional[Dict] = None,
        pretokenized: bool = False
    ) -> List[Dict]:
        if metadata is None:
            metadata = {}

        sentences = text if pretokenized else sent_tokenize(text)
        if not sentences: # Handle empty input
            return []

        try:
            # Load model only when needed
            model = self._get_model()
            
            # Process embeddings in batches to reduce memory usage
            sentence_embeddings = []
            for i in range(0, len(sentences), self.embedding_batch_size):
                batch = sentences[i:i + self.embedding_batch_size]
                batch_embeddings = model.encode(batch, convert_to_numpy=True)
                sentence_embeddings.append(batch_embeddings)
            
            # Concatenate batches
            if sentence_embeddings:
                sentence_embeddings = np.vstack(sentence_embeddings).astype(np.float32)
            else:
                return []

            # Calculate dynamic threshold if type is percentile
            current_similarity_threshold = self.fixed_similarity_threshold
            if self.threshold_type == "percentile" and len(sentences) > 1:
                # Calculate all pairwise similarities between consecutive sentences
                consecutive_similarities = []
                for i in range(len(sentence_embeddings) - 1):
                    # Use float16 for similarity calculations to save memory
                    emb1 = sentence_embeddings[i:i+1].astype(np.float32)
                    emb2 = sentence_embeddings[i+1:i+2].astype(np.float32)
                    sim = cosine_similarity(emb1, emb2)[0][0]
                    consecutive_similarities.append(sim)
                
                # Set threshold as the Nth percentile of these similarities
                current_similarity_threshold = np.percentile(consecutive_similarities, self.threshold_percentile)
                # Clear intermediate arrays
                del consecutive_similarities

            chunks = []
            current_chunk_sentences = []
            current_chunk_embs = []

            for i, (sent, emb) in enumerate(zip(sentences, sentence_embeddings)):
                if not current_chunk_sentences:
                    current_chunk_sentences.append(sent)
                    current_chunk_embs.append(emb)
                    continue

                # Calculate similarity with the last sentence in the current chunk
                # Use float32 for final similarity calculations (FAISS compatibility)
                emb_array = emb.reshape(1, -1).astype(np.float32)
                last_emb_array = current_chunk_embs[-1].reshape(1, -1).astype(np.float32)
                sim = cosine_similarity(emb_array, last_emb_array)[0][0]
                
                # Calculate current chunk length using tiktoken
                current_chunk_text = " ".join(current_chunk_sentences)
                current_length = self._calculate_token_length(current_chunk_text)

                # Decide if a new chunk should start
                if sim < current_similarity_threshold or current_length >= self.max_chunk_tokens:
                    chunks.append({"text": current_chunk_text, "metadata": metadata.copy()})

                if current_length >= self.max_chunk_tokens:
                    # Apply overlap only for size-based splits
                    current_chunk_sentences = current_chunk_sentences[-self.overlap:] if self.overlap > 0 else []
                    current_chunk_embs = current_chunk_embs[-self.overlap:] if self.overlap > 0 else []
                else:
                    # No overlap for semantic splits
                    current_chunk_sentences = []
                    current_chunk_embs = []

                current_chunk_sentences.append(sent)
                current_chunk_embs.append(emb)

            # Add the last chunk if it's not empty
            if current_chunk_sentences:
                chunks.append({"text": " ".join(current_chunk_sentences), "metadata": metadata.copy()})

            # Clear intermediate arrays
            del sentence_embeddings
            del current_chunk_embs
            
            # Unload model if configured
            if self.unload_model_after_use:
                self.unload_model()
            
            # Force garbage collection if unload was requested
            if self.unload_model_after_use:
                gc.collect()

            return chunks
            
        except Exception as e:
            # Ensure model is unloaded on error if configured
            if self.unload_model_after_use and self.model is not None:
                self.unload_model()
            raise