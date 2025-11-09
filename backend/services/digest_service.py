"""
Daily Digest Service - Enhanced daily digest service with better error handling
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from core.config import settings
from core.exceptions import DailyDigestError
from services.email_service import EmailService
from services.ai_service import AIService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


class DailyDigestService:
    """Enhanced daily digest service with better error handling and configuration"""

    def __init__(
        self,
        email_service: EmailService,
        ai_service: AIService,
        rag_service: RAGService,
    ):
        """Initialize daily digest service"""
        try:
            self.email_service = email_service
            self.ai_service = ai_service
            self.rag_service = rag_service
            self.users_file = "subscribers.json"  # Use consistent filename

            logger.info("Daily Digest Service initialized successfully")

        except Exception as e:
            raise DailyDigestError(
                message=f"Failed to initialize daily digest service: {str(e)}",
                error_code="DIGEST_SERVICE_INIT_FAILED",
                details={"original_error": str(e)},
            )

    def load_users(self) -> List[Dict]:
        """Load users from subscribers.json file with enhanced error handling"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, "r") as f:
                    data = json.load(f)

                    # Handle both formats: direct list or {'subscribers': [...]}
                    if isinstance(data, list):
                        users = data
                    elif isinstance(data, dict) and "subscribers" in data:
                        users = data["subscribers"]
                    else:
                        logger.warning(
                            f"Unexpected format in {self.users_file}, using empty list"
                        )
                        users = []

                    logger.info(f"Loaded {len(users)} users from {self.users_file}")
                    return users
            else:
                # File doesn't exist yet - create empty file for future use (matching subscribers router format)
                logger.debug(
                    f"No users file found at {self.users_file}, creating empty file"
                )
                with open(self.users_file, "w") as f:
                    json.dump({"subscribers": []}, f, indent=2)
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in users file: {e}")
            raise DailyDigestError(
                message="Invalid JSON format in users file",
                error_code="INVALID_USERS_FILE",
                details={"file": self.users_file},
            )
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            raise DailyDigestError(
                message=f"Failed to load users: {str(e)}",
                error_code="LOAD_USERS_FAILED",
                details={"file": self.users_file},
            )

    def save_users(self, users: List[Dict]):
        """Save users to subscribers.json file with enhanced error handling"""
        try:
            with open(self.users_file, "w") as f:
                json.dump(users, f, indent=2)
            logger.info(f"Saved {len(users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            raise DailyDigestError(
                message=f"Failed to save users: {str(e)}",
                error_code="SAVE_USERS_FAILED",
                details={"file": self.users_file, "user_count": len(users)},
            )

    async def generate_agnostic_daily_digest(self) -> dict:
        """
        Generate a clean, interest-agnostic daily digest in a structured format
        suitable for frontend rendering.
        Returns:
            dict: {
                "intro": str,
                "articles": List[Dict[str, str]],
                "closing": str
            }
        """
        try:
            results = self.rag_service.search_documents(query=".", n_results=10)

            if not results:
                return {
                    "intro": "Good morning! ☕\n\nI don’t have enough new content to generate a full digest today.",
                    "articles": [],
                    "closing": "Stay tuned for more updates!\n\nBest regards,\nAlan",
                }

            # Prepare content for LLM: full text or metadata
            # (You might send title + snippet + url for each)
            docs_for_llm = []
            seen = set()
            for r in results:
                article_id = r["metadata"].get("article_id")
                if article_id and article_id not in seen:
                    seen.add(article_id)
                    docs_for_llm.append(
                        {
                            "title": r["metadata"].get("title", "Untitled"),
                            "url": r["metadata"].get("url", ""),
                            "content": r["content"],
                        }
                    )
                if len(docs_for_llm) >= 10:
                    break

            # Create the human message
            human_message = (
                "Here are articles to summarise for today's digest:\n\n"
                + "\n\n".join(
                    [
                        f"Title: {d['title']}\nURL: {d['url']}\nContent: {d['content']}"
                        for d in docs_for_llm
                    ]
                )
                + "\n\nGenerate the structured digest according to the schema."
            )

            system_prompt = """
You are an AI assistant that generates a daily digest in a structured JSON format.

Your output MUST be a single JSON object with the following schema:
{
  "intro": "A 2-3 sentence introduction to the digest.",
  "articles": [
    {
      "title": "Article Title",
      "url": "Article URL",
      "summary": "A short summary of the article."
    }
  ],
  "closing": "A friendly closing message."
}

Do not include any text outside of the JSON object.
"""

            # Call your AI service
            response = await self.ai_service.generate_text(
                system_prompt=system_prompt,
                human_message=human_message,
                response_format="json",  # or use schema parameter if available
            )

            # Parse JSON
            digest_obj = json.loads(response)

            # Validate / fallback if needed
            if (
                "intro" not in digest_obj
                or "articles" not in digest_obj
                or "closing" not in digest_obj
            ):
                # fallback
                raise ValueError("Invalid digest format")

            return digest_obj

        except Exception as e:
            logger.error(
                f"Failed to generate structured daily digest: {e}", exc_info=True
            )
            return {
                "intro": "Good morning! ☕\n\nI ran into issues generating today’s digest, but I will have updates soon.",
                "articles": [],
                "closing": "Best regards,\nAlan",
            }

    async def _generate_big_picture_summary(self, content: str) -> str:
        """Generate a big picture summary using an LLM."""
        try:
            system_prompt = """
            You are Alan, an AI assistant. Your task is to create a "big picture" introduction to a set of articles, written like the opening of a thought-provoking newsletter or podcast episode. 
            Start with a phrase like 'This week...' and write 2–3 sentences that weave together the themes or connections between the articles in a clever, insightful way. 
            Use words like 'explore', 'unpack', or 'delve into' to set a reflective, narrative tone. 
            This is not a detailed summary—it's the hook that makes the reader curious about the deeper ideas.
            """

            human_message = (
                f"Generate a big picture summary from this content:\n\n{content}"
            )

            # Use AI service to generate the summary
            summary = await self.ai_service.generate_text(
                system_prompt=system_prompt, human_message=human_message
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to generate big picture summary: {e}")
            return "Here are the top stories for today:"

    async def _generate_digest_summary(
        self, content: str, user_interests: List[str]
    ) -> str:
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
                user_interests=user_interests,
            )

            return digest

        except Exception as e:
            logger.error(f"Failed to generate AI digest summary: {e}")
            raise DailyDigestError(
                message=f"AI digest generation failed: {str(e)}",
                error_code="AI_DIGEST_GENERATION_FAILED",
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

    async def send_daily_digest(
        self, user_email: str, user_name: str, user_interests: List[str]
    ) -> bool:
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
            digest_content = await self.generate_agnostic_daily_digest(
                user_email, user_interests
            )

            # Create email subject
            subject = f"Daily Digest from Alan - {datetime.now().strftime('%B %d, %Y')}"

            # Send email
            success = await self.email_service.send_reply(
                to_email=user_email,
                subject=subject,
                body=digest_content,
                original_subject="Daily Digest",
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
                details={"user_email": user_email, "user_name": user_name},
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
                next_run = now.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )
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
            active_users = [user for user in users if user.get("is_active", True)]

            logger.info(f"Sending daily digests to {len(active_users)} users")

            success_count = 0
            for user in active_users:
                try:
                    success = await self.send_daily_digest(
                        user_email=user["email"],
                        user_name=user["name"],
                        user_interests=user["interests"],
                    )

                    if success:
                        success_count += 1

                    # Small delay between emails to avoid rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(
                        f"Failed to send digest to {user.get('email', 'unknown')}: {e}"
                    )
                    continue

            logger.info(
                f"Daily digest completed: {success_count}/{len(active_users)} sent successfully"
            )

        except Exception as e:
            logger.error(f"Failed to send digests to all users: {e}")
            raise DailyDigestError(
                message=f"Failed to send digests to all users: {str(e)}",
                error_code="SEND_ALL_DIGESTS_FAILED",
            )

    """  """

    def get_service_status(self) -> Dict[str, any]:
        """Get daily digest service status"""
        try:
            users = self.load_users()
            active_users = [user for user in users if user.get("is_active", True)]

            return {
                "status": "healthy",
                "total_subscribers": len(users),
                "active_subscribers": len(active_users),
                "digest_hour": settings.digest_hour,
                "digest_minute": settings.digest_minute,
                "users_file": self.users_file,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "users_file": self.users_file,
            }
