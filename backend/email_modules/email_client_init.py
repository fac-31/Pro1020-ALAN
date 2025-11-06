import asyncio
import logging
from services.email_service import EmailService
from email_modules.background_tasks import email_polling_task

logger = logging.getLogger(__name__)

async def initialize_email_client(app):
    """Initialize email client and start background polling task"""
    try:
        app.state.email_client = EmailService()
        logger.info("Email client initialized successfully")
        
        # Pass the client and RAG service to the background task
        rag_service = getattr(app.state, 'rag_service', None)
        app.state.polling_task = asyncio.create_task(email_polling_task(app.state.email_client, rag_service))
        logger.info("Email polling task started with RAG integration")
        
    except Exception as e:
        logger.error(f"Failed to initialize email client: {e}")

async def shutdown_email_client(app):
    """Gracefully shut down the background task"""
    logger.info("Shutting down email polling task...")
    task = getattr(app.state, "polling_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Polling task cancelled successfully.")


