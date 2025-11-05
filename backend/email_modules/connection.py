import imaplib
import smtplib
import logging
import unicodedata
import aiosmtplib
from typing import Optional, List, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .utils import clean_str

logger = logging.getLogger(__name__)

class EmailConnection:
    def __init__(self, gmail_user: str, gmail_app_pass: str):
        self.gmail_user = gmail_user
        self.gmail_app_pass = gmail_app_pass
    
    def get_imap_connection(self) -> Optional[imaplib.IMAP4_SSL]:
        """Get IMAP connection to Gmail"""
        try:
            logger.info("Connecting to Gmail IMAP server...")
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
            
            return mail
        except Exception as e:
            logger.error(f"Error connecting to IMAP: {e}")
            return None
    
    def get_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """Get SMTP connection to Gmail"""
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.gmail_user, self.gmail_app_pass)
            return server
        except Exception as e:
            logger.error(f"Error connecting to SMTP: {e}")
            return None
    
    def close_imap_connection(self, mail: imaplib.IMAP4_SSL):
        """Close IMAP connection safely"""
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
    
    def close_smtp_connection(self, server: smtplib.SMTP):
        """Close SMTP connection safely"""
        if server:
            try:
                server.quit()
                logger.info("SMTP connection closed")
            except Exception as e:
                logger.error(f"Error closing SMTP connection: {e}")
    
    def search_unread_emails(self, mail: imaplib.IMAP4_SSL) -> List[bytes]:
        """Search for unread emails"""
        try:
            logger.info("Selecting inbox...")
            try:
                mail.select('inbox')
                logger.info("Inbox selected")
            except UnicodeDecodeError as e:
                logger.warning(f"Unicode error selecting inbox: {e}")
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
                return []
            
            if status == 'OK' and messages[0]:
                try:
                    email_ids = messages[0].split()
                    logger.info("Found %d unread emails", len(email_ids))
                    return email_ids
                except UnicodeDecodeError as e:
                    safe_error = unicodedata.normalize("NFKC", str(e)).replace("\xa0", " ")
                    logger.warning("Unicode error splitting email IDs: %s", safe_error)
                    # Try to handle the email IDs as bytes
                    try:
                        email_ids = [msg.decode('utf-8', errors='ignore') for msg in messages[0].split()]
                        logger.info("Found %d unread emails (after Unicode fix)", len(email_ids))
                        return email_ids
                    except Exception as e2:
                        safe_error2 = unicodedata.normalize("NFKC", str(e2)).replace("\xa0", " ")
                        logger.error("Failed to process email IDs: %s", safe_error2)
                        return []
            else:
                logger.info("No unread emails found")
                return []
                
        except Exception as e:
            logger.error(f"Error searching for unread emails: {e}")
            return []
    
    def fetch_email(self, mail: imaplib.IMAP4_SSL, email_id: bytes) -> Optional[bytes]:
        """Fetch email content by ID"""
        try:
            logger.info("Processing email: %s", clean_str(str(email_id)))
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
                
                return email_body
            else:
                logger.warning("No email data for %s", clean_str(str(email_id)))
                return None
                
        except Exception as e:
            logger.error("Error fetching email %s: %s", clean_str(str(email_id)), clean_str(str(e)))
            return None
    
    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read in Gmail"""
        mail = None
        try:
            mail = self.get_imap_connection()
            if not mail:
                return False
                
            mail.select('inbox')
            
            # Mark as read
            mail.store(email_id, '+FLAGS', '\\Seen')
            
            logger.info(f"Marked email {email_id} as read")
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
        finally:
            if mail:
                self.close_imap_connection(mail)
    
    async def send_email(self, to_email: str, subject: str, body: str, original_subject: str = "") -> bool:
        """Send email via SMTP (async)"""
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
            
            # Send email using async SMTP
            await aiosmtplib.send(
                msg,
                hostname='smtp.gmail.com',
                port=587,
                start_tls=True,
                username=self.gmail_user,
                password=self.gmail_app_pass,
            )
            
            logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
