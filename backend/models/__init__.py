"""
Pydantic models for Alan's AI Assistant
Provides data validation and serialization for requests and responses
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator


# Base Models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = False
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


# Email Models
class EmailInfo(BaseModel):
    """Email information model"""
    sender_email: EmailStr = Field(description="Sender email address")
    sender_name: str = Field(description="Sender name")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body content")
    message_id: Optional[str] = Field(None, description="Email message ID")
    email_id: Optional[str] = Field(None, description="Email ID")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="Email attachments")
    links: List[str] = Field(default_factory=list, description="Links found in email")


class EmailReplyRequest(BaseModel):
    """Request model for generating email replies"""
    sender_name: str = Field(description="Sender name")
    sender_email: EmailStr = Field(description="Sender email address")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")
    user_interests: Optional[List[str]] = Field(None, description="User interests")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Conversation history")


class EmailReplyResponse(BaseResponse):
    """Response model for email replies"""
    reply: str = Field(description="Generated reply content")
    sender_name: str = Field(description="Sender name")
    sender_email: EmailStr = Field(description="Sender email address")
    subject: str = Field(description="Original subject")
    confidence: Optional[float] = Field(None, description="AI confidence score")


# User Models
class UserSubscription(BaseModel):
    """User subscription model"""
    email: EmailStr = Field(description="User email address")
    name: str = Field(description="User name")
    interests: List[str] = Field(description="User interests")
    subscribed_at: datetime = Field(default_factory=datetime.now, description="Subscription date")
    is_active: bool = Field(default=True, description="Whether subscription is active")


class UserSubscriptionRequest(BaseModel):
    """Request model for user subscription"""
    email: EmailStr = Field(description="User email address")
    name: str = Field(description="User name")
    interests: List[str] = Field(description="User interests")
    
    @validator('interests')
    def validate_interests(cls, v):
        """Validate interests list"""
        if not v:
            raise ValueError('Interests list cannot be empty')
        if len(v) > 10:
            raise ValueError('Maximum 10 interests allowed')
        return v


class UserSubscriptionResponse(BaseResponse):
    """Response model for user subscription"""
    user: UserSubscription = Field(description="User subscription details")


class UserListResponse(BaseResponse):
    """Response model for user list"""
    subscribers: List[UserSubscription] = Field(description="List of subscribers")
    total_count: int = Field(description="Total number of subscribers")


# RAG Models
class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    content: str = Field(description="Document content")
    title: str = Field(description="Document title")
    topics: List[str] = Field(description="Document topics")
    
    @validator('content')
    def validate_content(cls, v):
        """Validate content"""
        if not v.strip():
            raise ValueError('Content cannot be empty')
        if len(v) > 100000:  # 100KB limit
            raise ValueError('Content too large (max 100KB)')
        return v.strip()
    
    @validator('title')
    def validate_title(cls, v):
        """Validate title"""
        if not v.strip():
            raise ValueError('Title cannot be empty')
        if len(v) > 200:
            raise ValueError('Title too long (max 200 characters)')
        return v.strip()


class NewsArticleRequest(BaseModel):
    """Request model for news article"""
    title: str = Field(description="Article title")
    content: str = Field(description="Article content")
    topics: List[str] = Field(description="Article topics")
    source: Optional[str] = Field(None, description="Article source")
    published_at: Optional[datetime] = Field(None, description="Publication date")


class SearchRequest(BaseModel):
    """Request model for RAG search"""
    query: str = Field(description="Search query")
    user_interests: Optional[List[str]] = Field(None, description="User interests for filtering")
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query"""
        if not v.strip():
            raise ValueError('Search query cannot be empty')
        if len(v) > 500:
            raise ValueError('Search query too long (max 500 characters)')
        return v.strip()


class SearchResult(BaseModel):
    """Search result model"""
    content: str = Field(description="Result content")
    score: float = Field(description="Relevance score")
    metadata: Dict[str, Any] = Field(description="Result metadata")


class SearchResponse(BaseResponse):
    """Response model for search results"""
    results: List[SearchResult] = Field(description="Search results")
    query: str = Field(description="Original query")
    total_results: int = Field(description="Total number of results")


class KnowledgeBaseStats(BaseModel):
    """Knowledge base statistics model"""
    total_documents: int = Field(description="Total number of documents")
    unique_topics: int = Field(description="Number of unique topics")
    topics: List[str] = Field(description="List of topics")
    last_updated: Optional[datetime] = Field(None, description="Last update time")


class KnowledgeBaseStatsResponse(BaseResponse):
    """Response model for knowledge base statistics"""
    stats: KnowledgeBaseStats = Field(description="Knowledge base statistics")


# Content Evaluation Models
class ContentEvaluationRequest(BaseModel):
    """Request model for content evaluation"""
    sender_email: EmailStr = Field(description="Sender email address")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Email attachments")
    links: Optional[List[str]] = Field(None, description="Links in email")


class ContentEvaluationResult(BaseModel):
    """Content evaluation result model"""
    should_add: bool = Field(description="Whether content should be added to knowledge base")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    content_type: str = Field(description="Type of content")
    topics: List[str] = Field(description="Identified topics")
    reasoning: str = Field(description="Reasoning for decision")
    source: str = Field(description="Content source")


class ContentEvaluationResponse(BaseResponse):
    """Response model for content evaluation"""
    evaluation: ContentEvaluationResult = Field(description="Evaluation result")


# Daily Digest Models
class DailyDigestSubscriptionRequest(BaseModel):
    """Request model for daily digest subscription"""
    email: EmailStr = Field(description="Subscriber email address")
    name: str = Field(description="Subscriber name")
    interests: List[str] = Field(description="Subscriber interests")
    
    @validator('interests')
    def validate_interests(cls, v):
        """Validate interests list"""
        if not v:
            raise ValueError('Interests list cannot be empty')
        return v


class DailyDigestStats(BaseModel):
    """Daily digest statistics model"""
    total_subscribers: int = Field(description="Total number of subscribers")
    active_subscribers: int = Field(description="Number of active subscribers")
    last_digest_sent: Optional[datetime] = Field(None, description="Last digest sent time")
    next_digest_scheduled: Optional[datetime] = Field(None, description="Next digest scheduled time")


class DailyDigestStatsResponse(BaseResponse):
    """Response model for daily digest statistics"""
    stats: DailyDigestStats = Field(description="Daily digest statistics")


# Health Check Models
class ServiceStatus(BaseModel):
    """Service status model"""
    name: str = Field(description="Service name")
    status: str = Field(description="Service status")
    last_check: datetime = Field(default_factory=datetime.now, description="Last status check")
    details: Optional[Dict[str, Any]] = Field(None, description="Service details")


class HealthCheckResponse(BaseResponse):
    """Health check response model"""
    status: str = Field(description="Overall system status")
    services: List[ServiceStatus] = Field(description="Individual service statuses")
    version: str = Field(description="Application version")
    environment: str = Field(description="Environment")


# Application Info Models
class ApplicationInfo(BaseModel):
    """Application information model"""
    name: str = Field(description="Application name")
    version: str = Field(description="Application version")
    status: str = Field(description="Application status")
    features: List[str] = Field(description="Available features")
    environment: str = Field(description="Environment")


class ApplicationInfoResponse(BaseResponse):
    """Response model for application information"""
    app: ApplicationInfo = Field(description="Application information")
