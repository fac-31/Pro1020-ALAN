"""
Content Evaluation Service - Enhanced content evaluation with better error handling
"""

import logging
import json
import requests
from typing import Dict, List
from dataclasses import dataclass
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tracers import LangChainTracer
from langsmith import Client
from bs4 import BeautifulSoup

from core.config import settings
from core.exceptions import ContentEvaluationError, create_content_evaluation_error

logger = logging.getLogger(__name__)


@dataclass
class ContentEvaluation:
    """Result of content evaluation"""
    should_add: bool
    confidence: float
    content_type: str
    extracted_content: str
    topics: List[str]
    reasoning: str
    source: str


class ContentEvaluationService:
    """
    Enhanced AI-powered evaluator that determines if email content should be added to RAG knowledge base.
    Analyzes email content, attachments, and links to make intelligent decisions.
    """
    
    def __init__(self):
        """Initialize content evaluation service with configuration from settings"""
        try:
            self.openai_api_key = settings.openai_api_key
            if not self.openai_api_key:
                raise ContentEvaluationError(
                    message="OpenAI API key not configured",
                    error_code="OPENAI_API_KEY_MISSING"
                )
            
            # Initialize OpenAI client
            self.client = OpenAI(api_key=self.openai_api_key)
            
            # Initialize LangSmith tracking (optional)
            self.langsmith_client = None
            self.tracer = None
            self._setup_langsmith_tracking()
            
            # Initialize LangChain LLM with optional tracing
            callbacks = [self.tracer] if self.tracer else []
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                api_key=self.openai_api_key,
                callbacks=callbacks
            )
            
            logger.info("Content Evaluation Service initialized successfully with LangSmith tracking")
            
        except ContentEvaluationError:
            raise
        except Exception as e:
            raise ContentEvaluationError(
                message=f"Failed to initialize content evaluation service: {str(e)}",
                error_code="CONTENT_EVALUATION_INIT_FAILED",
                details={"original_error": str(e)}
            )
    
    def _setup_langsmith_tracking(self):
        """Setup LangSmith tracking if API key is provided"""
        if settings.langsmith_api_key:
            try:
                # Initialize LangSmith client
                self.langsmith_client = Client(api_key=settings.langsmith_api_key)
                
                # Create tracer for LangChain
                project_name = settings.langsmith_project_evaluation or f"{settings.langsmith_project}-evaluation"
                self.tracer = LangChainTracer(
                    project_name=project_name,
                    client=self.langsmith_client
                )
                
                logger.info(f"LangSmith tracking enabled for content evaluation project: {project_name}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith tracking: {e}")
                self.langsmith_client = None
                self.tracer = None
        else:
            logger.info("LangSmith tracking disabled for content evaluation (LANGSMITH_API_KEY not set)")
    
    async def evaluate_email_content(
        self,
        sender_email: str,
        subject: str,
        body: str,
        attachments: List[Dict] = None,
        links: List[str] = None
    ) -> ContentEvaluation:
        """
        Evaluate email content to determine if it should be added to knowledge base
        
        Args:
            sender_email: Email sender address
            subject: Email subject
            body: Email body content
            attachments: List of email attachments
            links: List of URLs found in email
            
        Returns:
            ContentEvaluation result
        """
        try:
            if not body.strip() and not attachments and not links:
                return ContentEvaluation(
                    should_add=False,
                    confidence=1.0,
                    content_type="empty",
                    extracted_content="",
                    topics=[],
                    reasoning="No content to evaluate",
                    source="empty_content"
                )
            
            # Extract content from different sources
            extracted_content = ""
            content_sources = []
            
            # Process email body
            if body.strip():
                extracted_content += f"Email Body: {body.strip()}\n\n"
                content_sources.append("email_body")
            
            # Process attachments
            if attachments:
                attachment_content = self._extract_attachment_content(attachments)
                if attachment_content:
                    extracted_content += f"Attachments: {attachment_content}\n\n"
                    content_sources.append("attachments")
            
            # Process links
            if links:
                link_content = await self._extract_link_content(links)
                if link_content:
                    extracted_content += f"Links: {link_content}\n\n"
                    content_sources.append("links")
            
            if not extracted_content.strip():
                return ContentEvaluation(
                    should_add=False,
                    confidence=1.0,
                    content_type="no_extractable_content",
                    extracted_content="",
                    topics=[],
                    reasoning="No extractable content found",
                    source="no_content"
                )
            
            # Call AI evaluation
            evaluation_result = self._call_ai_evaluation(
                sender_email, subject, extracted_content, attachments or [], links or []
            )
            
            # Create ContentEvaluation object
            return ContentEvaluation(
                should_add=evaluation_result.get("should_add", False),
                confidence=evaluation_result.get("confidence", 0.0),
                content_type=evaluation_result.get("content_type", "unknown"),
                extracted_content=evaluation_result.get("extracted_content", extracted_content),
                topics=evaluation_result.get("topics", []),
                reasoning=evaluation_result.get("reasoning", ""),
                source=evaluation_result.get("source", "ai_evaluation")
            )
            
        except Exception as e:
            logger.error(f"Error evaluating email content: {e}")
            raise create_content_evaluation_error(f"Content evaluation failed: {str(e)}")
    
    def _extract_attachment_content(self, attachments: List[Dict]) -> str:
        """Extract content from email attachments"""
        try:
            content_parts = []
            
            for attachment in attachments:
                filename = attachment.get('filename', 'unknown')
                content_type = attachment.get('content_type', '')
                content = attachment.get('content')
                
                if content:
                    if content_type.startswith('text/'):
                        try:
                            # Try to decode text content
                            if isinstance(content, bytes):
                                text_content = content.decode('utf-8', errors='ignore')
                            else:
                                text_content = str(content)
                            
                            content_parts.append(f"File: {filename}\nContent: {text_content[:500]}")
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract text from attachment {filename}: {e}")
                            content_parts.append(f"File: {filename} (text extraction failed)")
                    
                    else:
                        content_parts.append(f"File: {filename} (type: {content_type})")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error extracting attachment content: {e}")
            return ""
    
    async def _extract_link_content(self, links: List[str]) -> str:
        """Extract content from URLs found in email"""
        try:
            content_parts = []
            
            for link in links[:3]:  # Limit to first 3 links
                try:
                    response = requests.get(link, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; Alan AI Assistant)'
                    })
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Extract title
                        title = soup.find('title')
                        title_text = title.get_text().strip() if title else "No title"
                        
                        # Extract main content (try different selectors)
                        content_selectors = ['article', 'main', '.content', '#content', 'p']
                        main_content = ""
                        
                        for selector in content_selectors:
                            elements = soup.select(selector)
                            if elements:
                                main_content = " ".join([elem.get_text().strip() for elem in elements[:3]])
                                break
                        
                        if main_content:
                            content_parts.append(f"URL: {link}\nTitle: {title_text}\nContent: {main_content[:300]}")
                        else:
                            content_parts.append(f"URL: {link}\nTitle: {title_text}")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract content from link {link}: {e}")
                    content_parts.append(f"URL: {link} (content extraction failed)")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error extracting link content: {e}")
            return ""
    
    def _call_ai_evaluation(self, sender_email: str, subject: str, extracted_content: str, 
                           attachments: List[Dict], links: List[str]) -> Dict:
        """Call the AI model to evaluate content with enhanced error handling"""
        try:
            system_prompt = """
            You are an AI assistant designed to evaluate content for a RAG knowledge base.
            Your task is to determine if the provided content (from an email, attachment, or link) is valuable
            for a knowledge base that helps an AI assistant answer questions about technology, AI, research, and business.
            
            Respond with a JSON object containing:
            - "should_add": boolean (true if content is valuable, false otherwise)
            - "confidence": float (0.0 to 1.0, how confident you are in your decision)
            - "content_type": string (e.g., "email_body", "attachment", "web_page")
            - "extracted_content": string (the cleaned, summarized, or key parts of the content to add)
            - "topics": list of strings (relevant topics like "AI", "technology", "research", "business", "startup")
            - "reasoning": string (brief explanation for your decision)
            
            Focus on factual, informative, or educational content. Avoid personal conversations, spam, or irrelevant data.
            If the content is too short, generic, or lacks substance, set "should_add" to false.
            """
            
            human_message = f"""
Sender: {sender_email}
Subject: {subject}
Content:
{extracted_content}

Attachments count: {len(attachments) if attachments else 0}
Links count: {len(links) if links else 0}

Evaluate this content for addition to Alan's knowledge base.
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message)
            ]
            
            # Add metadata for LangSmith tracking
            run_metadata = {
                "sender_email": sender_email,
                "subject": subject,
                "content_length": len(extracted_content),
                "attachments_count": len(attachments) if attachments else 0,
                "links_count": len(links) if links else 0,
                "evaluation_type": "content_evaluation"
            }
            
            # Generate evaluation with metadata
            response = self.llm.invoke(
                messages,
                metadata=run_metadata,
                tags=["content_evaluation", "rag_decision"]
            )
            
            # Parse JSON response
            result = json.loads(response.content.strip())
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI evaluation response: {e}")
            return {
                "should_add": False,
                "confidence": 0.0,
                "content_type": "unknown",
                "extracted_content": extracted_content,
                "topics": [],
                "reasoning": f"AI response parsing failed: {e}",
                "source": "AI_Parse_Error"
            }
        except Exception as e:
            logger.error(f"Error in AI evaluation: {e}")
            return {
                "should_add": False,
                "confidence": 0.0,
                "content_type": "unknown",
                "extracted_content": extracted_content,
                "topics": [],
                "reasoning": f"AI evaluation failed: {e}",
                "source": "AI_Error"
            }
    
    def get_service_status(self) -> Dict[str, any]:
        """Get content evaluation service status"""
        try:
            return {
                "status": "healthy",
                "openai_model": settings.openai_model,
                "langsmith_enabled": self.tracer is not None,
                "evaluation_temperature": 0.3
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "openai_model": settings.openai_model
            }
