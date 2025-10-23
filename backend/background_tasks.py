import asyncio
import logging
import os
from email_client import EmailClient, generate_reply

logger = logging.getLogger(__name__)

async def email_polling_task(email_client: EmailClient):
    """Background task to poll for emails and send replies"""
    if not email_client:
        logger.error("Email client not provided to polling task.")
        return
    
    polling_interval = int(os.getenv('POLLING_INTERVAL', 300))
    
    while True:
        try:
            logger.info("Checking for new emails...")
            unread_emails = await asyncio.to_thread(email_client.check_unread_emails)
            logger.info(f"Found {len(unread_emails)} unread emails")
            
            for email in unread_emails:
                try:
                    processed_ids = email_client.load_processed_ids()
                    message_id = email.get('message_id', '')
                    
                    if message_id and message_id in processed_ids:
                        logger.info(f"Email message {message_id} already processed, skipping")
                        continue
                    
                    reply_body = generate_reply(
                        email['sender_name'],
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
            logger.error(f"Error in email polling task: {e}")
            await asyncio.sleep(60)
