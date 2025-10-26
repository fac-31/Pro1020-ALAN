from email.message import EmailMessage
from email.header import decode_header
from email import message_from_bytes
from typing import Dict, Optional
import logging
import re
from .utils import clean_str

logger = logging.getLogger(__name__)

class EmailParser:
    def parse_email_message(self, raw_email: bytes) -> Optional[Dict]:
        """Parse email message and extract relevant information"""
        try:
            logger.info("Parsing email message, raw_email type: %s, length: %d", type(raw_email), len(raw_email) if raw_email else 0)
            
            # Handle potential encoding issues
            if isinstance(raw_email, str):
                logger.info("Converting string to bytes for email parsing")
                raw_email = raw_email.encode('utf-8', errors='ignore')
            
            logger.info("Creating email message from bytes...")
            msg = message_from_bytes(raw_email)
            logger.info("Email message created successfully")
            
            # Extract sender information
            sender_info = self.extract_sender_info(msg)
            
            # Extract subject
            subject = self.extract_subject(msg)
            
            # Extract body
            body = self.extract_email_body(msg)
            
            return {
                'sender_email': sender_info['email'],
                'sender_name': sender_info['name'],
                'subject': subject,
                'body': body.strip() if body else "",
                'message_id': msg.get('Message-ID', '')
            }
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    def extract_sender_info(self, msg: EmailMessage) -> Dict[str, str]:
        """Extract sender name and email from message"""
        from_header = msg.get('From', '')
        logger.info("From header: %s", clean_str(from_header))
        
        if from_header:
            # Decode header if needed
            logger.info("Decoding From header...")
            decoded_parts = decode_header(from_header)
            from_header = ''.join([part[0].decode(part[1] or 'utf-8', errors='ignore') if isinstance(part[0], bytes) else part[0] for part in decoded_parts])
            logger.info("Decoded From header: %s", clean_str(from_header))
            
            # Parse "Name <email@domain.com>" format
            if '<' in from_header and '>' in from_header:
                sender_name = from_header.split('<')[0].strip().strip('"')
                sender_email = from_header.split('<')[1].split('>')[0].strip()
            else:
                sender_email = from_header.strip()
                sender_name = sender_email
        else:
            sender_email = "unknown@example.com"
            sender_name = "Unknown"
        
        logger.info("Extracted sender: %s <%s>", clean_str(sender_name), clean_str(sender_email))
        return {'name': sender_name, 'email': sender_email}
    
    def extract_subject(self, msg: EmailMessage) -> str:
        """Extract and decode subject from message"""
        subject = msg.get('Subject', 'No Subject')
        logger.info("Subject header: %s", clean_str(subject))
        
        if subject:
            # Decode header if needed
            logger.info("Decoding Subject header...")
            decoded_parts = decode_header(subject)
            subject = ''.join([part[0].decode(part[1] or 'utf-8', errors='ignore') if isinstance(part[0], bytes) else part[0] for part in decoded_parts])
            logger.info("Decoded subject: %s", clean_str(subject))
        
        return subject
    
    def extract_email_body(self, msg: EmailMessage) -> str:
        """Extract email body from message"""
        body = ""
        logger.info("Email is multipart: %s", msg.is_multipart())
        
        if msg.is_multipart():
            logger.info("Processing multipart email...")
            for part in msg.walk():
                content_type = part.get_content_type()
                logger.info("Found part with content type: %s", clean_str(content_type))
                
                if content_type == "text/plain":
                    logger.info("Extracting plain text body...")
                    body = part.get_payload(decode=True)
                    if body:
                        body = body.decode('utf-8', errors='ignore')
                    logger.info("Plain text body length: %d", len(body) if body else 0)
                    break
                elif content_type == "text/html" and not body:
                    # Fallback to HTML if no plain text
                    logger.info("Extracting HTML body as fallback...")
                    body = part.get_payload(decode=True)
                    if body:
                        body = body.decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        body = re.sub(r'<[^>]+>', '', body)
                    logger.info("HTML body length after conversion: %d", len(body) if body else 0)
        else:
            # Single part message
            logger.info("Processing single part email...")
            body = msg.get_payload(decode=True)
            if body:
                body = body.decode('utf-8', errors='ignore')
            logger.info("Single part body length: %d", len(body) if body else 0)
        
        return body
