import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables from .env file
load_dotenv()

from core.config import settings
from core.exceptions import convert_to_http_exception
from email_modules.background_tasks import email_polling_task
from routers.subscribers import router as subscribers_router
from routers.rag import router as rag_router
from routers.content import router as content_router
from routers.ai import router as ai_router
from routers.fetch import router as fetch_router
from services.rag_service import RAGService
from services.digest_service import DailyDigestService
from services.ai_service import AIService
from services.email_service import EmailService
from services.content_service import ContentEvaluationService
from ai_modules.conversation_memory import ConversationMemory

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level), format=settings.log_format
)
logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---
app = FastAPI(
    title=settings.app_name, version=settings.app_version, debug=settings.debug
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
        # Initialize services with clear dependencies
        app.state.rag_engine = RAGService()
        app.state.ai_service = AIService(rag_service=app.state.rag_engine)
        app.state.conversation_memory = ConversationMemory()

        app.state.email_service = EmailService(
            rag_service=app.state.rag_engine,
            ai_service=app.state.ai_service,
            memory=app.state.conversation_memory,
        )

        app.state.content_service = ContentEvaluationService()
        app.state.digest_service = DailyDigestService(
            email_service=app.state.email_service,
            ai_service=app.state.ai_service,
            rag_service=app.state.rag_engine,
        )

        logger.info("All services initialized successfully")

        # Start background tasks
        app.state.digest_task = asyncio.create_task(
            app.state.digest_service.daily_digest_task()
        )
        logger.info("Daily digest task started")

        app.state.polling_task = asyncio.create_task(
            email_polling_task(
                email_client=app.state.email_service, rag_service=app.state.rag_engine
            )
        )
        logger.info("Email polling task started")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        http_exc = convert_to_http_exception(e)
        raise http_exc


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shut down all services"""
    try:
        # Shutdown background tasks
        if hasattr(app.state, "polling_task"):
            app.state.polling_task.cancel()
            try:
                await app.state.polling_task
            except asyncio.CancelledError:
                logger.info("Email polling task cancelled successfully")

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
app.include_router(content_router)
app.include_router(ai_router)
app.include_router(fetch_router)


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
            "Enhanced error handling",
        ],
    }


@app.get("/health")
def health_check():
    """Enhanced health check endpoint with service status"""
    try:
        services = {}

        # Check each service status
        if hasattr(app.state, "email_service"):
            services["email_service"] = app.state.email_service.get_service_status()

        if hasattr(app.state, "rag_engine"):
            services["rag_engine"] = app.state.rag_engine.get_service_status()

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
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/processed_messages")
def get_processed_messages():
    """Return the list of processed incoming email message IDs."""
    if not getattr(app.state, "email_service", None):
        raise HTTPException(status_code=503, detail="Email service is not available.")

    processed_ids = app.state.email_service.load_processed_ids()
    return JSONResponse(content={"processed_message_ids": processed_ids})


# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
