"""
Unit tests for chunker modules
Tests HybridChunker and SemanticChunker
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chunk_modules.hybrid_chunker import HybridChunker
from chunk_modules.semantic_merger import SemanticChunker


class TestSemanticChunker(unittest.TestCase):
    """Test Semantic Chunker functionality"""

    @classmethod
    def setUpClass(cls):
        """Ensure NLTK tokenizers are available for sent_tokenize() calls."""
        import nltk
        for resource in ("punkt", "punkt_tab"):
            try:
                nltk.data.find(f"tokenizers/{resource}")
            except LookupError:
                nltk.download(resource, quiet=True)

    def setUp(self):
        self.test_text = "The cat sat on the mat. The feline was resting comfortably. The dog barked loudly."

    @patch('chunk_modules.semantic_merger.cosine_similarity')
    @patch('chunk_modules.semantic_merger.SentenceTransformer')
    def test_fixed_threshold_chunking(self, mock_sentence_transformer, mock_cosine):
        """Test chunking with a fixed similarity threshold"""
        # Mock embeddings
        mock_model = MagicMock()
        mock_model.encode.return_value = [
            [0.1, 0.2, 0.9],
            [0.1, 0.2, 0.8],
            [0.8, 0.2, 0.1]
        ]
        mock_sentence_transformer.return_value = mock_model

        # Mock cosine similarity
        mock_cosine.side_effect = [
            [[0.99]],  # sim(sentence 0, 1)
            [[0.50]]   # sim(sentence 1, 2)
        ]

        chunker = SemanticChunker(
            threshold_type="fixed",
            similarity_threshold=0.85
        )

        chunks = chunker.chunk(self.test_text)

        self.assertEqual(len(chunks), 2)
        self.assertIn("The cat sat on the mat.", chunks[0]['text'])
        self.assertIn("The feline was resting comfortably.", chunks[0]['text'])
        self.assertEqual(chunks[1]['text'], "The dog barked loudly.")

    @patch('chunk_modules.semantic_merger.np.percentile')
    @patch('chunk_modules.semantic_merger.cosine_similarity')
    @patch('chunk_modules.semantic_merger.SentenceTransformer')
    def test_percentile_threshold_chunking(self, mock_sentence_transformer, mock_cosine, mock_percentile):
        """Test chunking with a percentile-based similarity threshold"""
        # Mock embeddings
        mock_model = MagicMock()
        mock_model.encode.return_value = [
            [0.1, 0.2, 0.9],
            [0.1, 0.2, 0.8],
            [0.5, 0.5, 0.5],
            [0.8, 0.2, 0.1]
        ]
        mock_sentence_transformer.return_value = mock_model

        # Mock cosine similarity
        mock_cosine.side_effect = [
            [[0.9]],  # sim(0,1)
            [[0.6]],  # sim(1,2)
            [[0.3]]   # sim(2,3)
        ]

        # Mock np.percentile
        mock_percentile.return_value = 0.6

        chunker = SemanticChunker(
            threshold_type="percentile",
            threshold_percentile=50
        )

        text = "Sentence 1. Sentence 2. Sentence 3. Sentence 4."
        chunks = chunker.chunk(text)

        self.assertEqual(len(chunks), 2)


class TestHybridChunker(unittest.TestCase):
    """Test Hybrid Chunker functionality"""

    def setUp(self):
        self.long_text = "This is a long text for testing the hybrid chunker. " * 200
        self.metadata = {"source": "test_document.txt"}

    @patch('chunk_modules.hybrid_chunker.RecursiveSplitter')
    @patch('chunk_modules.hybrid_chunker.NormaliseSentence')
    @patch('chunk_modules.hybrid_chunker.SemanticChunker')
    def test_chunk_document(self, mock_semantic_chunker, mock_normalise_sentence, mock_recursive_splitter):
        """Test the full document chunking pipeline of the HybridChunker"""
        # Mock coarse chunks
        mock_recursive_splitter.return_value.split.return_value = ["coarse chunk 1", "coarse chunk 2"]
        # Mock normalized chunks
        mock_normalise_sentence.return_value.normalize.return_value = ["normalized chunk 1", "normalized chunk 2"]

        # Mock SemanticChunker to dynamically copy incoming metadata
        def semantic_chunk_side_effect(text, metadata):
            if "normalized chunk 1" in text:
                return [
                    {"text": "semantic chunk 1a", "metadata": metadata.copy()},
                    {"text": "semantic chunk 1b", "metadata": metadata.copy()}
                ]
            else:
                return [
                    {"text": "semantic chunk 2a", "metadata": metadata.copy()}
                ]

        mock_semantic_chunker.return_value.chunk.side_effect = semantic_chunk_side_effect

        chunker = HybridChunker()
        final_chunks = chunker.chunk_document(self.long_text, metadata=self.metadata)

        self.assertEqual(len(final_chunks), 3)

        # Check metadata propagation
        self.assertEqual(final_chunks[0]['metadata']['source'], "test_document.txt")
        self.assertEqual(final_chunks[0]['metadata']['coarse_index'], 0)
        self.assertEqual(final_chunks[0]['metadata']['semantic_index'], 0)

        self.assertEqual(final_chunks[1]['metadata']['source'], "test_document.txt")
        self.assertEqual(final_chunks[1]['metadata']['coarse_index'], 0)
        self.assertEqual(final_chunks[1]['metadata']['semantic_index'], 1)

        self.assertEqual(final_chunks[2]['metadata']['source'], "test_document.txt")
        self.assertEqual(final_chunks[2]['metadata']['coarse_index'], 1)
        self.assertEqual(final_chunks[2]['metadata']['semantic_index'], 0)


if __name__ == '__main__':
    unittest.main()
