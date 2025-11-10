import asyncio
import logging
import json
import os
from datetime import datetime
from typing import List, Dict

from services.rag_service import RAGService
from services.ai_service import AIService
from email_modules.connection import EmailConnection

logger = logging.getLogger(__name__)


class DailyDigestService:
    def __init__(
        self,
        email_client: EmailConnection,
        ai_service: AIService,
        rag_engine: RAGService,
    ):
        self.email_client = email_client
        self.ai_service = ai_service
        self.rag_engine = rag_engine
        self.users_file = "users.json"

    # --------------------------
    # User management
    # --------------------------
    def load_users(self) -> List[Dict]:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, "r") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return []

    def save_users(self, users: List[Dict]):
        try:
            with open(self.users_file, "w") as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    # --------------------------
    # Internal helper for grouping chunks by article
    # --------------------------
    def _group_context_by_article(self, context_chunks: List[Dict]) -> Dict[str, Dict]:
        """
        Groups retrieved chunks by unique article (title + url).
        Expects context_chunks to be structured as:
        [
            {
                "text": "chunk text...",
                "metadata": {...}
            },
            ...
        ]
        Returns a dictionary indexed by (title, url).
        """
        grouped = {}

        for chunk in context_chunks:
            metadata = chunk.get("metadata", {})
            title = metadata.get("title")
            url = metadata.get("url")

            if not title or not url:
                # Skip malformed entries
                continue

            key = (title, url)

            if key not in grouped:
                grouped[key] = {
                    "title": title,
                    "url": url,
                    "topics": metadata.get("topics", []),
                    "source": metadata.get("source"),
                    "content": "",
                }

            # Append chunk text
            text = chunk.get("text", "")
            if text:
                grouped[key]["content"] += "\n" + text

        return grouped

    # --------------------------
    # Digest generation
    # --------------------------
    async def generate_daily_digest(
        self, user_email: str, user_interests: List[str]
    ) -> str:
        try:
            # Create digest query based on user interests
            if user_interests:
                query = f"Summarize recent news and updates about {', '.join(user_interests)}"
            else:
                query = "Summarize recent technology and AI news"

            # Retrieve chunk-level RAG context
            raw_context = self.rag_engine.get_context_for_query(
                query=query,
                user_interests=user_interests,
                n_results=20,  # more chunks to allow grouping
            )

            if not raw_context:
                logger.warning(
                    f"No RAG context available for user {user_email}. Using fallback digest."
                )
                return self._generate_fallback_digest(user_interests)

            # Group chunks into articles
            grouped_articles = self._group_context_by_article(raw_context)

            # Build simplified article-level context
            context_str = ""
            for key, article in grouped_articles.items():
                snippet = article["content"].strip()

                # Avoid overly long sections
                snippet_preview = snippet[:700]

                context_str += (
                    f"\n---\n"
                    f"TITLE: {article['title']}\n"
                    f"URL: {article['url']}\n"
                    f"TOPICS: {', '.join(article['topics']) if article['topics'] else 'None'}\n"
                    f"CONTENT_SNIPPET:\n{snippet_preview}\n"
                )

            # Prepare final prompt
            digest_prompt = f"""
Generate a personalized daily digest for a user interested in {', '.join(user_interests) if user_interests else 'technology and AI'}.

Use the following article-level summaries extracted from the knowledge base:
{context_str}

Create a digest that includes:
1. Key highlights from recent news/articles
2. Interesting developments in their areas of interest
3. Brief summaries (2–3 sentences each)
4. A warm, engaging tone

Format it as a daily briefing email that Alan would send.
"""

            # Use AIService instead of direct OpenAI client
            messages = [
                {
                    "role": "system",
                    "content": "You are Alan, creating a personalized daily digest. Be informative, engaging, and concise.",
                },
                {"role": "user", "content": digest_prompt},
            ]

            # Use AIService's wrapper to avoid token/keyword errors
            response = self.ai_service.chat(messages)

            if not response:
                return self._generate_fallback_digest(user_interests)

            digest_content = response.strip()

            logger.info(f"Generated daily digest for {user_email}")
            return digest_content

        except Exception as e:
            logger.error(f"Error generating daily digest for {user_email}: {e}")
            return self._generate_fallback_digest(user_interests)

    # --------------------------
    # Fallback
    # --------------------------
    def _generate_fallback_digest(self, user_interests: List[str]) -> str:
        interests_text = (
            ", ".join(user_interests) if user_interests else "technology and AI"
        )

        return f"""Good morning! ☕

Here's your daily briefing from Alan:

I'm currently updating my knowledge base with the latest information about {interests_text}.

While I'm working on getting you the most current updates, here are some general insights:

• Stay curious and keep learning about your interests  
• Technology is evolving rapidly — there's always something new to discover  
• Consider setting up alerts for topics you care about  

I'll have more specific updates for you soon!

Best regards,  
Alan

P.S. Feel free to email me with any specific questions you'd like me to research!
"""

    # --------------------------
    # Sending digests
    # --------------------------
    async def send_daily_digests(self):
        try:
            users = self.load_users()
            if not users:
                logger.info("No users found for daily digest")
                return

            logger.info(f"Sending daily digests to {len(users)} users")

            for user in users:
                try:
                    user_email = user.get("email")
                    user_interests = user.get("interests", [])

                    if not user_email:
                        logger.warning(f"User missing email: {user}")
                        continue

                    digest_content = await self.generate_daily_digest(
                        user_email, user_interests
                    )

                    success = self.email_client.send_email(
                        to_email=user_email,
                        subject="Alan's Daily Briefing ☕",
                        body=digest_content,
                    )

                    if success:
                        logger.info(f"Daily digest sent successfully to {user_email}")
                    else:
                        logger.error(f"Failed to send daily digest to {user_email}")

                except Exception as e:
                    logger.error(
                        f"Error sending digest to {user.get('email', 'unknown')}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"Error in send_daily_digests: {e}")

    # --------------------------
    # Scheduled task
    # --------------------------
    async def daily_digest_task(self):
        while True:
            try:
                now = datetime.now()

                # 7:00–7:05 AM window
                if now.hour == 7 and now.minute < 5:
                    logger.info("Starting daily digest task...")
                    await self.send_daily_digests()
                    await asyncio.sleep(300)  # avoid multiple runs

                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info("Daily digest task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily digest task: {e}")
                await asyncio.sleep(300)

    # --------------------------
    # User management API
    # --------------------------
    def add_user(self, email: str, interests: List[str], name: str = ""):
        try:
            users = self.load_users()

            for user in users:
                if user.get("email") == email:
                    user["interests"] = interests
                    user["name"] = name
                    self.save_users(users)
                    logger.info(f"Updated user {email}")
                    return True

            new_user = {
                "email": email,
                "interests": interests,
                "name": name,
                "added_at": datetime.now().isoformat(),
            }

            users.append(new_user)
            self.save_users(users)
            logger.info(f"Added user {email}")
            return True

        except Exception as e:
            logger.error(f"Error adding user {email}: {e}")
            return False

    def remove_user(self, email: str):
        try:
            users = self.load_users()
            updated = [u for u in users if u.get("email") != email]

            if len(updated) < len(users):
                self.save_users(updated)
                logger.info(f"Removed user {email}")
                return True

            logger.warning(f"User {email} not found")
            return False

        except Exception as e:
            logger.error(f"Error removing user {email}: {e}")
            return False

    def get_digest_stats(self) -> Dict:
        try:
            users = self.load_users()
            return {
                "total_users": len(users),
                "users_with_interests": len([u for u in users if u.get("interests")]),
                "all_interests": list(
                    set(
                        [interest for u in users for interest in u.get("interests", [])]
                    )
                ),
                "users": users,
            }
        except Exception as e:
            logger.error(f"Error getting digest stats: {e}")
            return {"error": str(e)}
