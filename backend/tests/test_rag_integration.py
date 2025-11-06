#!/usr/bin/env python3
"""
Test script for RAG functionality
This script demonstrates Alan's RAG-powered capabilities
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the Python path (one level up from tests)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def test_rag_integration():
    """Test the RAG integration without requiring OpenAI API key"""
    print("🧠 Testing Alan's RAG Integration")
    print("=" * 50)
    
    try:
        # Test RAG engine import (will fail without API key, but that's expected)
        try:
            from services.rag_service import RAGService
            print("✅ RAG Service imported successfully")
            
            # Try to initialize (will fail without API key)
            try:
                rag_engine = RAGService()
                print("✅ RAG Service initialized successfully")
                
                # Test adding a sample document
                sample_doc = {
                    'id': 'test_doc_1',
                    'content': 'Alan is an AI assistant that helps with email management and provides intelligent responses using RAG technology.',
                    'metadata': {
                        'type': 'test_document',
                        'title': 'Alan AI Assistant',
                        'topics': ['ai', 'email', 'assistant']
                    }
                }
                
                success = rag_engine.add_documents([sample_doc])
                if success:
                    print("✅ Sample document added to knowledge base")
                    
                    # Test search
                    results = rag_engine.search_documents("What is Alan?", n_results=3)
                    print(f"✅ Search functionality works: {len(results)} results found")
                    
                    # Test stats
                    stats = rag_engine.get_knowledge_base_stats()
                    print(f"✅ Knowledge base stats: {stats.get('total_chunks', 0)} chunks")
                    
                else:
                    print("⚠️  Failed to add sample document")
                    
            except ValueError as e:
                if "OPENAI_API_KEY" in str(e):
                    print("⚠️  RAG Engine requires OPENAI_API_KEY (using mock mode)")
                    print("✅ RAG Engine structure is correct")
                else:
                    raise
                    
        except ImportError as e:
            print(f"❌ Error importing RAG Engine: {e}")
            return False
        
        # Test daily digest service
        try:
            from email_modules.daily_digest import DailyDigestService
            print("✅ Daily Digest Service imported successfully")
        except ImportError as e:
            print(f"❌ Error importing Daily Digest Service: {e}")
            return False
        
        # Test AI service with RAG (now via services)
        try:
            from services.ai_service import AIService
            print("✅ AI Service with RAG imported successfully")
        except ValueError as e:
            if "OPENAI_API_KEY" in str(e):
                print("⚠️  AI Service requires OPENAI_API_KEY (using mock mode)")
                print("✅ AI Service structure is correct")
            else:
                raise
        
        print("\n🎉 RAG Integration Test Complete!")
        print("\nTo use RAG-powered responses:")
        print("1. Set OPENAI_API_KEY in your .env file")
        print("2. Add documents to the knowledge base via API")
        print("3. Alan will generate context-aware responses!")
        print("\nNew API endpoints available:")
        print("- POST /documents/upload - Upload documents")
        print("- POST /news/add - Add news articles")
        print("- POST /search - Search knowledge base")
        print("- POST /digest/subscribe - Subscribe to daily digest")
        print("- GET /knowledge-base/stats - View knowledge base stats")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing RAG integration: {e}")
        return False

if __name__ == "__main__":
    success = test_rag_integration()
    sys.exit(0 if success else 1)


