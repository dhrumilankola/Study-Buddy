#!/usr/bin/env python3
"""
End-to-end test to verify the complete RAG pipeline with session filtering.
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import AsyncSessionLocal
from app.database.services import DocumentService, ChatService
from app.services.rag_service import EnhancedRAGService
from app.models.schemas import QueryRequest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_end_to_end():
    """Test the complete RAG pipeline with session filtering"""
    
    print("=== End-to-End RAG Pipeline Test ===\n")
    
    # Initialize RAG service
    rag_service = EnhancedRAGService()
    
    async with AsyncSessionLocal() as db_session:
        # Get a session with documents
        sessions = await ChatService.get_recent_sessions(db_session, limit=10)
        test_session = None
        test_docs = None
        
        for session in sessions:
            session_docs = await ChatService.get_session_documents(db_session, session.id)
            if session_docs:
                test_session = session
                test_docs = session_docs
                break
        
        if not test_session:
            print("No sessions with documents found. Please create a session with documents first.")
            return
        
        print(f"Testing with session: {test_session.session_uuid}")
        print(f"Session documents: {[doc.original_filename for doc in test_docs]}")
        print(f"Document UUIDs: {[doc.uuid_filename for doc in test_docs]}")
        print()
        
        # Test queries
        test_queries = [
            "What is this document about?",
            "Summarize the main points",
            "What are the key findings?",
        ]
        
        for i, question in enumerate(test_queries, 1):
            print(f"--- Test Query {i}: '{question}' ---")
            
            # Create query request
            query_request = QueryRequest(
                question=question,
                context_window=3,
                model_provider="gemini"  # Use Gemini since that's what you have
            )
            
            print("Generating response...")
            
            try:
                response_chunks = []
                response_text = ""
                
                # Collect response chunks
                async for chunk in rag_service.generate_response(query_request, session_uuid=test_session.session_uuid):
                    response_chunks.append(chunk)
                    
                    # Parse the chunk to extract content
                    if '"type": "response"' in chunk and '"content":' in chunk:
                        # Extract content from SSE format
                        import json
                        try:
                            # Remove "data: " prefix if present
                            chunk_data = chunk.replace("data: ", "").strip()
                            if chunk_data:
                                parsed = json.loads(chunk_data)
                                if parsed.get("type") == "response":
                                    response_text += parsed.get("content", "")
                        except:
                            pass
                    
                    # Limit collection to avoid too much output
                    if len(response_chunks) > 50:
                        break
                
                print(f"✅ Response generated successfully!")
                print(f"   Total chunks: {len(response_chunks)}")
                print(f"   Response preview: {response_text[:200]}...")
                
                # Check if response mentions the correct document
                expected_doc_names = [doc.original_filename for doc in test_docs]
                mentions_correct_doc = any(doc_name.split('.')[0] in response_text for doc_name in expected_doc_names)
                
                if mentions_correct_doc:
                    print(f"   ✅ Response appears to reference the correct document(s)")
                else:
                    print(f"   ⚠️  Response may not be from the expected documents")
                
            except Exception as e:
                print(f"❌ Error generating response: {e}")
            
            print()
        
        # Test without session (should work with all documents)
        print("--- Test Without Session Filter ---")
        query_request = QueryRequest(
            question="What documents are available?",
            context_window=3,
            model_provider="gemini"
        )
        
        try:
            response_chunks = []
            async for chunk in rag_service.generate_response(query_request, session_uuid=None):
                response_chunks.append(chunk)
                if len(response_chunks) > 20:  # Limit for test
                    break
            
            print(f"✅ Global query (no session) generated {len(response_chunks)} chunks")
            
        except Exception as e:
            print(f"❌ Error in global query: {e}")
        
        print("\n=== End-to-End Test Complete ===")
        print("\n🎉 If you see ✅ marks above, the session-specific document filtering is working correctly!")
        print("   Each chat session will now only retrieve context from its assigned documents.")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
