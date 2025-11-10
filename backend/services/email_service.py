"""
Email Service - Refactored EmailClient with better error handling and configuration
"""

import logging
from typing import List, Dict, Optional
from core.config import settings
from core.exceptions import EmailServiceError, create_email_connection_error
from email_modules.connection import EmailConnection
from email_modules.parser import EmailParser
from email_modules.message_tracker import MessageTracker
from email_modules.reply_generator import ReplyGenerator
from email_modules.utils import clean_str, setup_utf8_encoding

# Setup UTF-8 encoding
setup_utf8_encoding()

logger = logging.getLogger(__name__)


class EmailService:
    """Enhanced email service with better error handling and configuration management"""

    def __init__(self):
        """Initialize email service with configuration from settings"""
        try:
            self.gmail_user = settings.gmail_user
            self.gmail_app_pass = settings.gmail_app_pass

            if not self.gmail_user or not self.gmail_app_pass:
                raise EmailServiceError(
                    message="Gmail credentials not configured",
                    error_code="GMAIL_CREDENTIALS_MISSING",
                    details={"gmail_user_configured": bool(self.gmail_user)},
                )

            # Initialize components
            self.connection = EmailConnection(self.gmail_user, self.gmail_app_pass)
            self.parser = EmailParser()
            self.tracker = MessageTracker()
            self.reply_generator = ReplyGenerator()

            logger.info("Email service initialized successfully")

        except Exception as e:
            if isinstance(e, EmailServiceError):
                raise
            raise EmailServiceError(
                message=f"Failed to initialize email service: {str(e)}",
                error_code="EMAIL_SERVICE_INIT_FAILED",
                details={"original_error": str(e)},
            )

    def load_processed_ids(self) -> List[str]:
        """Load processed message IDs from JSON file"""
        try:
            return self.tracker.load_processed_ids()
        except Exception as e:
            logger.error(f"Failed to load processed IDs: {e}")
            return []

    def save_processed_id(self, message_id: str):
        """Save processed message ID to JSON file"""
        try:
            self.tracker.save_processed_id(message_id)
        except Exception as e:
            logger.error(f"Failed to save processed ID {message_id}: {e}")
            raise EmailServiceError(
                message=f"Failed to save processed message ID: {str(e)}",
                error_code="SAVE_PROCESSED_ID_FAILED",
                details={"message_id": message_id},
            )

    def check_unread_emails(self) -> List[Dict]:
        """Check for unread emails via IMAP with enhanced error handling"""
        emails = []
        mail = None

        try:
            mail = self.connection.get_imap_connection()
            if not mail:
                raise create_email_connection_error(
                    "Failed to establish IMAP connection"
                )

            # Search for unread emails
            email_ids = self.connection.search_unread_emails(mail)
            logger.info(f"Found {len(email_ids)} unread emails")

            # Process emails in batches to avoid overwhelming the system
            max_emails = min(len(email_ids), settings.max_emails_per_batch)

            for i, email_id in enumerate(email_ids[:max_emails]):
                try:
                    logger.info(
                        "Processing email %d/%d: %s",
                        i + 1,
                        max_emails,
                        clean_str(str(email_id)),
                    )

                    # Fetch email content
                    email_body = self.connection.fetch_email(mail, email_id)
                    if email_body:
                        # Parse email message
                        parsed_email = self.parser.parse_email_message(email_body)
                        if parsed_email:
                            parsed_email["email_id"] = email_id.decode(
                                "utf-8", errors="ignore"
                            )
                            emails.append(parsed_email)
                            logger.info(
                                "Successfully parsed email from %s",
                                clean_str(parsed_email.get("sender_email", "unknown")),
                            )
                        else:
                            logger.warning(
                                "Failed to parse email %s", clean_str(str(email_id))
                            )
                    else:
                        logger.warning("No email data for %s", clean_str(str(email_id)))

                except UnicodeDecodeError as e:
                    logger.warning(
                        "Unicode error processing email %s, skipping: %s",
                        clean_str(str(email_id)),
                        clean_str(str(e)),
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "Error processing email %s: %s",
                        clean_str(str(email_id)),
                        clean_str(str(e)),
                    )
                    continue

        except UnicodeDecodeError as e:
            logger.error(
                "Unicode decode error in email checking: %s", clean_str(str(e))
            )
            raise EmailServiceError(
                message="Unicode decode error while checking emails",
                error_code="UNICODE_DECODE_ERROR",
                details={"error": str(e)},
            )
        except EmailServiceError:
            raise  # Re-raise our custom exceptions
        except Exception as e:
            logger.error("Unexpected error checking emails: %s", clean_str(str(e)))
            raise EmailServiceError(
                message=f"Unexpected error while checking emails: {str(e)}",
                error_code="EMAIL_CHECK_UNEXPECTED_ERROR",
                details={"error": str(e)},
            )
        finally:
            if mail:
                try:
                    self.connection.close_imap_connection(mail)
                except Exception as e:
                    logger.warning(f"Error closing IMAP connection: {e}")

        logger.info("Returning %d emails", len(emails))
        return emails

    async def send_reply(
        self, to_email: str, subject: str, body: str, original_subject: str = ""
    ) -> bool:
        """Send email reply via SMTP with enhanced error handling"""
        try:
            return await self.connection.send_email(
                to_email, subject, body, original_subject
            )
        except Exception as e:
            logger.error(f"Failed to send reply to {to_email}: {e}")
            raise EmailServiceError(
                message=f"Failed to send email reply: {str(e)}",
                error_code="SEND_REPLY_FAILED",
                details={"to_email": to_email, "subject": subject},
            )

    def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read in Gmail with enhanced error handling"""
        try:
            return self.connection.mark_as_read(email_id)
        except Exception as e:
            logger.error(f"Failed to mark email {email_id} as read: {e}")
            raise EmailServiceError(
                message=f"Failed to mark email as read: {str(e)}",
                error_code="MARK_AS_READ_FAILED",
                details={"email_id": email_id},
            )

    def generate_reply(
        self, sender_name: str, sender_email: str, subject: str, body: str
    ) -> str:
        """Generate email reply using AI service"""
        try:
            return self.reply_generator.generate_reply(
                sender_name, sender_email, subject, body
            )
        except Exception as e:
            logger.error(f"Failed to generate reply for {sender_email}: {e}")
            # Return a fallback reply instead of raising an exception
            return f"Hi {sender_name},\n\nThank you for your email. I'm currently experiencing some technical difficulties with my AI system, but I'll get back to you as soon as possible.\n\nBest regards,\nAlan"

    def get_service_status(self) -> Dict[str, any]:
        """Get email service status"""
        try:
            # Test connection
            mail = self.connection.get_imap_connection()
            if mail:
                self.connection.close_imap_connection(mail)
                return {
                    "status": "healthy",
                    "gmail_user": self.gmail_user,
                    "connection_test": "successful",
                }
            else:
                return {
                    "status": "unhealthy",
                    "gmail_user": self.gmail_user,
                    "connection_test": "failed",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "gmail_user": self.gmail_user,
                "connection_test": "failed",
                "error": str(e),
            }
