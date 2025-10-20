import imaplib
import smtplib
import json
import logging
import asyncio
import sys
import unicodedata
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.message import EmailMessage
from email import message_from_bytes
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# Ensure stdout/stderr are UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def clean_str(s):
    """Convert any bytes/str to safe, printable UTF-8."""
    if s is None:
        return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", errors="replace")
    # Normalize weird spaces, accents, etc.
    s = unicodedata.normalize("NFKC", s).replace("\xa0", " ")
    return s

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailClient:
    def __init__(self):
        self.gmail_user = os.getenv('GMAIL_USER')
        self.gmail_app_pass = os.getenv('GMAIL_APP_PASS')
        self.processed_file = 'processed_messages.json'
        
        if not self.gmail_user or not self.gmail_app_pass:
            raise ValueError("GMAIL_USER and GMAIL_APP_PASS must be set in environment variables")
    
    def load_processed_ids(self) -> List[str]:
        """Load processed message IDs from JSON file"""
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return data.get('processed_ids', [])
            return []
        except Exception as e:
            logger.error(f"Error loading processed IDs: {e}")
            return []
    
    def save_processed_id(self, message_id: str):
        """Save processed message ID to JSON file"""
        try:
            processed_ids = self.load_processed_ids()
            if message_id not in processed_ids:
                processed_ids.append(message_id)
                
                data = {'processed_ids': processed_ids}
                with open(self.processed_file, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Saved processed message ID: {message_id}")
        except Exception as e:
            logger.error(f"Error saving processed ID: {e}")
    
    def check_unread_emails(self) -> List[Dict]:
        """Check for unread emails via IMAP"""
        emails = []
        mail = None
        try:
            logger.info("Connecting to Gmail IMAP server...")
            # Connect to Gmail IMAP with Unicode-safe approach
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            logger.info("IMAP connection established")
            
            # Force UTF-8 encoding for Gmail IMAP
            mail._encoding = "utf-8"
            logger.info("UTF-8 encoding set for IMAP connection")
            
            logger.info("Logging in as %s", clean_str(self.gmail_user))
            mail.login(self.gmail_user, self.gmail_app_pass)
            logger.info("Successfully logged in to Gmail")
            
            # Re-enforce UTF-8 after login (Gmail may reset encoding)
            mail._encoding = "utf-8"
            logger.info("UTF-8 encoding re-enforced after login")
            
            logger.info("Selecting inbox...")
            try:
                mail.select('inbox')
                logger.info("Inbox selected")
            except UnicodeDecodeError as e:
                logger.warning(f"Unicode error selecting inbox: {e}")
                # Try to continue anyway
                logger.info("Attempting to continue despite Unicode error...")
            
            # Search for unread emails with Unicode-safe approach
            logger.info("Searching for unread emails...")
            try:
                # Use a more robust search approach
                status, messages = mail.search(None, 'UNSEEN')
                logger.info("Search status: %s", clean_str(str(status)))
            except UnicodeDecodeError as e:
                safe_error = unicodedata.normalize("NFKC", str(e)).replace("\xa0", " ")
                logger.warning("Unicode error in search, trying alternative approach: %s", safe_error)
                # Try with a different search method
                status, messages = mail.search(None, b'UNSEEN')
                logger.info("Alternative search status: %s", clean_str(str(status)))
            except Exception as e:
                safe_error = unicodedata.normalize("NFKC", str(e)).replace("\xa0", " ")
                logger.error("Search failed: %s", safe_error)
                status = 'NO'
                messages = [None]
            
            if status == 'OK' and messages[0]:
                try:
                    email_ids = messages[0].split()
                    logger.info("Found %d unread emails", len(email_ids))
                except UnicodeDecodeError as e:
                    safe_error = unicodedata.normalize("NFKC", str(e)).replace("\xa0", " ")
                    logger.warning("Unicode error splitting email IDs: %s", safe_error)
                    # Try to handle the email IDs as bytes
                    try:
                        email_ids = [msg.decode('utf-8', errors='ignore') for msg in messages[0].split()]
                        logger.info("Found %d unread emails (after Unicode fix)", len(email_ids))
                    except Exception as e2:
                        safe_error2 = unicodedata.normalize("NFKC", str(e2)).replace("\xa0", " ")
                        logger.error("Failed to process email IDs: %s", safe_error2)
                        email_ids = []
                
                for i, email_id in enumerate(email_ids):
                    try:
                        logger.info("Processing email %d/%d: %s", i+1, len(email_ids), clean_str(str(email_id)))
                        # Fetch email
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        logger.info("Fetch status for email %s: %s", clean_str(str(email_id)), clean_str(str(status)))
                        
                        if status == 'OK' and msg_data and msg_data[0]:
                            email_body = msg_data[0][1]
                            logger.info("Email body type: %s, length: %d", type(email_body), len(email_body) if email_body else 0)
                            
                            # Ensure we have bytes, not string
                            if isinstance(email_body, str):
                                logger.info("Converting string email body to bytes using latin-1")
                                email_body = email_body.encode('latin-1', errors='ignore')
                            
                            logger.info("Parsing email message...")
                            parsed_email = self.parse_email_message(email_body)
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
            else:
                logger.info("No unread emails found")
            
        except UnicodeDecodeError as e:
            import traceback
            logger.error("RAW UNICODE EXCEPTION >>> %s", repr(e))
            logger.debug("Full traceback:\n%s", traceback.format_exc())
            safe_error = unicodedata.normalize("NFKC", str(e)).replace("\xa0", " ")
            logger.error("Unicode decode error in email checking: %s", safe_error)
            logger.info("This error is likely due to non-ASCII characters in Gmail's IMAP response")
        except Exception as e:
            import traceback
            logger.error("RAW EXCEPTION >>> %s", repr(e))
            logger.debug("Full traceback:\n%s", traceback.format_exc())
            safe_error = unicodedata.normalize("NFKC", str(e)).replace("\xa0", " ")
            logger.error("Error checking emails: %s", safe_error)
        finally:
            if mail:
                try:
                    logger.info("Closing IMAP connection...")
                    # Only close if a mailbox is selected
                    if hasattr(mail, 'state') and mail.state == "SELECTED":
                        mail.close()
                    mail.logout()
                    logger.info("IMAP connection closed")
                except Exception as e:
                    logger.error("Error closing IMAP connection: %s", clean_str(str(e)))
        
        logger.info("Returning %d emails", len(emails))
        return emails
    
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
            
            # Extract sender
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
            
            # Extract subject
            subject = msg.get('Subject', 'No Subject')
            logger.info("Subject header: %s", clean_str(subject))
            if subject:
                # Decode header if needed
                logger.info("Decoding Subject header...")
                decoded_parts = decode_header(subject)
                subject = ''.join([part[0].decode(part[1] or 'utf-8', errors='ignore') if isinstance(part[0], bytes) else part[0] for part in decoded_parts])
                logger.info("Decoded subject: %s", clean_str(subject))
            
            # Extract body
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
                            import re
                            body = re.sub(r'<[^>]+>', '', body)
                        logger.info("HTML body length after conversion: %d", len(body) if body else 0)
            else:
                # Single part message
                logger.info("Processing single part email...")
                body = msg.get_payload(decode=True)
                if body:
                    body = body.decode('utf-8', errors='ignore')
                logger.info("Single part body length: %d", len(body) if body else 0)
            
            return {
                'sender_email': sender_email,
                'sender_name': sender_name,
                'subject': subject,
                'body': body.strip() if body else "",
                'message_id': msg.get('Message-ID', '')
            }
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    async def send_reply(self, to_email: str, subject: str, body: str, original_subject: str = "") -> bool:
        """Send email reply via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.gmail_user
            msg['To'] = to_email
            
            # Create reply subject
            if original_subject and not original_subject.startswith('Re:'):
                reply_subject = f"Re: {original_subject}"
            else:
                reply_subject = subject
            
            msg['Subject'] = reply_subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.gmail_user, self.gmail_app_pass)
            
            text = msg.as_string()
            server.sendmail(self.gmail_user, to_email, text)
            server.quit()
            
            logger.info(f"Reply sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return False
    
    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read in Gmail"""
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.gmail_user, self.gmail_app_pass)
            mail.select('inbox')
            
            # Mark as read
            mail.store(email_id, '+FLAGS', '\\Seen')
            
            mail.close()
            mail.logout()
            
            logger.info(f"Marked email {email_id} as read")
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False

def generate_reply(sender_name: str, subject: str, body: str) -> str:
    """Generate a simple reply message"""
    return f"""Hi {sender_name},

Thanks for your email about "{subject}". I'm Alan, your AI assistant, and I've received your message.

I'm currently in setup mode, but I'll be able to provide detailed, intelligent responses soon! 

Best regards,
Alan

---
Original message:
{body[:200]}{'...' if len(body) > 200 else ''}"""
