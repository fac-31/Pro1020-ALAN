import os
import json
import logging
import fitz  # PyMuPDF
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Optional
from services.rag_service import RAGService
from email_modules.daily_digest import DailyDigestService
from services.ai_service import AIService

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config import settings

# --- Router Setup ---
router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class DocumentUpload(BaseModel):
    content: str
    filename: str
    topics: List[str] = []

class NewsArticle(BaseModel):
    title: str
    content: str
    url: str = ""
    topics: List[str] = []

class QueryRequest(BaseModel):
    query: str
    user_interests: List[str] = []
    n_results: int = 5

class UserDigest(BaseModel):
    email: str
    interests: List[str]
    name: str = ""

# --- Dependency Injection ---
def get_rag_engine(request: Request) -> RAGService:
    """Dependency to get the RAG engine from application state."""
    if not hasattr(request.app.state, 'rag_engine') or not request.app.state.rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine is not available.")
    return request.app.state.rag_engine

def get_ai_service(request: Request) -> AIService:
    """Dependency to get the AI service from application state."""
    if not hasattr(request.app.state, 'ai_service') or not request.app.state.ai_service:
        raise HTTPException(status_code=503, detail="AI service is not available.")
    return request.app.state.ai_service

def get_digest_service(request: Request) -> DailyDigestService:
    """Dependency to get the daily digest service from application state."""
    if not hasattr(request.app.state, 'digest_service') or not request.app.state.digest_service:
        raise HTTPException(status_code=503, detail="Daily digest service is not available.")
    return request.app.state.digest_service

# --- API Endpoints ---

@router.post("/documents/upload", tags=["Documents"])
async def upload_document(
    document: DocumentUpload,
    rag_engine: RAGService = Depends(get_rag_engine)
):
    """Upload a document to Alan's knowledge base"""
    try:
        success = rag_engine.add_user_document(
            content=document.content,
            filename=document.filename,
            user_email="system",  # Could be enhanced to track user
            topics=document.topics
        )
        
        if success:
            return {"status": "success", "message": f"Document '{document.filename}' uploaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload document")
            
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.post("/documents/upload_pdf", tags=["Documents"])
async def upload_pdf_document(
    rag_engine: RAGService = Depends(get_rag_engine),
    file: UploadFile = File(...),
    topics: str = Form("")
):
    """Upload a PDF document to Alan's knowledge base"""
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are accepted.")

        # Read PDF content
        pdf_content = await file.read()
        
        # Extract text from PDF using PyMuPDF
        text_content = ""
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page in doc:
                text_content += page.get_text()

        # Split topics string into a list
        topic_list = [topic.strip() for topic in topics.split(',') if topic.strip()]

        # Add document to RAG engine
        success = rag_engine.add_user_document(
            content=text_content,
            filename=file.filename,
            user_email="system",
            topics=topic_list
        )
        
        if success:
            return {"status": "success", "message": f"PDF document '{file.filename}' uploaded and processed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process and upload PDF document")
            
    except Exception as e:
        logger.error(f"Error uploading PDF document: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading PDF: {str(e)}")


@router.post("/news/add", tags=["News"])
async def add_news_article(
    article: NewsArticle,
    rag_engine: RAGService = Depends(get_rag_engine)
):
    """Add a news article to Alan's knowledge base"""
    try:
        success = rag_engine.add_news_article(
            title=article.title,
            content=article.content,
            url=article.url,
            topics=article.topics
        )
        
        if success:
            return {"status": "success", "message": f"News article '{article.title}' added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add news article")
            
    except Exception as e:
        logger.error(f"Error adding news article: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding news article: {str(e)}")

@router.post("/search", tags=["RAG"])
async def search_knowledge_base(
    query_request: QueryRequest,
    rag_engine: RAGService = Depends(get_rag_engine)
):
    """Search Alan's knowledge base using RAG"""
    try:
        results = rag_engine.search_documents(
            query=query_request.query,
            n_results=query_request.n_results
        )
        
        return {
            "status": "success",
            "query": query_request.query,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching knowledge base: {str(e)}")


@router.get("/faiss/chunks", tags=["RAG"])
async def get_faiss_chunks():
    """Return the raw FAISS metadata.json documents (indexed chunks)"""
    try:
        meta_path = os.path.join(settings.rag_persist_directory, "metadata.json")
        if not os.path.exists(meta_path):
            raise HTTPException(status_code=404, detail="FAISS metadata.json not found")
        with open(meta_path, 'r') as f:
            data = json.load(f)
        # Return the list of document chunks and their metadata
        return {"status": "success", "chunks": data.get("documents", []), "metadata": data.get("metadata", [])}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading FAISS chunks: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading FAISS chunks: {str(e)}")

@router.get("/knowledge-base/stats", tags=["RAG"])
async def get_knowledge_base_stats(
    rag_engine: RAGService = Depends(get_rag_engine)
):
    """Get statistics about Alan's knowledge base"""
    try:
        stats = rag_engine.get_knowledge_base_stats()
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@router.post("/digest/subscribe", tags=["Daily Digest"])
async def subscribe_to_digest(
    user: UserDigest,
    digest_service: DailyDigestService = Depends(get_digest_service)
):
    """Subscribe to Alan's daily digest"""
    try:
        success = digest_service.add_user(
            email=user.email,
            interests=user.interests,
            name=user.name
        )
        
        if success:
            return {"status": "success", "message": f"Subscribed {user.email} to daily digest"}
        else:
            raise HTTPException(status_code=500, detail="Failed to subscribe to daily digest")
            
    except Exception as e:
        logger.error(f"Error subscribing to digest: {e}")
        raise HTTPException(status_code=500, detail=f"Error subscribing: {str(e)}")

@router.delete("/digest/unsubscribe/{email}", tags=["Daily Digest"])
async def unsubscribe_from_digest(
    email: str,
    digest_service: DailyDigestService = Depends(get_digest_service)
):
    """Unsubscribe from Alan's daily digest"""
    try:
        success = digest_service.remove_user(email)
        
        if success:
            return {"status": "success", "message": f"Unsubscribed {email} from daily digest"}
        else:
            raise HTTPException(status_code=404, detail=f"User {email} not found in digest list")
            
    except Exception as e:
        logger.error(f"Error unsubscribing from digest: {e}")
        raise HTTPException(status_code=500, detail=f"Error unsubscribing: {str(e)}")

@router.get("/digest/stats", tags=["Daily Digest"])
async def get_digest_stats(
    digest_service: DailyDigestService = Depends(get_digest_service)
):
    """Get statistics about daily digest subscribers"""
    try:
        stats = digest_service.get_digest_stats()
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        logger.error(f"Error getting digest stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting digest stats: {str(e)}")

@router.post("/test-rag", tags=["RAG"])
async def test_rag_response(
    query_request: QueryRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """Test RAG-powered response generation"""
    try:
        # Generate a test response using RAG
        # Access the RAG engine attached to the AI service
        rag_engine = ai_service.rag_engine
        context = rag_engine.get_context_for_query(
            query=query_request.query,
            user_interests=query_request.user_interests,
            n_results=query_request.n_results
        )
        
        # Create a test prompt
        test_prompt = f"""Based on the following information from my knowledge base:

{context}

Please provide a helpful response to this query: {query_request.query}

Be informative, concise, and helpful."""
        
        messages = [
            {"role": "system", "content": "You are Alan, an AI assistant. Provide helpful, accurate responses based on your knowledge base."},
            {"role": "user", "content": test_prompt}
        ]
        
        response = ai_service.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        reply = response.choices[0].message.content.strip()
        
        return {
            "status": "success",
            "query": query_request.query,
            "context_used": context,
            "response": reply
        }
        
    except Exception as e:
        logger.error(f"Error testing RAG response: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing RAG: {str(e)}")
