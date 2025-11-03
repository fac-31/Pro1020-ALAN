"""
Unit tests for email modules
Tests email parsing, connection handling, and message tracking
"""

import unittest
import tempfile
import os
import json
from email.message import EmailMessage
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_modules.parser import EmailParser
from email_modules.message_tracker import MessageTracker
from email_modules.utils import clean_str, setup_utf8_encoding


class TestEmailParser(unittest.TestCase):
    """Test email parsing functionality"""
    
    def setUp(self):
        self.parser = EmailParser()
    
    def test_parse_simple_email(self):
        """Test parsing a simple email message"""
        # Create a simple email
        msg = EmailMessage()
        msg['From'] = 'John Doe <john@example.com>'
        msg['To'] = 'alan@gmail.com'
        msg['Subject'] = 'Test Email'
        msg.set_content('Hello Alan, this is a test email.')
        
        raw_email = msg.as_bytes()
        result = self.parser.parse_email_message(raw_email)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['sender_email'], 'john@example.com')
        self.assertEqual(result['sender_name'], 'John Doe')
        self.assertEqual(result['subject'], 'Test Email')
        self.assertIn('Hello Alan', result['body'])
        self.assertEqual(result['attachments'], [])
        self.assertEqual(result['links'], [])
    
    def test_parse_email_with_links(self):
        """Test parsing email with links"""
        msg = EmailMessage()
        msg['From'] = 'Tech User <tech@example.com>'
        msg['Subject'] = 'Check this out'
        msg.set_content('''
        Hi Alan,
        
        Check out this interesting article: https://arxiv.org/abs/1706.03762
        Also see: https://openai.com/research
        
        Best regards
        ''')
        
        raw_email = msg.as_bytes()
        result = self.parser.parse_email_message(raw_email)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['links']), 2)
        self.assertIn('https://arxiv.org/abs/1706.03762', result['links'])
        self.assertIn('https://openai.com/research', result['links'])
    
    def test_parse_email_with_attachment(self):
        """Test parsing email with attachment"""
        msg = EmailMessage()
        msg['From'] = 'User <user@example.com>'
        msg['Subject'] = 'Document attached'
        msg.set_content('Please find the document attached.')
        
        # Add attachment
        msg.add_attachment(
            b'This is a test document content.',
            maintype='text',
            subtype='plain',
            filename='test_document.txt'
        )
        
        raw_email = msg.as_bytes()
        result = self.parser.parse_email_message(raw_email)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['attachments']), 1)
        attachment = result['attachments'][0]
        self.assertEqual(attachment['filename'], 'test_document.txt')
        self.assertEqual(attachment['content_type'], 'text/plain')
        self.assertGreater(attachment['size'], 0)
    
    def test_parse_multipart_email(self):
        """Test parsing multipart email"""
        msg = EmailMessage()
        msg['From'] = 'Sender <sender@example.com>'
        msg['Subject'] = 'Multipart Test'
        
        # Set multipart content
        msg.set_content('This is the plain text version.')
        msg.add_related('This is the HTML version.', subtype='html')
        
        raw_email = msg.as_bytes()
        result = self.parser.parse_email_message(raw_email)
        
        self.assertIsNotNone(result)
        self.assertIn('plain text version', result['body'])
    
    def test_extract_links_from_body(self):
        """Test link extraction from email body"""
        body = '''
        Check out these links:
        https://example.com/page1
        http://test.org/page2
        https://github.com/user/repo
        '''
        
        links = self.parser.extract_links_from_body(body)
        
        self.assertEqual(len(links), 3)
        self.assertIn('https://example.com/page1', links)
        self.assertIn('http://test.org/page2', links)
        self.assertIn('https://github.com/user/repo', links)
    
    def test_extract_attachments(self):
        """Test attachment extraction"""
        msg = EmailMessage()
        msg['From'] = 'Test <test@example.com>'
        msg.set_content('Email with attachments')
        
        # Add multiple attachments
        msg.add_attachment(
            b'PDF content here',
            maintype='application',
            subtype='pdf',
            filename='document.pdf'
        )
        msg.add_attachment(
            b'Image data',
            maintype='image',
            subtype='jpeg',
            filename='image.jpg'
        )
        
        attachments = self.parser.extract_attachments(msg)
        
        self.assertEqual(len(attachments), 2)
        filenames = [att['filename'] for att in attachments]
        self.assertIn('document.pdf', filenames)
        self.assertIn('image.jpg', filenames)


class TestMessageTracker(unittest.TestCase):
    """Test message tracking functionality"""
    
    def setUp(self):
        # Create temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        # Create tracker with temporary file
        self.tracker = MessageTracker(processed_messages_file=self.temp_file.name)
    
    def tearDown(self):
        # Clean up temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_save_and_load_processed_ids(self):
        """Test saving and loading processed message IDs"""
        # Test saving IDs
        self.tracker.save_processed_id('msg1')
        self.tracker.save_processed_id('msg2')
        self.tracker.save_processed_id('msg3')
        
        # Test loading IDs
        loaded_ids = self.tracker.load_processed_ids()
        
        self.assertEqual(len(loaded_ids), 3)
        self.assertIn('msg1', loaded_ids)
        self.assertIn('msg2', loaded_ids)
        self.assertIn('msg3', loaded_ids)
    
    def test_duplicate_ids_not_added(self):
        """Test that duplicate IDs are not added"""
        self.tracker.save_processed_id('msg1')
        self.tracker.save_processed_id('msg1')  # Duplicate
        self.tracker.save_processed_id('msg2')
        
        loaded_ids = self.tracker.load_processed_ids()
        
        self.assertEqual(len(loaded_ids), 2)  # Only unique IDs
        self.assertIn('msg1', loaded_ids)
        self.assertIn('msg2', loaded_ids)
    
    def test_empty_file_handling(self):
        """Test handling of empty or non-existent file"""
        # Test with empty file
        with open(self.temp_file.name, 'w') as f:
            f.write('')
        
        loaded_ids = self.tracker.load_processed_ids()
        self.assertEqual(loaded_ids, [])
        
        # Test with non-existent file
        os.unlink(self.temp_file.name)
        loaded_ids = self.tracker.load_processed_ids()
        self.assertEqual(loaded_ids, [])


class TestUtils(unittest.TestCase):
    """Test utility functions"""
    
    def test_clean_str(self):
        """Test string cleaning function"""
        # Test with normal string
        result = clean_str('Hello World')
        self.assertEqual(result, 'Hello World')
        
        # Test with special characters
        result = clean_str('Hello\nWorld\tTest')
        self.assertEqual(result, 'Hello\nWorld\tTest')  # clean_str doesn't replace newlines/tabs
        
        # Test with None
        result = clean_str(None)
        self.assertEqual(result, '')
        
        # Test with non-string input (should convert to string first)
        result = clean_str(123)
        self.assertEqual(result, '123')
    
    def test_setup_utf8_encoding(self):
        """Test UTF-8 encoding setup"""
        # This function sets environment variables, just test it doesn't crash
        try:
            setup_utf8_encoding()
            self.assertTrue(True)  # If we get here, it worked
        except Exception as e:
            self.fail(f"setup_utf8_encoding() raised an exception: {e}")


if __name__ == '__main__':
    unittest.main()
