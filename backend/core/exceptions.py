"""
Custom exception classes for Alan's AI Assistant
Provides structured error handling with proper HTTP status codes and error messages
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException


class AlanBaseException(Exception):
    """Base exception class for Alan's AI Assistant"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(AlanBaseException):
    """Raised when there's a configuration error"""
    pass


class EmailServiceError(AlanBaseException):
    """Raised when email service operations fail"""
    pass


class AIServiceError(AlanBaseException):
    """Raised when AI service operations fail"""
    pass


class RAGServiceError(AlanBaseException):
    """Raised when RAG service operations fail"""
    pass


class ContentEvaluationError(AlanBaseException):
    """Raised when content evaluation fails"""
    pass


class DailyDigestError(AlanBaseException):
    """Raised when daily digest operations fail"""
    pass


class ValidationError(AlanBaseException):
    """Raised when data validation fails"""
    pass


class ExternalServiceError(AlanBaseException):
    """Raised when external service calls fail"""
    pass


class RateLimitError(AlanBaseException):
    """Raised when rate limits are exceeded"""
    pass


class AuthenticationError(AlanBaseException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(AlanBaseException):
    """Raised when authorization fails"""
    pass


class NotFoundError(AlanBaseException):
    """Raised when a resource is not found"""
    pass


class ConflictError(AlanBaseException):
    """Raised when there's a conflict (e.g., duplicate resource)"""
    pass


class ServiceUnavailableError(AlanBaseException):
    """Raised when a service is unavailable"""
    pass


# HTTP Exception mappings
EXCEPTION_TO_HTTP_STATUS = {
    ConfigurationError: 500,
    EmailServiceError: 503,
    AIServiceError: 503,
    RAGServiceError: 503,
    ContentEvaluationError: 503,
    DailyDigestError: 503,
    ValidationError: 400,
    ExternalServiceError: 502,
    RateLimitError: 429,
    AuthenticationError: 401,
    AuthorizationError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    ServiceUnavailableError: 503,
}


def convert_to_http_exception(exc: Exception) -> HTTPException:
    """Convert any exception to FastAPI HTTPException"""
    if isinstance(exc, AlanBaseException):
        status_code = EXCEPTION_TO_HTTP_STATUS.get(type(exc), 500)
        
        detail = {
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    else:
        status_code = 500
        detail = {
            "error": "An unexpected internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {"original_error": str(exc)}
        }
    
    return HTTPException(status_code=status_code, detail=detail)


# Specific error constructors for common scenarios
def create_email_connection_error(message: str = "Failed to connect to email service") -> EmailServiceError:
    """Create email connection error"""
    return EmailServiceError(
        message=message,
        error_code="EMAIL_CONNECTION_FAILED",
        details={"service": "email", "operation": "connection"}
    )


def create_openai_error(message: str = "OpenAI API error") -> AIServiceError:
    """Create OpenAI API error"""
    return AIServiceError(
        message=message,
        error_code="OPENAI_API_ERROR",
        details={"service": "openai", "operation": "api_call"}
    )


def create_rag_search_error(message: str = "RAG search failed") -> RAGServiceError:
    """Create RAG search error"""
    return RAGServiceError(
        message=message,
        error_code="RAG_SEARCH_FAILED",
        details={"service": "rag", "operation": "search"}
    )


def create_content_evaluation_error(message: str = "Content evaluation failed") -> ContentEvaluationError:
    """Create content evaluation error"""
    return ContentEvaluationError(
        message=message,
        error_code="CONTENT_EVALUATION_FAILED",
        details={"service": "content_evaluator", "operation": "evaluation"}
    )


def create_validation_error(message: str, field: Optional[str] = None) -> ValidationError:
    """Create validation error"""
    details = {"field": field} if field else {}
    return ValidationError(
        message=message,
        error_code="VALIDATION_ERROR",
        details=details
    )


def create_not_found_error(resource: str, identifier: Optional[str] = None) -> NotFoundError:
    """Create not found error"""
    details = {"resource": resource}
    if identifier:
        details["identifier"] = identifier
    
    return NotFoundError(
        message=f"{resource} not found",
        error_code="NOT_FOUND",
        details=details
    )


def create_rate_limit_error(service: str, retry_after: Optional[int] = None) -> RateLimitError:
    """Create rate limit error"""
    details = {"service": service}
    if retry_after:
        details["retry_after"] = retry_after
    
    return RateLimitError(
        message=f"Rate limit exceeded for {service}",
        error_code="RATE_LIMIT_EXCEEDED",
        details=details
    )
