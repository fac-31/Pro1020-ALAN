import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from email_client_init import initialize_email_client, shutdown_email_client
from routers.subscribers import router as subscribers_router
from routers.rag import router as rag_router
from rag_engine import RAGEngine
from daily_digest import DailyDigestService
from ai_modules.ai_service import AIService
from email_modules.connection import EmailConnection

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize all services"""
    try:
        # Initialize email client
        await initialize_email_client(app)
        
        # Initialize RAG engine
        app.state.rag_engine = RAGEngine()
        logger.info("RAG engine initialized successfully")
        
        # Initialize AI service
        app.state.ai_service = AIService()
        logger.info("AI service initialized successfully")
        
        # Initialize daily digest service
        app.state.digest_service = DailyDigestService(
            email_client=app.state.email_client.connection,
            ai_service=app.state.ai_service,
            rag_engine=app.state.rag_engine
        )
        logger.info("Daily digest service initialized successfully")
        
        # Start daily digest task
        app.state.digest_task = asyncio.create_task(app.state.digest_service.daily_digest_task())
        logger.info("Daily digest task started")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")

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
    return {
        "message": "Alan's AI Assistant Backend", 
        "status": "running",
        "features": [
            "Email-based AI assistant",
            "RAG-powered responses", 
            "Daily digest automation",
            "Document knowledge base",
            "News article ingestion",
            "AI content evaluation",
            "Email attachment processing",
            "Link content extraction"
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "email_client": "initialized" if getattr(app.state, "email_client", None) else "not_initialized",
        "rag_engine": "initialized" if getattr(app.state, "rag_engine", None) else "not_initialized",
        "ai_service": "initialized" if getattr(app.state, "ai_service", None) else "not_initialized",
        "digest_service": "initialized" if getattr(app.state, "digest_service", None) else "not_initialized",
        "content_evaluation": "enabled",
        "attachment_processing": "enabled",
        "link_extraction": "enabled"
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