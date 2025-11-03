import asyncio
import logging
from email_client import EmailClient
from background_tasks import email_polling_task

logger = logging.getLogger(__name__)

async def initialize_email_client(app):
    """Initialize email client and start background polling task"""
    try:
        # Wait for RAG service to be ready (with timeout)
        rag_service = None
        max_wait = 30  # Wait up to 30 seconds for RAG service
        wait_time = 0
        while rag_service is None and wait_time < max_wait:
            rag_service = getattr(app.state, 'rag_service', None)
            if rag_service is None:
                logger.info(f"Waiting for RAG service to initialize... ({wait_time}s)")
                await asyncio.sleep(1)
                wait_time += 1
        
        if rag_service is None:
            logger.warning("RAG service not available after 30s, continuing without it")
        
        app.state.email_client = EmailClient()
        logger.info("Email client initialized successfully")
        
        # Start polling task
        app.state.polling_task = asyncio.create_task(email_polling_task(app.state.email_client, rag_service))
        logger.info("Email polling task started with RAG integration")
        
        # Verify task is running
        await asyncio.sleep(0.1)  # Give task a moment to start
        if app.state.polling_task.done():
            error = app.state.polling_task.exception()
            if error:
                logger.error(f"Email polling task failed immediately: {error}", exc_info=error)
            else:
                logger.warning("Email polling task completed immediately (unexpected)")
        else:
            logger.info("Email polling task is running successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize email client: {e}", exc_info=True)
        # Set to None so endpoints can detect the failure
        app.state.email_client = None
        app.state.polling_task = None

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
