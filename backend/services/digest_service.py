"""
Daily Digest Service - Enhanced daily digest service with better error handling
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict

from core.config import settings
from core.exceptions import DailyDigestError
from services.email_service import EmailService
from services.ai_service import AIService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


class DailyDigestService:
    """Enhanced daily digest service with better error handling and configuration"""
    
    def __init__(self, email_service: EmailService, ai_service: AIService, rag_service: RAGService):
        """Initialize daily digest service"""
        try:
            self.email_service = email_service
            self.ai_service = ai_service
            self.rag_service = rag_service
            self.users_file = 'subscribers.json'  # Use consistent filename
            
            logger.info("Daily Digest Service initialized successfully")
            
        except Exception as e:
            raise DailyDigestError(
                message=f"Failed to initialize daily digest service: {str(e)}",
                error_code="DIGEST_SERVICE_INIT_FAILED",
                details={"original_error": str(e)}
            )
    
    def load_users(self) -> List[Dict]:
        """Load users from subscribers.json file with enhanced error handling"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users = json.load(f)
                    logger.info(f"Loaded {len(users)} users from {self.users_file}")
                    return users
            else:
                logger.info(f"No users file found at {self.users_file}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in users file: {e}")
            raise DailyDigestError(
                message="Invalid JSON format in users file",
                error_code="INVALID_USERS_FILE",
                details={"file": self.users_file}
            )
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            raise DailyDigestError(
                message=f"Failed to load users: {str(e)}",
                error_code="LOAD_USERS_FAILED",
                details={"file": self.users_file}
            )
    
    def save_users(self, users: List[Dict]):
        """Save users to subscribers.json file with enhanced error handling"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            logger.info(f"Saved {len(users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            raise DailyDigestError(
                message=f"Failed to save users: {str(e)}",
                error_code="SAVE_USERS_FAILED",
                details={"file": self.users_file, "user_count": len(users)}
            )
    
    async def generate_daily_digest(self, user_email: str, user_interests: List[str]) -> str:
        """
        Generate a personalized daily digest for a user with enhanced error handling
        
        Args:
            user_email: User's email address
            user_interests: List of user's interests
            
        Returns:
            Generated digest content
        """
        try:
            if not user_interests:
                raise DailyDigestError(
                    message="User interests are required for digest generation",
                    error_code="MISSING_USER_INTERESTS",
                    details={"user_email": user_email}
                )
            
            # Get relevant content from RAG based on user interests
            digest_content = []
            
            for interest in user_interests:
                try:
                    # Search for content related to this interest
                    results = self.rag_service.search_documents(interest, n_results=2)
                    
                    for result in results:
                        content = result['content'][:300]  # Limit content length
                        digest_content.append(f"📚 {interest.title()}: {content}")
                        
                except Exception as e:
                    logger.warning(f"Failed to get content for interest '{interest}': {e}")
                    continue
            
            # Generate AI-powered digest summary
            if digest_content:
                content_text = "\n\n".join(digest_content)
                
                try:
                    digest_summary = await self._generate_digest_summary(content_text, user_interests)
                    return digest_summary
                except Exception as e:
                    logger.error(f"Failed to generate AI digest summary: {e}")
                    # Fallback to basic digest
                    return self._create_fallback_digest(content_text, user_interests)
            else:
                return self._create_empty_digest(user_interests)
                
        except DailyDigestError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate daily digest for {user_email}: {e}")
            raise DailyDigestError(
                message=f"Failed to generate daily digest: {str(e)}",
                error_code="DIGEST_GENERATION_FAILED",
                details={"user_email": user_email, "interests": user_interests}
            )
    
    async def _generate_digest_summary(self, content: str, user_interests: List[str]) -> str:
        """Generate AI-powered digest summary"""
        try:
            system_prompt = f"""
            You are Alan, an AI assistant creating a personalized daily digest.
            
            User's interests: {', '.join(user_interests)}
            
            Create a concise, engaging daily digest that:
            1. Summarizes the key information from the provided content
            2. Highlights the most relevant points for the user's interests
            3. Uses a friendly, professional tone
            4. Includes actionable insights when possible
            5. Keeps it concise but informative
            
            Format it as a well-structured email digest.
            """
            
            human_message = f"Create a daily digest from this content:\n\n{content}"
            
            # Use AI service to generate digest
            digest = self.ai_service.generate_email_reply(
                sender_name="Alan",
                sender_email="alan@assistant.com",
                subject="Daily Digest",
                body=human_message,
                user_interests=user_interests
            )
            
            return digest
            
        except Exception as e:
            logger.error(f"Failed to generate AI digest summary: {e}")
            raise DailyDigestError(
                message=f"AI digest generation failed: {str(e)}",
                error_code="AI_DIGEST_GENERATION_FAILED"
            )
    
    def _create_fallback_digest(self, content: str, user_interests: List[str]) -> str:
        """Create a fallback digest when AI generation fails"""
        return f"""
        Good morning! Here's your personalized daily digest from Alan:
        
        Based on your interests in {', '.join(user_interests)}, here's what I found:
        
        {content}
        
        Have a great day!
        
        Best regards,
        Alan
        """
    
    def _create_empty_digest(self, user_interests: List[str]) -> str:
        """Create digest when no content is available"""
        return f"""
        Good morning! Here's your daily digest from Alan:
        
        I didn't find any new content related to your interests in {', '.join(user_interests)} today.
        
        Don't worry - I'm always learning and will have more personalized content for you soon!
        
        Best regards,
        Alan
        """
    
    async def send_daily_digest(self, user_email: str, user_name: str, user_interests: List[str]) -> bool:
        """
        Send daily digest to a user with enhanced error handling
        
        Args:
            user_email: User's email address
            user_name: User's name
            user_interests: List of user's interests
            
        Returns:
            True if digest was sent successfully, False otherwise
        """
        try:
            # Generate digest content
            digest_content = await self.generate_daily_digest(user_email, user_interests)
            
            # Create email subject
            subject = f"Daily Digest from Alan - {datetime.now().strftime('%B %d, %Y')}"
            
            # Send email
            success = await self.email_service.send_reply(
                to_email=user_email,
                subject=subject,
                body=digest_content,
                original_subject="Daily Digest"
            )
            
            if success:
                logger.info(f"Successfully sent daily digest to {user_email}")
            else:
                logger.error(f"Failed to send daily digest to {user_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily digest to {user_email}: {e}")
            raise DailyDigestError(
                message=f"Failed to send daily digest: {str(e)}",
                error_code="SEND_DIGEST_FAILED",
                details={"user_email": user_email, "user_name": user_name}
            )
    
    async def daily_digest_task(self):
        """
        Background task to send daily digests to all subscribers
        Runs at the configured time each day
        """
        logger.info("Daily digest task started")
        
        while True:
            try:
                # Get current time
                now = datetime.now()
                target_hour = settings.digest_hour
                target_minute = settings.digest_minute
                
                # Calculate next run time
                next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                # Calculate sleep time
                sleep_seconds = (next_run - now).total_seconds()
                logger.info(f"Next daily digest scheduled for {next_run}")
                
                # Sleep until next run time
                await asyncio.sleep(sleep_seconds)
                
                # Send digests to all users
                await self._send_digests_to_all_users()
                
            except asyncio.CancelledError:
                logger.info("Daily digest task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily digest task: {e}")
                # Sleep for 1 hour before retrying
                await asyncio.sleep(3600)
    
    async def _send_digests_to_all_users(self):
        """Send digests to all subscribed users"""
        try:
            users = self.load_users()
            active_users = [user for user in users if user.get('is_active', True)]
            
            logger.info(f"Sending daily digests to {len(active_users)} users")
            
            success_count = 0
            for user in active_users:
                try:
                    success = await self.send_daily_digest(
                        user_email=user['email'],
                        user_name=user['name'],
                        user_interests=user['interests']
                    )
                    
                    if success:
                        success_count += 1
                    
                    # Small delay between emails to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to send digest to {user.get('email', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Daily digest completed: {success_count}/{len(active_users)} sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send digests to all users: {e}")
            raise DailyDigestError(
                message=f"Failed to send digests to all users: {str(e)}",
                error_code="SEND_ALL_DIGESTS_FAILED"
            )
    
    def get_service_status(self) -> Dict[str, any]:
        """Get daily digest service status"""
        try:
            users = self.load_users()
            active_users = [user for user in users if user.get('is_active', True)]
            
            return {
                "status": "healthy",
                "total_subscribers": len(users),
                "active_subscribers": len(active_users),
                "digest_hour": settings.digest_hour,
                "digest_minute": settings.digest_minute,
                "users_file": self.users_file
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "users_file": self.users_file
            }
