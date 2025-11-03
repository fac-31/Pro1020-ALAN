import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.exceptions import convert_to_http_exception
from core.nltk_setup import setup_nltk_data # Import the NLTK setup function
from email_client_init import initialize_email_client, shutdown_email_client
from routers.subscribers import router as subscribers_router
from routers.rag import router as rag_router
from services.rag_service import RAGService
from services.digest_service import DailyDigestService
from services.ai_service import AIService
from services.email_service import EmailService
from services.content_service import ContentEvaluationService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)
logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize all services with enhanced error handling"""
    try:
        setup_nltk_data() # Call NLTK setup at the very beginning of startup

        # Initialize email service
        app.state.email_service = EmailService()
        logger.info("Email service initialized successfully")
        
        # Initialize RAG service
        app.state.rag_service = RAGService()
        logger.info("RAG service initialized successfully")
        
        # Initialize AI service
        app.state.ai_service = AIService()
        logger.info("AI service initialized successfully")
        
        # Initialize content evaluation service
        app.state.content_service = ContentEvaluationService()
        logger.info("Content evaluation service initialized successfully")
        
        # Initialize daily digest service
        app.state.digest_service = DailyDigestService(
            email_service=app.state.email_service,
            ai_service=app.state.ai_service,
            rag_service=app.state.rag_service
        )
        logger.info("Daily digest service initialized successfully")
        
        # Start daily digest task
        app.state.digest_task = asyncio.create_task(app.state.digest_service.daily_digest_task())
        logger.info("Daily digest task started")
        
        # Initialize email client for backward compatibility
        await initialize_email_client(app)
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Convert to HTTP exception for better error handling
        http_exc = convert_to_http_exception(e)
        raise http_exc

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shut down all services"""
    try:
        # Shutdown email client
        await shutdown_email_client(app)
        
        # Shutdown daily digest task
        if hasattr(app.state, "digest_task"):
            app.state.digest_task.cancel()
            try:
                await app.state.digest_task
            except asyncio.CancelledError:
                logger.info("Daily digest task cancelled successfully")
        
        logger.info("All services shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# --- API Endpoints ---

# Include routers
app.include_router(subscribers_router)
app.include_router(rag_router)

@app.get("/")
def home():
    """Home endpoint with application information"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "features": [
            "Email-based AI assistant",
            "RAG-powered responses", 
            "Daily digest automation",
            "Document knowledge base",
            "News article ingestion",
            "AI content evaluation",
            "Email attachment processing",
            "Link content extraction",
            "LangSmith tracking",
            "Enhanced error handling"
        ]
    }

@app.get("/health")
def health_check():
    """Enhanced health check endpoint with service status"""
    try:
        services = {}
        
        # Check each service status
        if hasattr(app.state, "email_service"):
            services["email_service"] = app.state.email_service.get_service_status()
        
        if hasattr(app.state, "rag_service"):
            services["rag_service"] = app.state.rag_service.get_service_status()
        
        if hasattr(app.state, "ai_service"):
            services["ai_service"] = app.state.ai_service.get_service_status()
        
        if hasattr(app.state, "content_service"):
            services["content_service"] = app.state.content_service.get_service_status()
        
        if hasattr(app.state, "digest_service"):
            services["digest_service"] = app.state.digest_service.get_service_status()
        
        # Determine overall health
        overall_status = "healthy"
        for service_name, service_status in services.items():
            if service_status.get("status") != "healthy":
                overall_status = "degraded"
                break
        
        return {
            "status": overall_status,
            "version": settings.app_version,
            "environment": settings.environment,
            "services": services,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/processed_messages")
def get_processed_messages():
    """Return the list of processed incoming email message IDs."""
    if not getattr(app.state, "email_client", None):
        raise HTTPException(status_code=503, detail="Email service is not available.")
    
    processed_ids = app.state.email_client.load_processed_ids()
    return JSONResponse(content={"processed_message_ids": processed_ids})

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)