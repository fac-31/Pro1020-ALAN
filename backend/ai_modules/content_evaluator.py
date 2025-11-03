"""
AI-powered content evaluator to determine if email content should be added to RAG knowledge base.
This module analyzes email content, attachments, and links to decide what's worth storing.
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tracers import LangChainTracer
from langsmith import Client

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

class ContentEvaluator:
    """
    AI-powered evaluator that determines if email content should be added to RAG knowledge base.
    Analyzes email content, attachments, and links to make intelligent decisions.
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment variables")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Initialize LangSmith tracking (optional)
        self.langsmith_client = None
        self.tracer = None
        self._setup_langsmith_tracking()
        
        # Initialize LangChain LLM with optional tracing
        callbacks = [self.tracer] if self.tracer else []
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,  # Lower temperature for more consistent evaluation
            api_key=self.openai_api_key,
            callbacks=callbacks
        )
        
        logger.info("Content Evaluator initialized successfully with LangSmith tracking")
    
    def _setup_langsmith_tracking(self):
        """Setup LangSmith tracking if API key is provided"""
        langsmith_api_key = os.getenv('LANGSMITH_API_KEY')
        langsmith_project = os.getenv('LANGSMITH_PROJECT', 'alan-content-evaluation')
        
        if langsmith_api_key:
            try:
                # Initialize LangSmith client
                self.langsmith_client = Client(api_key=langsmith_api_key)
                
                # Create tracer for LangChain
                self.tracer = LangChainTracer(
                    project_name=langsmith_project,
                    client=self.langsmith_client
                )
                
                logger.info(f"LangSmith tracking enabled for content evaluation project: {langsmith_project}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith tracking: {e}")
                self.langsmith_client = None
                self.tracer = None
        else:
            logger.info("LangSmith tracking disabled for content evaluation (LANGSMITH_API_KEY not set)")
    
    def evaluate_email_content(self, sender_email: str, subject: str, body: str,
                             attachments: List[Dict] = None,
                             links: List[str] = None) -> ContentEvaluation:
        """
        Evaluate if email content should be added to RAG knowledge base.
        
        Args:
            sender_email: Email address of sender
            subject: Email subject
            body: Email body content
            attachments: List of attachment info (filename, content_type, size)
            links: List of URLs found in email
            
        Returns:
            ContentEvaluation with decision and reasoning
        """
        try:
            # Extract content from different sources
            extracted_content = self._extract_all_content(body, attachments, links)
            
            if not extracted_content:
                return ContentEvaluation(
                    should_add=False,
                    confidence=0.0,
                    content_type="empty",
                    extracted_content="",
                    topics=[],
                    reasoning="No extractable content found",
                    source="email"
                )
            
            # Use AI to evaluate content
            evaluation = self._ai_evaluate_content(
                sender_email, subject, body, extracted_content
            )
            
            logger.info(f"Content evaluation completed: {evaluation.should_add} "
                      f"(confidence: {evaluation.confidence:.2f})")
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating email content: {e}")
            return ContentEvaluation(
                should_add=False,
                confidence=0.0,
                content_type="error",
                extracted_content="",
                topics=[],
                reasoning=f"Evaluation failed: {str(e)}",
                source="email"
            )
    
    def _extract_all_content(self, 
                           body: str, 
                           attachments: List[Dict] = None,
                           links: List[str] = None) -> str:
        """Extract and combine content from all sources"""
        content_parts = []
        
        # Add email body
        if body and body.strip():
            content_parts.append(f"Email Body:\n{body}")
        
        # Process attachments
        if attachments:
            for attachment in attachments:
                attachment_content = self._extract_attachment_content(attachment)
                if attachment_content:
                    content_parts.append(f"Attachment ({attachment.get('filename', 'unknown')}):\n{attachment_content}")
        
        # Process links
        if links:
            for link in links:
                link_content = self._extract_link_content(link)
                if link_content:
                    content_parts.append(f"Link Content ({link}):\n{link_content}")
        
        return "\n\n".join(content_parts)
    
    def _extract_attachment_content(self, attachment: Dict) -> str:
        """Extract content from email attachment"""
        try:
            filename = attachment.get('filename', '')
            content_type = attachment.get('content_type', '')
            content = attachment.get('content', '')
            
            # Handle text-based attachments
            if content_type.startswith('text/'):
                return content
            
            # Handle PDF attachments (would need additional processing)
            elif content_type == 'application/pdf':
                return f"[PDF Document: {filename}]"
            
            # Handle other document types
            elif content_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return f"[Word Document: {filename}]"
            
            # Handle images
            elif content_type.startswith('image/'):
                return f"[Image: {filename}]"
            
            else:
                return f"[File: {filename} ({content_type})]"
                
        except Exception as e:
            logger.error(f"Error extracting attachment content: {e}")
            return ""
    
    def _extract_link_content(self, url: str) -> str:
        """Extract content from web links"""
        try:
            # Simple web scraping for common content types
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                # Extract text from HTML (simplified)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                # Limit content length
                if len(text) > 2000:
                    text = text[:2000] + "..."
                
                return text
            
            elif 'application/json' in content_type:
                return f"[JSON Data from {url}]"
            
            else:
                return f"[Content from {url}]"
                
        except Exception as e:
            logger.error(f"Error extracting link content from {url}: {e}")
            return f"[Link: {url}]"
    
    def _ai_evaluate_content(self, 
                           sender_email: str,
                           subject: str, 
                           body: str,
                           extracted_content: str) -> ContentEvaluation:
        """Use AI to evaluate if content should be added to knowledge base"""
        
        system_prompt = """You are an AI content evaluator for Alan's knowledge base. 
Your job is to determine if email content should be added to the RAG knowledge base.

EVALUATION CRITERIA:
- Add content that is: factual, educational, informative, or contains useful knowledge
- Add content about: technology, AI, startups, business, science, news, research
- Add content that: provides insights, explanations, or valuable information
- Do NOT add: personal messages, spam, irrelevant content, or low-quality information

CONFIDENCE SCORING:
- 0.9-1.0: High-quality, highly relevant content
- 0.7-0.8: Good quality, relevant content
- 0.5-0.6: Moderate quality, somewhat relevant
- 0.3-0.4: Low quality, marginally relevant
- 0.0-0.2: Poor quality, not relevant

RESPONSE FORMAT:
Return a JSON response with:
{
    "should_add": boolean,
    "confidence": float (0.0-1.0),
    "content_type": string,
    "topics": [list of topics],
    "reasoning": string
}"""

        human_message = f"""
Email Details:
- From: {sender_email}
- Subject: {subject}
- Body: {body}

Extracted Content:
{extracted_content}

Evaluate this content for addition to Alan's knowledge base.
"""

        try:
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
            import json
            result = json.loads(response.content.strip())
            
            return ContentEvaluation(
                should_add=result.get('should_add', False),
                confidence=result.get('confidence', 0.0),
                content_type=result.get('content_type', 'unknown'),
                extracted_content=extracted_content,
                topics=result.get('topics', []),
                reasoning=result.get('reasoning', ''),
                source="email"
            )
            
        except Exception as e:
            logger.error(f"Error in AI evaluation: {e}")
            return ContentEvaluation(
                should_add=False,
                confidence=0.0,
                content_type="error",
                extracted_content=extracted_content,
                topics=[],
                reasoning=f"AI evaluation failed: {str(e)}",
                source="email"
            )
    
    def extract_links_from_email(self, body: str) -> List[str]:
        """Extract URLs from email body"""
        import re
        
        # Simple URL regex pattern
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, body)
        
        return list(set(urls))  # Remove duplicates
    
    def extract_attachment_info(self, email_message) -> List[Dict]:
        """Extract attachment information from email message"""
        attachments = []
        
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        content_type = part.get_content_type()
                        
                        if filename:
                            attachments.append({
                                'filename': filename,
                                'content_type': content_type,
                                'size': len(part.get_payload(decode=True) or b'')
                            })
            
            return attachments
            
        except Exception as e:
            logger.error(f"Error extracting attachment info: {e}")
            return []
