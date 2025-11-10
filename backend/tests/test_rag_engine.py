"""
Unit tests for RAG engine
Tests document storage, search, and retrieval functionality
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag_service import RAGService


class TestRAGEngine(unittest.TestCase):
    """Test RAG engine functionality"""

    def setUp(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()

        # Mock OpenAI API key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Mock OpenAI client
            with patch("services.rag_service.OpenAI") as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client

                # Mock embedding function
                mock_client.embeddings.create.return_value = Mock(
                    data=[Mock(embedding=[0.1] * 1536)]
                )

                self.rag_engine = RAGService(persist_directory=self.temp_dir)

    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_rag_engine_initialization(self):
        """Test RAG engine initialization"""
        self.assertIsNotNone(self.rag_engine.index)
        self.assertEqual(self.rag_engine.dimension, 1536)
        self.assertEqual(len(self.rag_engine.documents), 0)
        self.assertEqual(len(self.rag_engine.metadata), 0)

    @patch("services.rag_service.OpenAI")
    def test_add_documents(self, mock_openai):
        """Test adding documents to RAG engine"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        documents = [
            {
                "content": "This is a test document about AI.",
                "title": "Doc1",
                "topics": ["ai"],
            },
            {
                "content": "Another document about machine learning.",
                "title": "Doc2",
                "topics": ["ml"],
            },
        ]

        success = self.rag_engine.add_documents(documents)

        self.assertTrue(success)
        self.assertEqual(len(self.rag_engine.documents), 2)
        self.assertEqual(len(self.rag_engine.metadata), 2)

    @patch("services.rag_service.OpenAI")
    def test_search_documents(self, mock_openai):
        """Test searching documents in RAG engine"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        # Add test documents
        documents = [
            {
                "content": "This is a test document about AI.",
                "title": "A",
                "topics": ["ai"],
            },
            {
                "content": "Another document about machine learning.",
                "title": "B",
                "topics": ["ml"],
            },
            {
                "content": "A third document about natural language processing.",
                "title": "C",
                "topics": ["nlp"],
            },
        ]

        self.rag_engine.add_documents(documents)

        # Search for documents
        results = self.rag_engine.search_documents("AI research", n_results=2)

        self.assertIsNotNone(results)
        self.assertLessEqual(len(results), 2)

    @patch("services.rag_service.OpenAI")
    def test_add_news_article(self, mock_openai):
        """Test adding news articles"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        success = self.rag_engine.add_news_article(
            title="AI Breakthrough",
            content="Scientists have made a breakthrough in AI research.",
            topics=["ai", "research", "breakthrough"],
        )

        self.assertTrue(success)
        self.assertEqual(len(self.rag_engine.documents), 1)
        self.assertEqual(len(self.rag_engine.metadata), 1)

        # Check metadata
        metadata = self.rag_engine.metadata[0]
        self.assertEqual(metadata["type"], "news_article")
        self.assertEqual(metadata["title"], "AI Breakthrough")
        self.assertEqual(metadata["topics"], ["ai", "research", "breakthrough"])

    @patch("services.rag_service.OpenAI")
    def test_add_user_document(self, mock_openai):
        """Test adding user documents"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        success = self.rag_engine.add_user_document(
            content="This is a user document about technology.",
            title="User Tech Doc",
            topics=["technology", "user"],
        )

        self.assertTrue(success)
        self.assertEqual(len(self.rag_engine.documents), 1)
        self.assertEqual(len(self.rag_engine.metadata), 1)

        # Check metadata
        metadata = self.rag_engine.metadata[0]
        self.assertEqual(metadata["type"], "user_document")
        self.assertEqual(metadata["title"], "User Tech Doc")
        self.assertEqual(metadata["topics"], ["technology", "user"])

    @patch("services.rag_service.OpenAI")
    def test_get_context_for_query(self, mock_openai):
        """Test getting context for a query"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        # Add test documents
        self.rag_engine.add_documents(
            [
                {
                    "content": "AI is transforming industries.",
                    "title": "T1",
                    "topics": ["ai"],
                },
                {
                    "content": "Machine learning algorithms are improving.",
                    "title": "T2",
                    "topics": ["ml"],
                },
                {
                    "content": "Natural language processing is advancing.",
                    "title": "T3",
                    "topics": ["nlp"],
                },
            ]
        )

        # Get context for query
        context = self.rag_engine.get_context_for_query(
            query="artificial intelligence", user_interests=["ai", "technology"]
        )

        self.assertIsNotNone(context)
        self.assertIsInstance(context, str)

    def test_get_knowledge_base_stats(self):
        """Test getting knowledge base statistics"""
        # Add some test data
        self.rag_engine.documents = ["doc1", "doc2", "doc3"]
        self.rag_engine.metadata = [
            {"topics": ["ai", "tech"]},
            {"topics": ["ai", "research"]},
            {"topics": ["tech", "startup"]},
        ]

        stats = self.rag_engine.get_knowledge_base_stats()

        self.assertEqual(stats["total_documents"], 3)
        self.assertEqual(stats["unique_topics"], 3)  # ai, tech, research, startup
        self.assertIn("ai", stats["topics"])
        self.assertIn("tech", stats["topics"])
        self.assertIn("research", stats["topics"])
        self.assertIn("startup", stats["topics"])

    def test_clear_knowledge_base(self):
        """Test clearing knowledge base"""
        # Add some test data
        self.rag_engine.documents = ["doc1", "doc2"]
        self.rag_engine.metadata = [{"topics": ["ai"]}, {"topics": ["tech"]}]

        # Clear knowledge base
        self.rag_engine.clear_knowledge_base()

        self.assertEqual(len(self.rag_engine.documents), 0)
        self.assertEqual(len(self.rag_engine.metadata), 0)
        self.assertEqual(self.rag_engine.index.ntotal, 0)

    @patch("services.rag_service.OpenAI")
    def test_persistence(self, mock_openai):
        """Test data persistence"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        # Add test document
        self.rag_engine.add_documents(
            [{"content": "Test document for persistence", "title": "T", "topics": []}]
        )

        # Create new RAG engine instance (should load existing data)
        new_rag_engine = RAGService(persist_directory=self.temp_dir)

        # Check if data was loaded
        self.assertEqual(len(new_rag_engine.documents), 1)
        self.assertEqual(len(new_rag_engine.metadata), 1)
        self.assertEqual(new_rag_engine.documents[0], "Test document for persistence")

    def test_error_handling(self):
        """Test error handling in RAG engine"""
        # Test with invalid OpenAI API key
        with patch.dict(os.environ, {}, clear=True):
            from core.config import settings as cfg

            # openai key absent will raise in service init
            with self.assertRaises(Exception):
                RAGService(persist_directory=self.temp_dir)

    @patch("rag_engine.OpenAI")
    def test_embedding_error_handling(self, mock_openai):
        """Test handling of embedding errors"""
        # Mock OpenAI client to raise exception
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        # Should handle error gracefully
        success = self.rag_engine.add_documents(["Test document"])

        self.assertFalse(success)
        self.assertEqual(len(self.rag_engine.documents), 0)


if __name__ == "__main__":
    unittest.main()
