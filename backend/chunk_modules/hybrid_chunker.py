from typing import List, Dict, Optional
from .recursive_splitter import RecursiveSplitter
from .normalise_sentence import NormaliseSentence
from .semantic_merger import SemanticChunker # Updated import

class HybridChunker:
    def __init__(
        self,
        recursive_chunk_size: int = 1000,
        recursive_overlap: int = 200,
        sentence_overlap: int = 1,
        semantic_embedding_model_name: str = "all-MiniLM-L6-v2",
        semantic_model_size: str = "small",
        semantic_max_chunk_tokens: int = 500,
        semantic_similarity_threshold: float = 0.75,
        semantic_threshold_type: str = "fixed",
        semantic_threshold_percentile: float = 75.0,
        semantic_overlap: int = 1,
        semantic_unload_model_after_use: bool = False,
        semantic_embedding_batch_size: int = 32
    ):
        self.recursive = RecursiveSplitter(chunk_size=recursive_chunk_size, overlap=recursive_overlap)
        self.normalizer = NormaliseSentence(sentence_overlap=sentence_overlap)
        self.semantic = SemanticChunker(
            embedding_model_name=semantic_embedding_model_name,
            model_size=semantic_model_size,
            max_chunk_tokens=semantic_max_chunk_tokens,
            similarity_threshold=semantic_similarity_threshold,
            threshold_type=semantic_threshold_type,
            threshold_percentile=semantic_threshold_percentile,
            overlap=semantic_overlap,
            unload_model_after_use=semantic_unload_model_after_use,
            embedding_batch_size=semantic_embedding_batch_size
        )

    def chunk_document(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        if metadata is None:
            metadata = {}

        final_chunks = []
        coarse_chunks = self.recursive.split(text)
        normalized_chunks = self.normalizer.normalize(coarse_chunks)

        for i, chunk_text in enumerate(normalized_chunks):
            # Pass original metadata and coarse index to semantic chunker
            sem_chunks_with_metadata = self.semantic.chunk(text=chunk_text, metadata=metadata.copy())
            for j, sem_chunk_dict in enumerate(sem_chunks_with_metadata):
                # sem_chunk_dict already contains 'text' and 'metadata'
                # Update metadata with coarse and semantic indices
                sem_chunk_dict['metadata'].update({
                    "coarse_index": i,
                    "semantic_index": j
                })
                final_chunks.append(sem_chunk_dict)

        return final_chunks