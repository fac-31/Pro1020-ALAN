import asyncio
import logging
import os
from email_client import EmailClient, generate_reply
from services.content_service import ContentEvaluationService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)

async def email_polling_task(email_client: EmailClient, rag_service: RAGService = None):
    """Background task to poll for emails and send replies with enhanced error handling"""
    if not email_client:
        logger.error("Email client not provided to polling task.")
        return
    
    logger.info("=" * 50)
    logger.info("Email polling task STARTED")
    logger.info(f"RAG service available: {rag_service is not None}")
    logger.info("=" * 50)
    
    # Initialize content evaluation service
    try:
        content_evaluator = ContentEvaluationService()
        logger.info("Content evaluation service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize content evaluation service: {e}", exc_info=True)
        return
    
    # Use settings from config, fallback to env var, then default to 15 minutes
    from core.config import settings
    polling_interval = int(os.getenv('POLLING_INTERVAL', settings.polling_interval))
    logger.info(f"Polling interval: {polling_interval} seconds ({polling_interval/60:.1f} minutes)")
    
    check_count = 0  # Track check count for reduced logging
    
    while True:
        try:
            check_count += 1
            # Reduce logging frequency - only log every 10th check to avoid log spam
            should_log = check_count == 1 or check_count % 10 == 0
            
            if should_log:
                logger.info(f"Checking for new emails... (check #{check_count})")
            
            unread_emails = await asyncio.to_thread(email_client.check_unread_emails)
            
            # Always log if emails found, or every 10th check
            if len(unread_emails) > 0 or should_log:
                logger.info(f"Found {len(unread_emails)} unread emails")
            
            for email in unread_emails:
                try:
                    processed_ids = email_client.load_processed_ids()
                    message_id = email.get('message_id', '')
                    
                    if message_id and message_id in processed_ids:
                        logger.info(f"Email message {message_id} already processed, skipping")
                        continue
                    
                    # Evaluate content for potential addition to knowledge base
                    evaluation = await content_evaluator.evaluate_email_content(
                        sender_email=email['sender_email'],
                        subject=email['subject'],
                        body=email['body'],
                        attachments=email.get('attachments', []),
                        links=email.get('links', [])
                    )
                    
                    # Add content to knowledge base if evaluation suggests it
                    if evaluation.should_add and evaluation.confidence > 0.6 and rag_service:
                        try:
                            # Add as user document
                            success_add = rag_service.add_user_document(
                                content=evaluation.extracted_content,
                                title=f"Email from {email['sender_name']}: {email['subject']}",
                                topics=evaluation.topics
                            )
                            
                            if success_add:
                                logger.info(f"Added email content to knowledge base: {evaluation.reasoning}")
                            else:
                                logger.warning("Failed to add email content to knowledge base")
                                
                        except Exception as e:
                            logger.error(f"Error adding email content to knowledge base: {e}")
                    
                    # Generate reply
                    reply_body = generate_reply(
                        email['sender_name'],
                        email['sender_email'],
                        email['subject'],
                        email['body']
                    )
                    
                    success = await email_client.send_reply(
                        to_email=email['sender_email'],
                        subject="Alan's Reply",
                        body=reply_body,
                        original_subject=email['subject']
                    )
                    
                    if success:
                        if message_id:
                            await asyncio.to_thread(email_client.save_processed_id, message_id)
                        await asyncio.to_thread(email_client.mark_as_read, email['email_id'])
                        logger.info(f"Successfully processed and replied to email from {email['sender_email']}")
                    else:
                        logger.error(f"Failed to send reply to {email['sender_email']}")
                        
                except Exception as e:
                    logger.error(f"Error processing email from {email.get('sender_email', 'unknown')}: {e}")
                    continue
            
            await asyncio.sleep(polling_interval)

        except asyncio.CancelledError:
            logger.info("Email polling task cancelled.")
            break
            
        except Exception as e:
            logger.error(f"Error in email polling task: {e}", exc_info=True)
            logger.info(f"Retrying in 60 seconds...")
            await asyncio.sleep(60)
