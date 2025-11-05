"""
Email Client - Main orchestrator for email operations
"""

import logging
from typing import List, Dict
from email_modules.connection import EmailConnection
from email_modules.parser import EmailParser
from email_modules.message_tracker import MessageTracker
from email_modules.reply_generator import ReplyGenerator
from email_modules.utils import clean_str, setup_utf8_encoding

# Setup UTF-8 encoding
setup_utf8_encoding()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailClient:
    def __init__(self):
        from core.config import settings
        
        self.gmail_user = settings.gmail_user
        self.gmail_app_pass = settings.gmail_app_pass
        
        if not self.gmail_user or not self.gmail_app_pass:
            raise ValueError("Gmail credentials not configured")
        
        # Initialize components
        self.connection = EmailConnection(self.gmail_user, self.gmail_app_pass)
        self.parser = EmailParser()
        self.tracker = MessageTracker()
        self.reply_generator = ReplyGenerator()
    
    def load_processed_ids(self) -> List[str]:
        """Load processed message IDs from JSON file"""
        return self.tracker.load_processed_ids()
    
    def save_processed_id(self, message_id: str):
        """Save processed message ID to JSON file"""
        self.tracker.save_processed_id(message_id)
    
    def check_unread_emails(self) -> List[Dict]:
        """Check for unread emails via IMAP"""
        emails = []
        mail = None
        
        try:
            mail = self.connection.get_imap_connection()
            if not mail:
                logger.error("Failed to establish IMAP connection")
                return emails
            
            # Search for unread emails
            email_ids = self.connection.search_unread_emails(mail)
            
            for i, email_id in enumerate(email_ids):
                try:
                    logger.info("Processing email %d/%d: %s", i+1, len(email_ids), clean_str(str(email_id)))
                    
                    # Fetch email content
                    email_body = self.connection.fetch_email(mail, email_id)
                    if email_body:
                        # Check email size before parsing (skip very large emails)
                        email_size_mb = len(email_body) / (1024 * 1024)
                        if email_size_mb > 5.0:  # Skip emails larger than 5MB
                            logger.warning(f"Skipping email {email_id}: too large ({email_size_mb:.2f} MB)")
                            continue
                        
                        # Parse email message with timeout protection
                        try:
                            parsed_email = self.parser.parse_email_message(email_body)
                        except Exception as e:
                            logger.error(f"Error parsing email {email_id}: {e}")
                            continue
                            
                        if parsed_email:
                            parsed_email['email_id'] = email_id.decode('utf-8', errors='ignore')
                            emails.append(parsed_email)
                            logger.info("Successfully parsed email from %s", clean_str(parsed_email.get('sender_email', 'unknown')))
                        else:
                            logger.warning("Failed to parse email %s", clean_str(str(email_id)))
                    else:
                        logger.warning("No email data for %s", clean_str(str(email_id)))
                        
                except UnicodeDecodeError as e:
                    logger.warning("Unicode error processing email %s, skipping: %s", clean_str(str(email_id)), clean_str(str(e)))
                    continue
                except Exception as e:
                    logger.error("Error processing email %s: %s", clean_str(str(email_id)), clean_str(str(e)))
                    continue
                    
        except UnicodeDecodeError as e:
            import traceback
            logger.error("RAW UNICODE EXCEPTION >>> %s", repr(e))
            logger.debug("Full traceback:\n%s", traceback.format_exc())
            logger.error("Unicode decode error in email checking: %s", clean_str(str(e)))
            logger.info("This error is likely due to non-ASCII characters in Gmail's IMAP response")
        except Exception as e:
            import traceback
            logger.error("RAW EXCEPTION >>> %s", repr(e))
            logger.debug("Full traceback:\n%s", traceback.format_exc())
            logger.error("Error checking emails: %s", clean_str(str(e)))
        finally:
            if mail:
                self.connection.close_imap_connection(mail)
        
        logger.info("Returning %d emails", len(emails))
        return emails
    
    def send_reply(self, to_email: str, subject: str, body: str, original_subject: str = "") -> bool:
        """Send email reply via SMTP"""
        return self.connection.send_email(to_email, subject, body, original_subject)
    
    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read in Gmail"""
        return self.connection.mark_as_read(email_id)

def generate_reply(sender_name: str, sender_email: str, subject: str, body: str) -> str:
    """Generate a simple reply message"""
    reply_generator = ReplyGenerator()
    return reply_generator.generate_reply(sender_name, sender_email, subject, body)
