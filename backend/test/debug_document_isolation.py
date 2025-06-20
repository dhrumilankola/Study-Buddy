#!/usr/bin/env python3
"""
Debug script to test document isolation in chat sessions.
This will help identify why documents from other sessions are appearing in responses.
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

async def debug_document_isolation():
    """Debug document isolation in chat sessions"""
    
    print("=== Document Isolation Debug ===\n")
    
    # Initialize RAG service
    rag_service = EnhancedRAGService()
    
    async with AsyncSessionLocal() as db_session:
        # Get all documents
        documents = await DocumentService.get_all_documents(db_session)
        print(f"Available documents:")
        for doc in documents:
            print(f"  - ID: {doc.id}, UUID: {doc.uuid_filename}, File: {doc.original_filename}")
        print()
        
        # Get all sessions with documents
        sessions = await ChatService.get_recent_sessions(db_session, limit=10)
        sessions_with_docs = []
        
        for session in sessions:
            session_docs = await ChatService.get_session_documents(db_session, session.id)
            if session_docs:
                sessions_with_docs.append((session, session_docs))
        
        print(f"Sessions with documents:")
        for session, docs in sessions_with_docs:
            doc_names = [doc.original_filename for doc in docs]
            doc_uuids = [doc.uuid_filename for doc in docs]
            print(f"  - Session {session.session_uuid}:")
            print(f"    Documents: {doc_names}")
            print(f"    UUIDs: {doc_uuids}")
        print()
        
        if not sessions_with_docs:
            print("No sessions with documents found!")
            return
        
        # Test the first session with documents
        test_session, test_docs = sessions_with_docs[0]
        print(f"Testing session: {test_session.session_uuid}")
        print(f"Expected documents: {[doc.original_filename for doc in test_docs]}")
        print(f"Expected UUIDs: {[doc.uuid_filename for doc in test_docs]}")
        print()
        
        # Test 1: Check session document filter retrieval
        print("1. Testing session document filter retrieval...")
        session_filter = await rag_service._get_session_document_filter(test_session.session_uuid)
        print(f"   Retrieved filter: {session_filter}")
        expected_uuids = [doc.uuid_filename for doc in test_docs]
        if session_filter == expected_uuids:
            print("   ✅ Session filter matches expected documents")
        else:
            print(f"   ❌ Session filter mismatch! Expected: {expected_uuids}")
        print()
        
        # Test 2: Check hybrid search with session filter
        print("2. Testing hybrid search with session filter...")
        test_query = "explain the paper"
        try:
            search_results = await rag_service._perform_hybrid_search(
                query=test_query,
                k=5,
                session_document_filter=session_filter
            )
            
            print(f"   Found {len(search_results)} results:")
            correct_results = 0
            for i, result in enumerate(search_results):
                metadata = result.get("metadata", {})
                uuid_filename = metadata.get("uuid_filename", "Unknown")
                filename = metadata.get("filename", "Unknown")
                score = result.get("score", 0)
                
                is_correct = uuid_filename in session_filter if session_filter else False
                marker = "✅" if is_correct else "❌"
                
                print(f"     {i+1}. {marker} {filename} ({uuid_filename}) - Score: {score:.3f}")
                
                if is_correct:
                    correct_results += 1
                else:
                    print(f"        🚨 ERROR: This document should NOT be in results!")
            
            if correct_results == len(search_results) and len(search_results) > 0:
                print(f"   ✅ All {correct_results} results are from correct documents")
            else:
                print(f"   ❌ Only {correct_results}/{len(search_results)} results are correct")
                
        except Exception as e:
            print(f"   ❌ Error in hybrid search: {e}")
        print()
        
        # Test 3: Test complete RAG pipeline
        print("3. Testing complete RAG pipeline...")
        query_request = QueryRequest(
            question=test_query,
            context_window=3,
            model_provider="gemini"
        )
        
        try:
            print("   Generating response...")
            response_chunks = []
            context_sources = set()
            
            async for chunk in rag_service.generate_response(query_request, session_uuid=test_session.session_uuid):
                response_chunks.append(chunk)
                
                # Look for source information in the chunk
                if "Source:" in chunk:
                    # Extract source information
                    lines = chunk.split('\n')
                    for line in lines:
                        if "Source:" in line:
                            context_sources.add(line.strip())
                
                # Limit to avoid too much output
                if len(response_chunks) > 20:
                    break
            
            print(f"   Generated {len(response_chunks)} response chunks")
            
            if context_sources:
                print(f"   Found context sources in response:")
                for source in context_sources:
                    print(f"     - {source}")
                    
                # Check if any sources are from wrong documents
                wrong_sources = []
                expected_filenames = [doc.original_filename for doc in test_docs]
                for source in context_sources:
                    is_correct = any(filename.split('.')[0] in source for filename in expected_filenames)
                    if not is_correct:
                        wrong_sources.append(source)
                
                if wrong_sources:
                    print(f"   ❌ Found sources from WRONG documents:")
                    for wrong_source in wrong_sources:
                        print(f"     🚨 {wrong_source}")
                else:
                    print(f"   ✅ All sources are from correct documents")
            else:
                print(f"   ⚠️  No source information found in response")
                
        except Exception as e:
            print(f"   ❌ Error in RAG pipeline: {e}")
        
        print("\n=== Debug Complete ===")

if __name__ == "__main__":
    asyncio.run(debug_document_isolation())
