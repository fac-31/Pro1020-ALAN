import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from email_client_init import initialize_email_client, shutdown_email_client
from routers.subscribers import router as subscribers_router

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
    """Initialize email client and start background polling task"""
    await initialize_email_client(app)

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shut down the background task"""
    await shutdown_email_client(app)

# --- API Endpoints ---

# Include the subscribers router
app.include_router(subscribers_router)

@app.get("/")
def home():
    return {"message": "Alan's Email Assistant Backend", "status": "running"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "email_client": "initialized" if getattr(app.state, "email_client", None) else "not_initialized"}

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