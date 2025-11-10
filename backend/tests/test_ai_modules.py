"""
Unit tests for AI modules
Tests AI service, conversation memory, and content evaluation
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import AIService
from ai_modules.conversation_memory import ConversationMemory
from services.content_service import ContentEvaluationService, ContentEvaluation


class TestConversationMemory(unittest.TestCase):
    """Test conversation memory functionality"""

    def setUp(self):
        # Create temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        )
        self.temp_file.close()

        # Initialize memory with explicit file path
        self.memory = ConversationMemory(memory_file=self.temp_file.name)

    def tearDown(self):
        # Clean up temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_add_and_get_messages(self):
        """Test adding and retrieving messages"""
        # Add messages
        self.memory.add_message(
            "user@example.com", "incoming", "Hello Alan", "Greeting"
        )
        self.memory.add_message("user@example.com", "outgoing", "Hi there!", "Reply")

        # Get conversation history
        history = self.memory.get_conversation_history("user@example.com")

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Hello Alan")
        self.assertEqual(history[1]["content"], "Hi there!")

    def test_conversation_history_limit(self):
        """Test conversation history with limit"""
        # Add multiple messages
        for i in range(10):
            self.memory.add_message(
                "user@example.com", "incoming", f"Message {i}", f"Subject {i}"
            )

        # Get limited history
        history = self.memory.get_conversation_history("user@example.com", limit=5)

        self.assertEqual(len(history), 5)
        # Should get the most recent messages
        self.assertEqual(history[0]["content"], "Message 9")
        self.assertEqual(history[4]["content"], "Message 5")

    def test_multiple_users(self):
        """Test memory with multiple users"""
        # Add messages for different users
        self.memory.add_message(
            "user1@example.com", "incoming", "Hello from user1", "Subject1"
        )
        self.memory.add_message(
            "user2@example.com", "incoming", "Hello from user2", "Subject2"
        )

        # Get history for each user
        history1 = self.memory.get_conversation_history("user1@example.com")
        history2 = self.memory.get_conversation_history("user2@example.com")

        self.assertEqual(len(history1), 1)
        self.assertEqual(len(history2), 1)
        self.assertEqual(history1[0]["content"], "Hello from user1")
        self.assertEqual(history2[0]["content"], "Hello from user2")

    def test_empty_history(self):
        """Test getting history for non-existent user"""
        history = self.memory.get_conversation_history("nonexistent@example.com")
        self.assertEqual(history, [])


class TestContentEvaluationService(unittest.TestCase):
    """Test content evaluation functionality"""

    def setUp(self):
        # Mock OpenAI API key and init service
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            self.evaluator = ContentEvaluationService()

    @patch("services.content_service.OpenAI")
    @patch("services.content_service.ChatOpenAI")
    def test_content_evaluation_service_initialization(
        self, mock_chat_openai, mock_openai
    ):
        """Test content evaluation service initialization"""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm
        svc = ContentEvaluationService()
        self.assertIsNotNone(svc.client)
        self.assertIsNotNone(svc.llm)

    def test_extract_attachment_content(self):
        """Test attachment content extraction (batch)"""
        # Batch with different types
        attachments = [
            {
                "filename": "test.txt",
                "content_type": "text/plain",
                "content": b"This is test content",
            },
            {
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "content": b"PDF content",
            },
            {
                "filename": "image.jpg",
                "content_type": "image/jpeg",
                "content": b"Image data",
            },
        ]
        content = self.evaluator._extract_attachment_content(attachments)
        self.assertIn("This is test content", content)
        self.assertIn("[File: document.pdf", content) or self.assertIn("[PDF", content)
        self.assertIn("image.jpg", content)

    @patch("requests.get")
    def test_extract_link_content(self, mock_get):
        """Test link content extraction (batch)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><head><title>T</title></head><body><p>This is test content</p></body></html>"
        mock_get.return_value = mock_response
        content = asyncio.run(
            self.evaluator._extract_link_content(["https://example.com"])
        )
        self.assertIn("This is test content", content) or self.assertIn(
            "Title", content
        )

    def test_evaluate_email_content_empty(self):
        """Test evaluation of empty email content"""
        evaluation = asyncio.run(
            self.evaluator.evaluate_email_content(
                sender_email="test@example.com",
                subject="Empty",
                body="",
                attachments=[],
                links=[],
            )
        )

        self.assertFalse(evaluation.should_add)
        self.assertIn(evaluation.content_type, ["empty", "no_extractable_content"])

    def test_evaluate_email_content_with_links(self):
        """Test evaluation of email with links"""
        evaluation = asyncio.run(
            self.evaluator.evaluate_email_content(
                sender_email="tech@example.com",
                subject="AI Research Paper",
                body="Check out this paper: https://arxiv.org/abs/1706.03762",
                attachments=[],
                links=["https://arxiv.org/abs/1706.03762"],
            )
        )

        # Should have extracted content
        self.assertIsNotNone(evaluation.extracted_content)
        self.assertIn("https://arxiv.org/abs/1706.03762", evaluation.extracted_content)


class TestAIService(unittest.TestCase):
    """Test AI service functionality"""

    def setUp(self):
        # Mock OpenAI API key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            self.ai_service = AIService()

    @patch("services.ai_service.OpenAI")
    @patch("services.ai_service.ChatOpenAI")
    def test_ai_service_initialization(self, mock_chat_openai, mock_openai):
        """Test AI service initialization"""
        # Mock the OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock the ChatOpenAI
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm

        ai_service = AIService()

        self.assertIsNotNone(ai_service.client)
        self.assertIsNotNone(ai_service.llm)
        self.assertIsNotNone(ai_service.rag_engine)

    def test_extract_query_from_email(self):
        """Test query extraction from email"""
        subject = "AI Research Paper"
        body = "I found this interesting research about transformer architectures."

        query = self.ai_service._extract_query_from_email(subject, body)

        self.assertIsNotNone(query)
        self.assertIn("AI Research Paper", query)
        self.assertIn("transformer architectures", query)

    def test_create_system_prompt(self):
        """Test system prompt creation"""
        user_interests = ["ai", "technology"]
        context = ["Context about AI research", "More context about technology"]

        prompt = self.ai_service._create_system_prompt(user_interests, context)

        self.assertIsNotNone(prompt)
        self.assertIn("Alan", prompt)
        self.assertIn("AI assistant", prompt)
        self.assertIn("ai", prompt.lower())
        self.assertIn("technology", prompt.lower())

    def test_create_human_message(self):
        """Test human message creation"""
        sender_name = "John Doe"
        sender_email = "john@example.com"
        subject = "Test Subject"
        body = "Test message body"
        conversation_history = [{"content": "Previous message", "role": "user"}]

        message = self.ai_service._create_human_message(
            sender_name, sender_email, subject, body, conversation_history
        )

        self.assertIsNotNone(message)
        self.assertIn("John Doe", message)
        self.assertIn("Test Subject", message)
        self.assertIn("Test message body", message)
        self.assertIn("Previous message", message)


if __name__ == "__main__":
    unittest.main()
