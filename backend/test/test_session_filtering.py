#!/usr/bin/env python3
"""
Test script to verify session-specific document filtering is working correctly.
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

async def test_session_filtering():
    """Test that session filtering works correctly"""
    
    print("=== Testing Session-Specific Document Filtering ===\n")
    
    # Initialize RAG service
    rag_service = EnhancedRAGService()
    
    async with AsyncSessionLocal() as db_session:
        # Get all sessions with documents
        sessions = await ChatService.get_recent_sessions(db_session, limit=10)
        sessions_with_docs = []
        
        for session in sessions:
            session_docs = await ChatService.get_session_documents(db_session, session.id)
            if session_docs:
                sessions_with_docs.append((session, session_docs))
        
        if not sessions_with_docs:
            print("No sessions with documents found. Please create a session with documents first.")
            return
        
        print(f"Found {len(sessions_with_docs)} sessions with documents:")
        for i, (session, docs) in enumerate(sessions_with_docs):
            doc_names = [doc.original_filename for doc in docs]
            print(f"  {i+1}. Session {session.session_uuid}: {len(docs)} docs - {doc_names}")
        print()
        
        # Test each session
        test_query = "What is this document about?"
        
        for session, session_docs in sessions_with_docs[:2]:  # Test first 2 sessions
            print(f"--- Testing Session {session.session_uuid} ---")
            print(f"Expected documents: {[doc.original_filename for doc in session_docs]}")
            print(f"Expected UUIDs: {[doc.uuid_filename for doc in session_docs]}")
            
            # Test the session document filter retrieval
            session_filter = await rag_service._get_session_document_filter(session.session_uuid)
            print(f"Retrieved session filter: {session_filter}")
            
            # Test hybrid search with session filter
            try:
                search_results = await rag_service._perform_hybrid_search(
                    query=test_query,
                    k=5,
                    session_document_filter=session_filter
                )
                
                print(f"Search returned {len(search_results)} results:")
                
                # Check if all results are from the correct documents
                correct_results = 0
                for i, result in enumerate(search_results):
                    metadata = result.get("metadata", {})
                    uuid_filename = metadata.get("uuid_filename", "Unknown")
                    filename = metadata.get("filename", "Unknown")
                    score = result.get("score", 0)
                    
                    is_correct = uuid_filename in session_filter if session_filter else False
                    marker = "✓" if is_correct else "✗"
                    
                    print(f"  {i+1}. {marker} {filename} ({uuid_filename}) - Score: {score:.3f}")
                    
                    if is_correct:
                        correct_results += 1
                    else:
                        print(f"      ⚠️  ERROR: This document should NOT be in the results!")
                
                # Summary
                if correct_results == len(search_results) and len(search_results) > 0:
                    print(f"  ✅ SUCCESS: All {correct_results} results are from the correct session documents")
                elif len(search_results) == 0:
                    print(f"  ⚠️  WARNING: No results found")
                else:
                    print(f"  ❌ FAILURE: Only {correct_results}/{len(search_results)} results are correct")
                
            except Exception as e:
                print(f"  ❌ ERROR during search: {e}")
            
            print()
        
        # Test without session filter (should return results from all documents)
        print("--- Testing Global Search (No Session Filter) ---")
        try:
            global_results = await rag_service._perform_hybrid_search(
                query=test_query,
                k=5,
                session_document_filter=None
            )
            
            print(f"Global search returned {len(global_results)} results:")
            
            # Show all document sources
            all_doc_sources = set()
            for result in global_results:
                metadata = result.get("metadata", {})
                uuid_filename = metadata.get("uuid_filename", "Unknown")
                filename = metadata.get("filename", "Unknown")
                all_doc_sources.add(f"{filename} ({uuid_filename})")
            
            for doc in sorted(all_doc_sources):
                print(f"  - {doc}")
            
            print(f"  ✅ Global search found documents from {len(all_doc_sources)} different sources")
            
        except Exception as e:
            print(f"  ❌ ERROR during global search: {e}")
        
        print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_session_filtering())
