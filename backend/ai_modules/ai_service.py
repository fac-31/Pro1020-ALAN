import os
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Initialize LangChain ChatOpenAI
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=self.openai_api_key
        )
        
        # Initialize RAG engine
        self.rag_engine = RAGEngine()
        
        logger.info("AI Service initialized successfully with RAG engine")
    
    def generate_email_reply(self, sender_name: str, sender_email: str, subject: str, body: str, 
                           user_interests: List[str] = None, conversation_history: List[Dict] = None) -> str:
        """
        Generate an AI-powered email reply using OpenAI, LangChain, and RAG
        
        Args:
            sender_name: Name of the person sending the email
            sender_email: Email address of the sender
            subject: Subject line of the email
            body: Body content of the email
            user_interests: List of user interests for personalization
            conversation_history: Previous conversation context
            
        Returns:
            Generated reply text
        """
        try:
            # Extract query from email content
            query = self._extract_query_from_email(subject, body)
            
            # Get relevant context using RAG
            context = self.rag_engine.get_context_for_query(
                query=query,
                user_interests=user_interests,
                n_results=5
            )
            
            # Create system prompt for Alan's personality
            system_prompt = self._create_system_prompt(user_interests, context)
            
            # Create human message with email context
            human_message = self._create_human_message(sender_name, subject, body, conversation_history)
            
            # Generate response using LangChain
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]
            
            response = self.llm.invoke(messages)
            
            # Extract the reply content
            reply = response.content.strip()
            
            logger.info(f"Generated RAG-powered reply for {sender_name}: {reply[:100]}...")
            return reply
            
        except Exception as e:
            logger.error(f"Error generating AI reply: {e}")
            # Fallback to a simple reply if AI fails
            return self._generate_fallback_reply(sender_name, subject)
    
    def _extract_query_from_email(self, subject: str, body: str) -> str:
        """Extract a search query from email subject and body"""
        # Combine subject and body for better context
        query = f"{subject} {body}".strip()
        
        # If the email is asking for specific information, use that as the query
        if any(keyword in query.lower() for keyword in ['summarize', 'summary', 'news', 'latest', 'recent', 'today']):
            return query
        
        # If asking about specific topics, extract those
        if any(keyword in query.lower() for keyword in ['ai', 'technology', 'startup', 'finance', 'health']):
            return query
        
        # Default to the full email content
        return query
    
    def _create_system_prompt(self, user_interests: List[str] = None, context: str = "") -> str:
        """Create the system prompt that defines Alan's personality and behavior"""
        interests_context = ""
        if user_interests:
            interests_context = f"\nThe user is interested in: {', '.join(user_interests)}. Reference these interests when relevant."
        
        context_instruction = ""
        if context and context != "No relevant information found in the knowledge base.":
            context_instruction = f"\n\nIMPORTANT: Use the following information from your knowledge base to provide accurate, up-to-date responses:\n\n{context}\n\nBase your response on this information when relevant."
        
        return f"""You are Alan, an AI assistant designed to help people with their emails and daily tasks. 

Your personality:
- Friendly, helpful, and professional
- Enthusiastic about technology and productivity
- Concise but warm in your responses
- Always eager to help and learn

Your capabilities:
- Answer questions about technology, productivity, and general topics
- Provide summaries of news, articles, and documents
- Help with email organization and management
- Provide helpful suggestions and advice
- Engage in friendly conversation

Guidelines for email replies:
- Keep responses concise (2-3 paragraphs max)
- Be helpful and actionable
- Show genuine interest in the sender's message
- Use a warm, professional tone
- Sign off as "Best regards, Alan"
- If the email is asking for help, offer specific suggestions
- If it's asking for summaries or information, provide accurate details
- If it's just a greeting, respond warmly and ask how you can help

{interests_context}{context_instruction}

Remember: You're Alan, the AI assistant. Be helpful, friendly, and professional in all your responses."""
    
    def _create_human_message(self, sender_name: str, subject: str, body: str, 
                            conversation_history: List[Dict] = None) -> str:
        """Create the human message with email context"""
        context = f"""You received an email from {sender_name}.

Subject: {subject}

Email content:
{body}

Please respond to this email as Alan, the AI assistant. Be helpful, friendly, and professional."""
        
        # Add conversation history if available
        if conversation_history:
            context += "\n\nPrevious conversation context:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                context += f"- {msg.get('role', 'unknown')}: {msg.get('content', '')}\n"
        
        return context
    
    def _generate_fallback_reply(self, sender_name: str, subject: str) -> str:
        """Generate a simple fallback reply if AI fails"""
        return f"""Hi {sender_name},

Thanks for your email about "{subject}". I'm Alan, your AI assistant, and I've received your message.

I'm currently experiencing some technical difficulties with my AI response system, but I'm working on getting back to full capacity soon! 

In the meantime, feel free to reach out if you need any help.

Best regards,
Alan"""
    
    def generate_welcome_email(self, name: str, interests: List[str]) -> str:
        """Generate a personalized welcome email for new subscribers"""
        try:
            system_prompt = """You are Alan, an AI assistant. Generate a warm, personalized welcome email for a new subscriber."""
            
            human_message = f"""Generate a welcome email for {name} who is interested in: {', '.join(interests)}.

Make it:
- Warm and welcoming
- Reference their specific interests
- Explain what Alan can help with
- Keep it concise but personal
- Sign off as "Best regards, Alan" """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]
            
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating welcome email: {e}")
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
    
    def get_conversation_summary(self, conversation_history: List[Dict]) -> str:
        """Generate a summary of the conversation for context"""
        if not conversation_history:
            return "No previous conversation history."
        
        try:
            system_prompt = "You are Alan, an AI assistant. Summarize the key points from this conversation history."
            
            human_message = f"""Please summarize this conversation history:

{chr(10).join([f"- {msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in conversation_history])}

Keep the summary concise and focus on the main topics discussed."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]
            
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {e}")
            return "Unable to generate conversation summary."
