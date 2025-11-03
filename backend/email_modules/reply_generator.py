import logging
from typing import List

logger = logging.getLogger(__name__)

class ReplyGenerator:
    def __init__(self):
        # Use lazy imports to avoid circular dependency
        self.ai_service = None
        self.memory = None
    
    def _get_ai_service(self):
        """Lazy import of AIService to avoid circular dependency"""
        if self.ai_service is None:
            from ai_modules.ai_service import AIService
            self.ai_service = AIService()
        return self.ai_service
    
    def _get_memory(self):
        """Lazy import of ConversationMemory to avoid circular dependency"""
        if self.memory is None:
            from ai_modules.conversation_memory import ConversationMemory
            self.memory = ConversationMemory()
        return self.memory
    
    def generate_reply(self, sender_name: str, sender_email: str, subject: str, body: str, 
                      user_interests: List[str] = None) -> str:
        """Generate an AI-powered reply using OpenAI and LangChain"""
        try:
            # Get services using lazy loading
            ai_service = self._get_ai_service()
            memory = self._get_memory()
            
            # Get conversation history for context
            conversation_history = memory.get_conversation_history(sender_email, limit=5)
            
            # Generate AI reply
            reply = ai_service.generate_email_reply(
                sender_name=sender_name,
                sender_email=sender_email,
                subject=subject,
                body=body,
                user_interests=user_interests,
                conversation_history=conversation_history
            )
            
            # Store the incoming message and reply in memory
            memory.add_message(
                sender_email=sender_email,
                message_type='incoming',
                content=f"Subject: {subject}\n\n{body}",
                subject=subject
            )
            
            memory.add_message(
                sender_email=sender_email,
                message_type='outgoing',
                content=reply,
                subject=f"Re: {subject}"
            )
            
            logger.info(f"Generated AI reply for {sender_name} ({sender_email})")
            return reply
            
        except Exception as e:
            logger.error(f"Error generating AI reply: {e}", exc_info=True)  # Add full traceback
            # Fallback to simple reply
            return self._generate_fallback_reply(sender_name, subject)

    def generate_welcome_email(self, name: str, interests: List[str]) -> str:
        """Generate a personalized welcome email for new subscribers"""
        try:
            ai_service = self._get_ai_service()
            return ai_service.generate_welcome_email(name, interests)
        except Exception as e:
            logger.error(f"Error generating welcome email: {e}")
            return self._generate_fallback_welcome(name, interests)
    
    def _generate_fallback_reply(self, sender_name: str, subject: str) -> str:
        """Generate a simple fallback reply if AI fails"""
        return f"""Hi {sender_name},

Thanks for your email about "{subject}". I'm Alan, your AI assistant, and I've received your message.

I'm currently experiencing some technical difficulties with my AI response system, but I'm working on getting back to full capacity soon! 

In the meantime, feel free to reach out if you need any help.

Best regards,
Alan"""

    def _generate_fallback_welcome(self, name: str, interests: List[str]) -> str:
        """Generate a simple fallback welcome email if AI fails"""
        return f"""Hi {name},

Welcome to Alan's newsletter! I'm thrilled to have you on board.

I see you're interested in {', '.join(interests)} - I'll make sure to share relevant insights and tips in these areas.

As your AI assistant, I'm here to help with:
- Answering questions about technology and productivity
- Providing helpful advice and suggestions
- Keeping you updated on topics you care about

Looking forward to helping you!

Best regards,
Alan"""
