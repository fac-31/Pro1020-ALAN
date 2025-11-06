"""
Integration tests for email processing pipeline
Tests the complete flow from email receipt to reply generation
"""

import unittest
import tempfile
import os
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from email.message import EmailMessage

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_modules.reply_generator import ReplyGenerator
from email_modules.background_tasks import email_polling_task
from services.content_service import ContentEvaluationService
from services.rag_service import RAGService


class TestEmailProcessingIntegration(unittest.TestCase):
    """Test complete email processing pipeline"""
    
    def setUp(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'GMAIL_USER': 'test@gmail.com',
            'GMAIL_APP_PASS': 'test_password',
            'OPENAI_API_KEY': 'test-key'
        }):
            # Mock email connection
            with patch('email_modules.connection.EmailConnection') as mock_connection:
                mock_conn = Mock()
                mock_connection.return_value = mock_conn
                
                # Mock IMAP connection
                mock_imap = Mock()
                mock_conn.get_imap_connection.return_value = mock_imap
                mock_conn.search_unread_emails.return_value = [b'1', b'2']
                mock_conn.fetch_email.return_value = self._create_test_email()
                mock_conn.close_imap_connection.return_value = True
                mock_conn.mark_as_read.return_value = True
                
                # Mock SMTP connection
                mock_conn.send_email.return_value = True
                
                self.email_client = EmailClient()
    
    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def _create_test_email(self):
        """Create a test email message"""
        msg = EmailMessage()
        msg['From'] = 'Test User <test@example.com>'
        msg['To'] = 'alan@gmail.com'
        msg['Subject'] = 'Test Email with AI Research'
        msg.set_content('''
        Hi Alan,
        
        I found this interesting research paper about transformer architectures.
        Check out this link: https://arxiv.org/abs/1706.03762
        
        Also, I have attached our technical documentation for review.
        
        Best regards,
        Test User
        ''')
        
        # Add attachment
        msg.add_attachment(
            b'This is a technical document about AI research.',
            maintype='text',
            subtype='plain',
            filename='research_notes.txt'
        )
        
        return msg.as_bytes()
    
    def test_email_client_initialization(self):
        """Test email client initialization"""
        self.assertIsNotNone(self.email_client)
        self.assertIsNotNone(self.email_client.connection)
        self.assertIsNotNone(self.email_client.parser)
        self.assertIsNotNone(self.email_client.tracker)
        self.assertIsNotNone(self.email_client.reply_generator)
    
    def test_email_parsing_with_attachments_and_links(self):
        """Test parsing email with attachments and links"""
        test_email = self._create_test_email()
        parsed_email = self.email_client.parser.parse_email_message(test_email)
        
        self.assertIsNotNone(parsed_email)
        self.assertEqual(parsed_email['sender_email'], 'test@example.com')
        self.assertEqual(parsed_email['sender_name'], 'Test User')
        self.assertEqual(parsed_email['subject'], 'Test Email with AI Research')
        self.assertIn('transformer architectures', parsed_email['body'])
        self.assertEqual(len(parsed_email['attachments']), 1)
        self.assertEqual(len(parsed_email['links']), 1)
        self.assertIn('https://arxiv.org/abs/1706.03762', parsed_email['links'])
    
    def test_reply_generator_fallback(self):
        """Test reply generator fallback"""
        rg = ReplyGenerator()
        reply = rg._generate_fallback_reply('Test User', 'Test Subject')
        self.assertIn('Test User', reply)
    
    @patch('services.content_service.OpenAI')
    @patch('services.content_service.ChatOpenAI')
    def test_content_evaluation_integration(self, mock_chat_openai, mock_openai):
        """Test content evaluation integration"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock ChatOpenAI
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm
        
        # Mock AI response
        mock_response = Mock()
        mock_response.content = '{"should_add": true, "confidence": 0.8, "content_type": "research", "topics": ["ai", "research"], "reasoning": "High-quality technical content"}'
        mock_llm.invoke.return_value = mock_response
        
        evaluator = ContentEvaluationService()
        
        evaluation = asyncio.run(evaluator.evaluate_email_content(
            sender_email='tech@example.com',
            subject='AI Research Paper',
            body='Check out this research paper about transformers.',
            attachments=[{
                'filename': 'paper.pdf',
                'content_type': 'application/pdf',
                'content': b'PDF content'
            }],
            links=['https://arxiv.org/abs/1706.03762']
        ))
        
        self.assertIsNotNone(evaluation)
        self.assertTrue(evaluation.should_add)
        self.assertGreater(evaluation.confidence, 0.5)
        self.assertIn('ai', evaluation.topics)
        self.assertIn('research', evaluation.topics)
    
    @patch('services.rag_service.OpenAI')
    def test_rag_engine_integration(self, mock_openai):
        """Test RAG engine integration"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        
        rag_engine = RAGService(persist_directory=self.temp_dir)
        
        # Add test documents
        success = rag_engine.add_documents([
            "AI is transforming industries.",
            "Machine learning algorithms are improving."
        ])
        
        self.assertTrue(success)
        self.assertEqual(len(rag_engine.documents), 2)
        
        # Search for documents
        results = rag_engine.search_documents("artificial intelligence", n_results=1)
        self.assertIsNotNone(results)
        self.assertLessEqual(len(results), 1)
    
    @patch('services.content_service.OpenAI')
    @patch('services.content_service.ChatOpenAI')
    @patch('services.rag_service.OpenAI')
    def test_complete_email_processing_pipeline(self, mock_rag_openai, mock_chat_openai, mock_openai):
        """Test complete email processing pipeline"""
        # Mock OpenAI clients
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_rag_openai.return_value = mock_client
        
        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        
        # Mock ChatOpenAI
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm
        
        # Mock AI response for content evaluation
        mock_response = Mock()
        mock_response.content = '{"should_add": true, "confidence": 0.8, "content_type": "research", "topics": ["ai", "research"], "reasoning": "High-quality technical content"}'
        mock_llm.invoke.return_value = mock_response
        
        # Initialize RAG engine
        rag_engine = RAGService(persist_directory=self.temp_dir)
        
        # Test email processing
        test_email = self._create_test_email()
        parsed_email = self.email_client.parser.parse_email_message(test_email)
        
        self.assertIsNotNone(parsed_email)
        
        # Test content evaluation
        evaluator = ContentEvaluationService()
        evaluation = asyncio.run(evaluator.evaluate_email_content(
            sender_email=parsed_email['sender_email'],
            subject=parsed_email['subject'],
            body=parsed_email['body'],
            attachments=parsed_email['attachments'],
            links=parsed_email['links']
        ))
        
        self.assertIsNotNone(evaluation)
        
        # Test adding to knowledge base if evaluation suggests it
        if evaluation.should_add and evaluation.confidence > 0.6:
            success = rag_engine.add_user_document(
                content=evaluation.extracted_content,
                title=f"Email from {parsed_email['sender_name']}: {parsed_email['subject']}",
                topics=evaluation.topics
            )
            self.assertTrue(success)
        
        # Test reply generation
        rg = ReplyGenerator()
        reply = rg._generate_fallback_reply(parsed_email['sender_name'], parsed_email['subject'])
        
        self.assertIsNotNone(reply)
        self.assertIsInstance(reply, str)
        self.assertGreater(len(reply), 0)


class TestBackgroundTaskIntegration(unittest.TestCase):
    """Test background task integration"""
    
    def setUp(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'GMAIL_USER': 'test@gmail.com',
            'GMAIL_APP_PASS': 'test_password',
            'OPENAI_API_KEY': 'test-key',
            'POLLING_INTERVAL': '1'  # Short interval for testing
        }):
            # Mock email client
            with patch('services.email_service.EmailService') as mock_email_client:
                mock_client = Mock()
                mock_email_client.return_value = mock_client
                
                # Mock email data
                mock_client.check_unread_emails.return_value = [
                    {
                        'sender_email': 'test@example.com',
                        'sender_name': 'Test User',
                        'subject': 'Test Subject',
                        'body': 'Test message body',
                        'attachments': [],
                        'links': [],
                        'message_id': 'test_msg_1',
                        'email_id': 'email_1'
                    }
                ]
                mock_client.load_processed_ids.return_value = []
                mock_client.save_processed_id.return_value = True
                mock_client.mark_as_read.return_value = True
                
                self.email_client = mock_client
    
    def tearDown(self):
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    @patch('services.content_service.OpenAI')
    @patch('services.content_service.ChatOpenAI')
    @patch('services.rag_service.OpenAI')
    @patch('services.email_service.EmailService.generate_reply')
    def test_email_polling_task_integration(self, mock_generate_reply, mock_rag_openai, mock_chat_openai, mock_openai):
        """Test email polling task integration"""
        # Mock OpenAI clients
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_rag_openai.return_value = mock_client
        
        # Mock embedding function
        mock_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        
        # Mock ChatOpenAI
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm
        
        # Mock AI response for content evaluation
        mock_response = Mock()
        mock_response.content = '{"should_add": true, "confidence": 0.8, "content_type": "research", "topics": ["ai", "research"], "reasoning": "High-quality technical content"}'
        mock_llm.invoke.return_value = mock_response
        
        # Mock reply generation
        mock_generate_reply.return_value = "This is a test reply from Alan."
        
        # Initialize RAG engine
        rag_engine = RAGService(persist_directory=self.temp_dir)
        
        # Test the polling task (run for a short time)
        async def test_polling():
            task = asyncio.create_task(
                email_polling_task(self.email_client, rag_engine)
            )
            
            # Let it run for a short time
            await asyncio.sleep(0.1)
            
            # Cancel the task
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Run the test
        asyncio.run(test_polling())
        
        # Verify that the email client methods were called
        self.email_client.check_unread_emails.assert_called()
        self.email_client.load_processed_ids.assert_called()
        mock_generate_reply.assert_called()


if __name__ == '__main__':
    unittest.main()
