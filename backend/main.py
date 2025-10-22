import asyncio
import logging
import os
from fastapi import FastAPI
from email_client import EmailClient, generate_reply
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global email client instance
email_client = None

@app.on_event("startup")
async def startup_event():
    """Initialize email client and start background polling task"""
    global email_client
    try:
        email_client = EmailClient()
        logger.info("Email client initialized successfully")
        
        # Start background email polling task
        asyncio.create_task(email_polling_task())
        logger.info("Email polling task started")
        
    except Exception as e:
        logger.error(f"Failed to initialize email client: {e}")

async def email_polling_task():
    """Background task to poll for emails and send replies"""
    global email_client
    
    if not email_client:
        logger.error("Email client not initialized")
        return
    
    polling_interval = int(os.getenv('POLLING_INTERVAL', 300))  # Default 5 minutes
    
    while True:
        try:
            logger.info("Checking for new emails...")
            
            # Get unread emails
            unread_emails = email_client.check_unread_emails()
            logger.info(f"Found {len(unread_emails)} unread emails")
            
            # Process each email
            for email in unread_emails:
                try:
                    # Check if already processed
                    processed_ids = email_client.load_processed_ids()
                    message_id = email.get('message_id', '')
                    
                    if message_id in processed_ids:
                        logger.info(f"Email {message_id} already processed, skipping")
                        continue
                    
                    # Generate reply
                    reply_body = generate_reply(
                        email['sender_name'],
                        email['subject'],
                        email['body']
                    )
                    
                    # Send reply
                    success = await email_client.send_reply(
                        to_email=email['sender_email'],
                        subject="Alan's Reply",
                        body=reply_body,
                        original_subject=email['subject']
                    )
                    
                    if success:
                        # Mark as processed
                        email_client.save_processed_id(message_id)
                        
                        # Mark email as read in Gmail
                        email_client.mark_as_read(email['email_id'])
                        
                        logger.info(f"Successfully processed and replied to email from {email['sender_email']}")
                    else:
                        logger.error(f"Failed to send reply to {email['sender_email']}")
                        
                except Exception as e:
                    logger.error(f"Error processing email from {email.get('sender_email', 'unknown')}: {e}")
                    continue
            
            # Wait before next poll
            await asyncio.sleep(polling_interval)
            
        except Exception as e:
            logger.error(f"Error in email polling task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

@app.get("/")
def home():
    return {
        "message": "Alan's Email Assistant Backend",
        "status": "running",
        "features": ["email_polling", "auto_reply"]
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "email_client": "initialized" if email_client else "not_initialized"
    }