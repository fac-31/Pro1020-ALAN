import asyncio
import logging
import json
import os
from datetime import datetime
from typing import List, Dict
from rag_engine import RAGEngine
from ai_modules.ai_service import AIService
from email_modules.connection import EmailConnection

logger = logging.getLogger(__name__)

class DailyDigestService:
    def __init__(self, email_client: EmailConnection, ai_service: AIService, rag_engine: RAGEngine):
        self.email_client = email_client
        self.ai_service = ai_service
        self.rag_engine = rag_engine
        self.users_file = 'users.json'
        
    def load_users(self) -> List[Dict]:
        """Load users from users.json file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return []
    
    def save_users(self, users: List[Dict]):
        """Save users to users.json file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    async def generate_daily_digest(self, user_email: str, user_interests: List[str]) -> str:
        """
        Generate a personalized daily digest for a user
        
        Args:
            user_email: User's email address
            user_interests: List of user's interests
            
        Returns:
            Generated digest content
        """
        try:
            # Create digest query based on user interests
            if user_interests:
                query = f"Summarize recent news and updates about {', '.join(user_interests)}"
            else:
                query = "Summarize recent technology and AI news"
            
            # Get relevant context from RAG
            context = self.rag_engine.get_context_for_query(
                query=query,
                user_interests=user_interests,
                n_results=10
            )
            
            # Generate digest using AI
            digest_prompt = f"""Generate a personalized daily digest for a user interested in {', '.join(user_interests) if user_interests else 'technology and AI'}.

Use the following information from your knowledge base:
{context}

Create a digest that includes:
1. Key highlights from recent news/articles
2. Interesting developments in their areas of interest
3. Brief summaries (2-3 sentences each)
4. A warm, engaging tone

Format it as a daily briefing email that Alan would send."""
            
            # Use AI service to generate the digest
            messages = [
                {"role": "system", "content": "You are Alan, creating a personalized daily digest. Be informative, engaging, and concise."},
                {"role": "user", "content": digest_prompt}
            ]
            
            response = self.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            digest_content = response.choices[0].message.content.strip()
            
            logger.info(f"Generated daily digest for {user_email}")
            return digest_content
            
        except Exception as e:
            logger.error(f"Error generating daily digest for {user_email}: {e}")
            return self._generate_fallback_digest(user_interests)
    
    def _generate_fallback_digest(self, user_interests: List[str]) -> str:
        """Generate a simple fallback digest if AI fails"""
        interests_text = ', '.join(user_interests) if user_interests else 'technology and AI'
        
        return f"""Good morning! ☕

Here's your daily briefing from Alan:

I'm currently updating my knowledge base with the latest information about {interests_text}. 

While I'm working on getting you the most current updates, here are some general insights:

• Stay curious and keep learning about your interests
• Technology is evolving rapidly - there's always something new to discover
• Consider setting up alerts for topics you care about

I'll have more specific updates for you soon!

Best regards,
Alan

P.S. Feel free to email me with any specific questions you'd like me to research!"""
    
    async def send_daily_digests(self):
        """Send daily digests to all users"""
        try:
            users = self.load_users()
            
            if not users:
                logger.info("No users found for daily digest")
                return
            
            logger.info(f"Sending daily digests to {len(users)} users")
            
            for user in users:
                try:
                    user_email = user.get('email')
                    user_interests = user.get('interests', [])
                    
                    if not user_email:
                        logger.warning(f"User missing email: {user}")
                        continue
                    
                    # Generate personalized digest
                    digest_content = await self.generate_daily_digest(user_email, user_interests)
                    
                    # Send email
                    success = self.email_client.send_email(
                        to_email=user_email,
                        subject="Alan's Daily Briefing ☕",
                        body=digest_content
                    )
                    
                    if success:
                        logger.info(f"Daily digest sent successfully to {user_email}")
                    else:
                        logger.error(f"Failed to send daily digest to {user_email}")
                        
                except Exception as e:
                    logger.error(f"Error sending digest to {user.get('email', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in send_daily_digests: {e}")
    
    async def daily_digest_task(self):
        """Background task to send daily digests at 7 AM"""
        while True:
            try:
                now = datetime.now()
                
                # Send at 07:00 AM
                if now.hour == 7 and now.minute < 5:
                    logger.info("Starting daily digest task...")
                    await self.send_daily_digests()
                    
                    # Wait a bit to avoid multiple sends
                    await asyncio.sleep(300)  # 5 minutes
                
                # Check every minute
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Daily digest task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily digest task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    def add_user(self, email: str, interests: List[str], name: str = ""):
        """Add a new user to the daily digest list"""
        try:
            users = self.load_users()
            
            # Check if user already exists
            for user in users:
                if user.get('email') == email:
                    # Update interests
                    user['interests'] = interests
                    user['name'] = name
                    self.save_users(users)
                    logger.info(f"Updated user {email} in daily digest list")
                    return True
            
            # Add new user
            new_user = {
                'email': email,
                'interests': interests,
                'name': name,
                'added_at': datetime.now().isoformat()
            }
            
            users.append(new_user)
            self.save_users(users)
            logger.info(f"Added user {email} to daily digest list")
            return True
            
        except Exception as e:
            logger.error(f"Error adding user {email}: {e}")
            return False
    
    def remove_user(self, email: str):
        """Remove a user from the daily digest list"""
        try:
            users = self.load_users()
            original_count = len(users)
            
            users = [user for user in users if user.get('email') != email]
            
            if len(users) < original_count:
                self.save_users(users)
                logger.info(f"Removed user {email} from daily digest list")
                return True
            else:
                logger.warning(f"User {email} not found in daily digest list")
                return False
                
        except Exception as e:
            logger.error(f"Error removing user {email}: {e}")
            return False
    
    def get_digest_stats(self) -> Dict:
        """Get statistics about daily digest users"""
        try:
            users = self.load_users()
            
            stats = {
                'total_users': len(users),
                'users_with_interests': len([u for u in users if u.get('interests')]),
                'all_interests': list(set([interest for user in users for interest in user.get('interests', [])])),
                'users': users
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting digest stats: {e}")
            return {'error': str(e)}
