"""
AI Service - Enhanced AI service with better error handling and configuration
"""

import logging
from typing import Dict, List, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tracers import LangChainTracer
from langsmith import Client

from core.config import settings
from core.exceptions import AIServiceError, create_openai_error
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


class AIService:
    """Enhanced AI service with better error handling and configuration management"""
    
    def __init__(self, rag_service: RAGService):
        """Initialize AI service with configuration from settings"""
        try:
            self.openai_api_key = settings.openai_api_key
            if not self.openai_api_key:
                raise AIServiceError(
                    message="OpenAI API key not configured",
                    error_code="OPENAI_API_KEY_MISSING"
                )
            
            # Initialize OpenAI client
            self.client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize LangSmith tracking (optional)
            self.langsmith_client = None
            self.tracer = None
            self._setup_langsmith_tracking()
            
            # Initialize LangChain ChatOpenAI with optional tracing
            callbacks = [self.tracer] if self.tracer else []
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                api_key=self.openai_api_key,
                callbacks=callbacks
            )
            
            # Use the provided RAG service
            self.rag_engine = rag_service
            
            logger.info("AI Service initialized successfully")
            
        except AIServiceError:
            raise
        except Exception as e:
            raise AIServiceError(
                message=f"Failed to initialize AI service: {str(e)}",
                error_code="AI_SERVICE_INIT_FAILED",
                details={"original_error": str(e)}
            )
    
    def _setup_langsmith_tracking(self):
        """Setup LangSmith tracking if API key is provided"""
        if settings.langsmith_api_key:
            try:
                # Initialize LangSmith client
                self.langsmith_client = Client(api_key=settings.langsmith_api_key)
                
                # Create tracer for LangChain
                project_name = settings.langsmith_project_email or settings.langsmith_project
                self.tracer = LangChainTracer(
                    project_name=project_name,
                    client=self.langsmith_client
                )
                
                logger.info(f"LangSmith tracking enabled for project: {project_name}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith tracking: {e}")
                self.langsmith_client = None
                self.tracer = None
        else:
            logger.info("LangSmith tracking disabled (LANGSMITH_API_KEY not set)")
    
    def generate_email_reply(
        self, 
        sender_name: str, 
        sender_email: str, 
        subject: str, 
        body: str, 
        user_interests: List[str] = None, 
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Generate an AI-powered email reply using OpenAI, LangChain, and RAG
        """
        try:
            # Extract query from email for RAG context
            query = self._extract_query_from_email(subject, body)
            
            # Get relevant context from RAG
            context = self.rag_engine.get_context_for_query(query, user_interests)
            
            # Create system prompt
            system_prompt = self._create_system_prompt(user_interests, context)
            
            # Create human message
            human_message = self._create_human_message(
                sender_name, sender_email, subject, body, conversation_history
            )
            
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]
            
            # Add metadata for LangSmith tracking
            run_metadata = {
                "sender_name": sender_name,
                "sender_email": sender_email,
                "subject": subject,
                "user_interests": user_interests or [],
                "context_documents": len(context) if context else 0,
                "conversation_history_length": len(conversation_history) if conversation_history else 0
            }
            
            # Generate response with metadata
            response = self.llm.invoke(
                messages,
                metadata=run_metadata,
                tags=["email_reply", "rag_powered"]
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI reply: {e}")
            raise create_openai_error(f"Failed to generate email reply: {str(e)}")
    
    def generate_welcome_email(self, user_name: str, user_email: str, interests: List[str]) -> str:
        """Generate a personalized welcome email"""
        try:
            system_prompt = f"""
            You are Alan, an AI assistant. Generate a warm, personalized welcome email for a new subscriber.
            
            User Details:
            - Name: {user_name}
            - Email: {user_email}
            - Interests: {', '.join(interests)}
            
            Guidelines:
            - Be friendly and professional
            - Acknowledge their interests
            - Explain what they can expect from Alan
            - Keep it concise but engaging
            - Sign as "Alan"
            """
            
            human_message = f"Generate a welcome email for {user_name} who is interested in {', '.join(interests)}."
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]
            
            response = self.llm.invoke(messages, tags=["welcome_email"])
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating welcome email: {e}")
            raise create_openai_error(f"Failed to generate welcome email: {str(e)}")

    def generate_tags(self, text_content: str) -> List[str]:
        """
        Analyzes text and returns a list of relevant tags.
        """
        MAX_CHARS = 100
        text_to_send = text_content[:MAX_CHARS]

        try:
            system_prompt = (
                "You are an expert at analyzing text and extracting relevant tags. "
                "Respond ONLY with a comma-separated list of 1–5 tags."
)
            human_message = f"Generate tags for the following text:\n\n{text_to_send}"

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]

            # Excluded the metadata for langsmith (BUG)
            response = self.llm.invoke(messages)

            
            tags = [tag.strip() for tag in response.content.split(',')]
            return tags

        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            raise create_openai_error(f"Failed to generate tags: {str(e)}")
    
    def _extract_query_from_email(self, subject: str, body: str) -> str:
        """Extract search query from email content"""
        # Combine subject and body for better context
        query = f"{subject} {body}".strip()
        
        # Limit query length for better search results
        if len(query) > 200:
            query = query[:200] + "..."
        
        return query
    
    def _create_system_prompt(self, user_interests: List[str] = None, context: str = None) -> str:
        """Create system prompt for AI"""
        base_prompt = """
        You are Alan, an AI assistant designed to help users with their questions and tasks.
        You are knowledgeable, helpful, and professional in your responses.
        
        Guidelines:
        - Be concise but comprehensive
        - Use a friendly, professional tone
        - Provide actionable advice when possible
        - If you don't know something, admit it and suggest alternatives
        - Always be helpful and supportive
        """
        
        if user_interests:
            interests_text = ", ".join(user_interests)
            base_prompt += f"\n\nUser's interests: {interests_text}"
        
        if context and context != "No relevant information found in the knowledge base.":
            base_prompt += f"\n\nRelevant context from knowledge base:\n{context}"
        
        return base_prompt
    
    def _create_human_message(
        self, 
        sender_name: str, 
        sender_email: str, 
        subject: str, 
        body: str, 
        conversation_history: List[Dict] = None
    ) -> str:
        """Create human message for AI"""
        message = f"""
        Email from: {sender_name} ({sender_email})
        Subject: {subject}
        
        Message:
        {body}
        """
        
        if conversation_history:
            message += "\n\nPrevious conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages
                message += f"- {msg.get('role', 'user')}: {msg.get('content', '')}\n"
        
        return message.strip()
    
    def get_service_status(self) -> Dict[str, any]:
        """Get AI service status"""
        try:
            # Test OpenAI API with a simple request
            test_response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            return {
                "status": "healthy",
                "openai_model": settings.openai_model,
                "langsmith_enabled": self.tracer is not None,
                "rag_engine_status": "connected" if self.rag_engine else "not_loaded",
                "api_test": "successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "openai_model": settings.openai_model,
                "langsmith_enabled": self.tracer is not None,
                "rag_engine_status": "connected" if self.rag_engine else "not_loaded",
                "api_test": "failed",
                "error": str(e)
            }