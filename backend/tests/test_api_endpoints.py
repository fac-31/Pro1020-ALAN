"""
API endpoint tests
Tests FastAPI endpoints and HTTP responses
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'GMAIL_USER': 'test@gmail.com',
            'GMAIL_APP_PASS': 'test_password',
            'OPENAI_API_KEY': 'test-key'
        }):
            # Mock all services
            with patch('main.initialize_email_client') as mock_init_email, \
                 patch('main.RAGEngine') as mock_rag, \
                 patch('main.AIService') as mock_ai, \
                 patch('main.DailyDigestService') as mock_digest:
                
                # Mock RAG engine
                mock_rag_instance = Mock()
                mock_rag.return_value = mock_rag_instance
                
                # Mock AI service
                mock_ai_instance = Mock()
                mock_ai.return_value = mock_ai_instance
                
                # Mock digest service
                mock_digest_instance = Mock()
                mock_digest.return_value = mock_digest_instance
                
                # Mock email client
                mock_email_client = Mock()
                mock_email_client.connection = Mock()
                
                # Mock app state
                app.state.email_client = mock_email_client
                app.state.rag_engine = mock_rag_instance
                app.state.ai_service = mock_ai_instance
                app.state.digest_service = mock_digest_instance
                
                self.client = TestClient(app)
    
    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_home_endpoint(self):
        """Test home endpoint"""
        response = self.client.get("/")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["message"], "Alan's AI Assistant Backend")
        self.assertEqual(data["status"], "running")
        self.assertIn("Email-based AI assistant", data["features"])
        self.assertIn("RAG-powered responses", data["features"])
        self.assertIn("AI content evaluation", data["features"])
        self.assertIn("Email attachment processing", data["features"])
        self.assertIn("Link content extraction", data["features"])
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["email_client"], "initialized")
        self.assertEqual(data["rag_engine"], "initialized")
        self.assertEqual(data["ai_service"], "initialized")
        self.assertEqual(data["digest_service"], "initialized")
        self.assertEqual(data["content_evaluation"], "enabled")
        self.assertEqual(data["attachment_processing"], "enabled")
        self.assertEqual(data["link_extraction"], "enabled")
    
    def test_processed_messages_endpoint(self):
        """Test processed messages endpoint"""
        # Mock processed IDs
        app.state.email_client.load_processed_ids.return_value = ["msg1", "msg2", "msg3"]
        
        response = self.client.get("/processed_messages")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("processed_message_ids", data)
        self.assertEqual(len(data["processed_message_ids"]), 3)
        self.assertIn("msg1", data["processed_message_ids"])
        self.assertIn("msg2", data["processed_message_ids"])
        self.assertIn("msg3", data["processed_message_ids"])
    
    def test_processed_messages_endpoint_no_email_client(self):
        """Test processed messages endpoint when email client is not available"""
        app.state.email_client = None
        
        response = self.client.get("/processed_messages")
        
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["detail"], "Email service is not available.")
    
    @patch('rag_engine.OpenAI')
    def test_rag_endpoints(self, mock_openai):
        """Test RAG-related endpoints"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        
        # Test document upload endpoint
        document_data = {
            "content": "This is a test document about AI.",
            "title": "Test Document",
            "topics": ["ai", "test"]
        }
        
        response = self.client.post("/documents/upload", json=document_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Document added successfully")
        self.assertTrue(data["success"])
        
        # Test news article endpoint
        news_data = {
            "title": "AI Breakthrough",
            "content": "Scientists have made a breakthrough in AI research.",
            "topics": ["ai", "research", "breakthrough"]
        }
        
        response = self.client.post("/news/add", json=news_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "News article added successfully")
        self.assertTrue(data["success"])
        
        # Test search endpoint
        search_data = {
            "query": "artificial intelligence",
            "user_interests": ["ai", "technology"],
            "n_results": 5
        }
        
        response = self.client.post("/search", json=search_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("query", data)
        
        # Test knowledge base stats endpoint
        response = self.client.get("/knowledge-base/stats")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_documents", data)
        self.assertIn("unique_topics", data)
        self.assertIn("topics", data)
        
        # Test clear knowledge base endpoint
        response = self.client.delete("/knowledge-base/clear")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Knowledge base cleared successfully")
        self.assertTrue(data["success"])
    
    def test_subscriber_endpoints(self):
        """Test subscriber-related endpoints"""
        # Test subscribe endpoint
        subscriber_data = {
            "email": "test@example.com",
            "interests": ["ai", "technology"],
            "name": "Test User"
        }
        
        response = self.client.post("/subscribe", json=subscriber_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Successfully subscribed to Alan's daily digest")
        self.assertTrue(data["success"])
        
        # Test get subscribers endpoint
        response = self.client.get("/subscribers")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("subscribers", data)
        self.assertIn("total_count", data)
        
        # Test get specific subscriber endpoint
        response = self.client.get("/subscribers/test@example.com")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "test@example.com")
        self.assertIn("interests", data)
        self.assertIn("name", data)
    
    def test_digest_endpoints(self):
        """Test daily digest endpoints"""
        # Test digest subscribe endpoint
        digest_data = {
            "email": "digest@example.com",
            "interests": ["ai", "startups"],
            "name": "Digest User"
        }
        
        response = self.client.post("/digest/subscribe", json=digest_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Successfully subscribed to daily digest")
        self.assertTrue(data["success"])
        
        # Test digest unsubscribe endpoint
        response = self.client.delete("/digest/unsubscribe/digest@example.com")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Successfully unsubscribed from daily digest")
        self.assertTrue(data["success"])
        
        # Test digest stats endpoint
        response = self.client.get("/digest/stats")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_subscribers", data)
        self.assertIn("subscribers", data)
    
    @patch('rag_engine.OpenAI')
    def test_test_rag_endpoint(self, mock_openai):
        """Test RAG test endpoint"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        
        response = self.client.post("/test-rag")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "RAG test completed successfully")
        self.assertTrue(data["success"])
        self.assertIn("test_results", data)
    
    def test_invalid_endpoints(self):
        """Test invalid endpoints return 404"""
        response = self.client.get("/invalid-endpoint")
        self.assertEqual(response.status_code, 404)
        
        response = self.client.post("/invalid-endpoint")
        self.assertEqual(response.status_code, 404)
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = self.client.get("/")
        
        # CORS headers should be present
        self.assertIn("access-control-allow-origin", response.headers)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")


if __name__ == '__main__':
    unittest.main()
