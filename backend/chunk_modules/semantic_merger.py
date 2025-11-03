from typing import List, Dict, Optional
import numpy as np
from nltk import sent_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import tiktoken # Import tiktoken

from .base_chunker import BaseChunker

class SemanticChunker(BaseChunker):
    def __init__(
        self,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        max_chunk_tokens: int = 500,
        similarity_threshold: float = 0.75, # Fixed threshold
        threshold_type: str = "fixed", # New: "fixed" or "percentile"
        threshold_percentile: float = 75.0, # New: for percentile thresholding
        overlap: int = 1
    ):
        self.model = SentenceTransformer(embedding_model_name)
        self.max_chunk_tokens = max_chunk_tokens
        self.fixed_similarity_threshold = similarity_threshold # Renamed
        self.threshold_type = threshold_type
        self.threshold_percentile = threshold_percentile
        self.overlap = overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base") # Initialize tiktoken

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

        sentence_embeddings = self.model.encode(sentences)

        # Calculate dynamic threshold if type is percentile
        current_similarity_threshold = self.fixed_similarity_threshold
        if self.threshold_type == "percentile" and len(sentences) > 1:
            # Calculate all pairwise similarities between consecutive sentences
            consecutive_similarities = []
            for i in range(len(sentence_embeddings) - 1):
                sim = cosine_similarity(sentence_embeddings[i].reshape(1, -1),
                                        sentence_embeddings[i+1].reshape(1, -1))[0][0]
                # sim = cosine_similarity([sentence_embeddings[i]], [sentence_embeddings[i+1]])[0][0]
                consecutive_similarities.append(sim)
            
            # Set threshold as the Nth percentile of these similarities
            current_similarity_threshold = np.percentile(consecutive_similarities, self.threshold_percentile)

        chunks = []
        current_chunk_sentences = []
        current_chunk_embs = []

        for i, (sent, emb) in enumerate(zip(sentences, sentence_embeddings)):
            if not current_chunk_sentences:
                current_chunk_sentences.append(sent)
                current_chunk_embs.append(emb)
                continue

            # Calculate similarity with the last sentence in the current chunk
            sim = cosine_similarity(emb.reshape(1, -1),
                                    current_chunk_embs[-1].reshape(1, -1))[0][0]

            # sim = cosine_similarity([emb], [current_chunk_embs[-1]])[0][0]
            
            # Calculate current chunk length using tiktoken
            current_chunk_text = " ".join(current_chunk_sentences)
            current_length = self._calculate_token_length(current_chunk_text)

            # Decide if a new chunk should start
            if sim < current_similarity_threshold or current_length >= self.max_chunk_tokens:
                chunks.append({"text": current_chunk_text, "metadata": metadata.copy()})
                
                # Apply overlap for the new chunk
                current_chunk_sentences = current_chunk_sentences[-self.overlap:] if self.overlap > 0 else []
                current_chunk_embs = current_chunk_embs[-self.overlap:] if self.overlap > 0 else []

            current_chunk_sentences.append(sent)
            current_chunk_embs.append(emb)

        # Add the last chunk if it's not empty
        if current_chunk_sentences:
            chunks.append({"text": " ".join(current_chunk_sentences), "metadata": metadata.copy()})

        return chunks