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

    def setUp(self):
        # This text has 3 sentences. The first two are similar, the third is different.
        self.test_text = "The cat sat on the mat. The feline was resting comfortably. The dog barked loudly."

    @patch("chunk_modules.semantic_merger.SentenceTransformer")
    def test_fixed_threshold_chunking(self, mock_sentence_transformer):
        """Test chunking with a fixed similarity threshold"""
        # Mock the sentence transformer model
        mock_model = MagicMock()
        mock_model.encode.return_value = [
            [0.1, 0.2, 0.9],  # "The cat sat on the mat."
            [0.1, 0.2, 0.8],  # "The feline was resting comfortably." (similar)
            [0.8, 0.2, 0.1],  # "The dog barked loudly." (dissimilar)
        ]
        mock_sentence_transformer.return_value = mock_model

        # Initialize chunker with a fixed threshold
        chunker = SemanticChunker(
            threshold_type="fixed",
            similarity_threshold=0.85,  # High threshold to split dissimilar sentences
        )

        chunks = chunker.chunk(self.test_text)

        # Expecting two chunks:
        # 1. "The cat sat on the mat. The feline was resting comfortably."
        # 2. "The dog barked loudly."
        self.assertEqual(len(chunks), 2)
        self.assertIn("The cat sat on the mat.", chunks[0]["text"])
        self.assertIn("The feline was resting comfortably.", chunks[0]["text"])
        self.assertEqual(chunks[1]["text"], "The dog barked loudly.")

    @patch("chunk_modules.semantic_merger.SentenceTransformer")
    def test_percentile_threshold_chunking(self, mock_sentence_transformer):
        """Test chunking with a percentile-based similarity threshold"""
        # Mock the sentence transformer model
        mock_model = MagicMock()
        mock_model.encode.return_value = [
            [0.1, 0.2, 0.9],  # Sentence 1
            [0.1, 0.2, 0.8],  # Sentence 2 (Similarity to 1 is high)
            [0.5, 0.5, 0.5],  # Sentence 3 (Similarity to 2 is medium)
            [0.8, 0.2, 0.1],  # Sentence 4 (Similarity to 3 is low)
        ]
        mock_sentence_transformer.return_value = mock_model

        # Initialize chunker with percentile threshold
        chunker = SemanticChunker(
            threshold_type="percentile",
            threshold_percentile=50,  # Use the median similarity as the threshold
        )

        # The similarities between consecutive sentences will be calculated.
        # Let's assume they are: sim(1,2) = 0.9, sim(2,3) = 0.6, sim(3,4) = 0.3
        # The 50th percentile (median) is 0.6. So, any similarity below 0.6 will cause a split.

        text = "Sentence 1. Sentence 2. Sentence 3. Sentence 4."
        chunks = chunker.chunk(text)

        # Expecting two chunks based on the median similarity threshold:
        # 1. "Sentence 1. Sentence 2. Sentence 3." (since sim(2,3) is 0.6, which is not less than the threshold)
        # 2. "Sentence 4." (since sim(3,4) is 0.3, which is less than the threshold)
        self.assertEqual(len(chunks), 2)


class TestHybridChunker(unittest.TestCase):
    """Test Hybrid Chunker functionality"""

    def setUp(self):
        self.long_text = "This is a long text for testing the hybrid chunker. " * 200
        self.metadata = {"source": "test_document.txt"}

    @patch("chunk_modules.hybrid_chunker.RecursiveSplitter")
    @patch("chunk_modules.hybrid_chunker.NormaliseSentence")
    @patch("chunk_modules.hybrid_chunker.SemanticChunker")
    def test_chunk_document(
        self, mock_semantic_chunker, mock_normalise_sentence, mock_recursive_splitter
    ):
        """Test the full document chunking pipeline of the HybridChunker"""
        # Mock the output of each stage in the pipeline
        mock_recursive_splitter.return_value.split.return_value = [
            "coarse chunk 1",
            "coarse chunk 2",
        ]
        mock_normalise_sentence.return_value.normalize.return_value = [
            "normalized chunk 1",
            "normalized chunk 2",
        ]

        # Mock the semantic chunker to return specific chunks with metadata
        mock_semantic_chunker.return_value.chunk.side_effect = [
            [
                {"text": "semantic chunk 1a", "metadata": {}},
                {"text": "semantic chunk 1b", "metadata": {}},
            ],
            [{"text": "semantic chunk 2a", "metadata": {}}],
        ]

        # Initialize the HybridChunker
        chunker = HybridChunker()

        final_chunks = chunker.chunk_document(self.long_text, metadata=self.metadata)

        # Verify the final output
        self.assertEqual(len(final_chunks), 3)

        # Check metadata propagation and enrichment
        self.assertEqual(final_chunks[0]["metadata"]["source"], "test_document.txt")
        self.assertEqual(final_chunks[0]["metadata"]["coarse_index"], 0)
        self.assertEqual(final_chunks[0]["metadata"]["semantic_index"], 0)

        self.assertEqual(final_chunks[1]["metadata"]["source"], "test_document.txt")
        self.assertEqual(final_chunks[1]["metadata"]["coarse_index"], 0)
        self.assertEqual(final_chunks[1]["metadata"]["semantic_index"], 1)

        self.assertEqual(final_chunks[2]["metadata"]["source"], "test_document.txt")
        self.assertEqual(final_chunks[2]["metadata"]["coarse_index"], 1)
        self.assertEqual(final_chunks[2]["metadata"]["semantic_index"], 0)


if __name__ == "__main__":
    unittest.main()
