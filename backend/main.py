import asyncio
import logging
import os
from fastapi import FastAPI
from email_client import EmailClient, generate_reply
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
class SubscribeForm(BaseModel):
    name: str
    email: str
    interests: list[str]

@app.post("/subscribe")
async def subscribe_user(form: SubscribeForm):
    """Handle user subscription form submission"""
    global email_client
    
    if not email_client:
        logger.error("Email client not initialized")
        return
    
    # 1. Check if email already processed
    processed_ids = email_client.load_processed_ids()
    if form.email in processed_ids:
        return {"status": "already_registered"}

    # 2. Save email as processed
    email_client.save_processed_id(form.email)

    # 3. Generate welcome email
    welcome_body = f"""Hi {form.name},

Thanks for subscribing! Your interests: {', '.join(form.interests)}.

Welcome aboard!

Best,
Alan
"""
    # 4. Send email (async compatible)
    success = await email_client.send_reply(
        to_email=form.email,
        subject="Welcome to Alan's Newsletter",
        body=welcome_body
    )

    return {"status": "success" if success else "failed"}

@app.get("/processed_emails")
def get_processed_emails():

    global email_client

    if not email_client:
        logger.error("Email client not initialized")
        return

    """Return the list of processed email IDs"""
    processed_ids = email_client.load_processed_ids()
    return JSONResponse(content={"processed_ids": processed_ids})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)