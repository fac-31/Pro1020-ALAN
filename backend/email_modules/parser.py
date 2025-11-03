from email.message import EmailMessage
from email.header import decode_header
from email import message_from_bytes
from typing import Dict, Optional, List
import logging
import re
from .utils import clean_str

logger = logging.getLogger(__name__)

class EmailParser:
    def __init__(self):
        from core.config import settings
        self.settings = settings
    
    def parse_email_message(self, raw_email: bytes) -> Optional[Dict]:
        """Parse email message and extract relevant information"""
        try:
            email_size_mb = len(raw_email) / (1024 * 1024)
            logger.info("Parsing email message, raw_email type: %s, length: %d bytes (%.2f MB)", 
                       type(raw_email), len(raw_email) if raw_email else 0, email_size_mb)
            
            # Skip very large emails to prevent hanging
            if email_size_mb > self.settings.max_email_size_mb:
                logger.warning("Email too large (%.2f MB > %.2f MB), skipping", 
                              email_size_mb, self.settings.max_email_size_mb)
                return None
            
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
            
            # Extract attachments (only if enabled and email isn't too large)
            attachments = []
            if self.settings.extract_attachments and email_size_mb < self.settings.max_email_size_mb:
                attachments = self.extract_attachments(msg)
            else:
                logger.info("Skipping attachment extraction (disabled or email too large)")
            
            # Extract links from body
            links = self.extract_links_from_body(body)
            
            return {
                'sender_email': sender_info['email'],
                'sender_name': sender_info['name'],
                'subject': subject,
                'body': body.strip() if body else "",
                'message_id': msg.get('Message-ID', ''),
                'attachments': attachments,
                'links': links
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
        """Extract email body from message (with size limits)"""
        body = ""
        max_body_size = 100 * 1024  # Limit body to 100KB to prevent memory issues
        logger.info("Email is multipart: %s", msg.is_multipart())
        
        if msg.is_multipart():
            logger.info("Processing multipart email...")
            parts_processed = 0
            for part in msg.walk():
                parts_processed += 1
                if parts_processed > 50:  # Safety limit: don't process more than 50 parts
                    logger.warning("Email has too many parts (>50), stopping body extraction")
                    break
                    
                content_type = part.get_content_type()
                logger.info("Found part with content type: %s", clean_str(content_type))
                
                if content_type == "text/plain":
                    logger.info("Extracting plain text body...")
                    try:
                        body_bytes = part.get_payload(decode=True)
                        if body_bytes:
                            body = body_bytes.decode('utf-8', errors='ignore')
                            # Truncate if too large
                            if len(body) > max_body_size:
                                logger.warning(f"Body too large ({len(body)} bytes), truncating to {max_body_size} bytes")
                                body = body[:max_body_size] + "... [truncated]"
                        logger.info("Plain text body length: %d", len(body) if body else 0)
                        if body:
                            break  # Found plain text, stop processing
                    except Exception as e:
                        logger.warning(f"Error extracting plain text body: {e}")
                        continue
                        
                elif content_type == "text/html" and not body:
                    # Fallback to HTML if no plain text
                    logger.info("Extracting HTML body as fallback...")
                    try:
                        body_bytes = part.get_payload(decode=True)
                        if body_bytes:
                            body = body_bytes.decode('utf-8', errors='ignore')
                            # Simple HTML to text conversion
                            body = re.sub(r'<[^>]+>', '', body)
                            # Truncate if too large
                            if len(body) > max_body_size:
                                logger.warning(f"HTML body too large ({len(body)} bytes), truncating to {max_body_size} bytes")
                                body = body[:max_body_size] + "... [truncated]"
                        logger.info("HTML body length after conversion: %d", len(body) if body else 0)
                        if body:
                            break  # Found HTML, stop processing
                    except Exception as e:
                        logger.warning(f"Error extracting HTML body: {e}")
                        continue
        else:
            # Single part message
            logger.info("Processing single part email...")
            try:
                body_bytes = msg.get_payload(decode=True)
                if body_bytes:
                    body = body_bytes.decode('utf-8', errors='ignore')
                    # Truncate if too large
                    if len(body) > max_body_size:
                        logger.warning(f"Body too large ({len(body)} bytes), truncating to {max_body_size} bytes")
                        body = body[:max_body_size] + "... [truncated]"
                logger.info("Single part body length: %d", len(body) if body else 0)
            except Exception as e:
                logger.warning(f"Error extracting single part body: {e}")
        
        return body
    
    def extract_attachments(self, msg: EmailMessage) -> List[Dict]:
        """Extract attachment information from email message (with size limits)"""
        attachments = []
        max_size_bytes = int(self.settings.max_attachment_size_mb * 1024 * 1024)
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        content_type = part.get_content_type()
                        
                        if filename:
                            # Decode filename if needed
                            decoded_parts = decode_header(filename)
                            filename = ''.join([
                                part[0].decode(part[1] or 'utf-8', errors='ignore') 
                                if isinstance(part[0], bytes) else part[0] 
                                for part in decoded_parts
                            ])
                            
                            # Check if we should extract content (skip large attachments)
                            try:
                                # Try to get content length without decoding full payload
                                payload = part.get_payload(decode=False)
                                if isinstance(payload, list):
                                    # Multipart - estimate size
                                    content_size = sum(len(str(p)) for p in payload[:10])  # Sample first 10 parts
                                else:
                                    content_size = len(str(payload))
                                
                                # Only decode if within size limit
                                if content_size > max_size_bytes:
                                    logger.info(f"Skipping large attachment: {filename} (~{content_size / (1024*1024):.2f} MB > {self.settings.max_attachment_size_mb} MB)")
                                    attachments.append({
                                        'filename': filename,
                                        'content_type': content_type,
                                        'size': content_size,
                                        'content': None,  # Content not extracted due to size
                                        'skipped': True
                                    })
                                    continue
                                
                                # Get attachment content (only for smaller attachments)
                                content = part.get_payload(decode=True)
                                if content and len(content) > max_size_bytes:
                                    logger.info(f"Attachment {filename} decoded but too large ({len(content) / (1024*1024):.2f} MB), truncating metadata")
                                    attachments.append({
                                        'filename': filename,
                                        'content_type': content_type,
                                        'size': len(content),
                                        'content': None,  # Don't store large content
                                        'skipped': True
                                    })
                                else:
                                    attachments.append({
                                        'filename': filename,
                                        'content_type': content_type,
                                        'size': len(content) if content else 0,
                                        'content': content
                                    })
                                    
                                    logger.info(f"Found attachment: {filename} ({content_type}, {len(content) / 1024:.1f} KB)")
                                    
                            except Exception as e:
                                logger.warning(f"Error processing attachment {filename}: {e}, skipping")
                                continue
            
            return attachments
            
        except Exception as e:
            logger.error(f"Error extracting attachments: {e}", exc_info=True)
            return []
    
    def extract_links_from_body(self, body: str) -> List[str]:
        """Extract URLs from email body"""
        if not body:
            return []
        
        # URL regex pattern
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, body)
        
        # Remove duplicates and return
        unique_urls = list(set(urls))
        logger.info(f"Found {len(unique_urls)} unique links in email body")
        
        return unique_urls
