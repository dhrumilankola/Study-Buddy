#!/usr/bin/env python3
"""
Debug script to test vector database filtering for document-session isolation.
This script will help identify issues with the RAG system's document filtering.
"""

import asyncio
import logging
import sys
import os
from typing import List, Dict, Any, Optional

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import AsyncSessionLocal
from app.database.services import DocumentService, ChatService
from app.services.vector_store import EnhancedVectorStoreService
from app.services.rag_service import EnhancedRAGService
from app.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_vector_filtering():
    """Debug the vector database filtering functionality"""
    
    print("=== Vector Database Filtering Debug ===\n")
    
    # Initialize services
    vector_store_service = EnhancedVectorStoreService()
    rag_service = EnhancedRAGService()
    
    async with AsyncSessionLocal() as db_session:
        # 1. Get all documents from database
        print("1. Checking documents in database...")
        documents = await DocumentService.get_all_documents(db_session)
        print(f"Found {len(documents)} documents in database:")
        for doc in documents:
            print(f"  - ID: {doc.id}, UUID: {doc.uuid_filename}, File: {doc.original_filename}, Status: {doc.processing_status}")
        print()
        
        # 2. Check vector store contents
        print("2. Checking vector store contents...")
        total_chunks = await vector_store_service.get_document_count()
        print(f"Total chunks in vector store: {total_chunks}")
        
        # Check chunks per document
        for doc in documents:
            if doc.processing_status == "indexed":
                chunk_count = await vector_store_service.get_document_chunk_count(doc.uuid_filename)
                print(f"  - {doc.original_filename} ({doc.uuid_filename}): {chunk_count} chunks")
        print()
        
        # 3. Get all chat sessions
        print("3. Checking chat sessions...")
        sessions = await ChatService.get_recent_sessions(db_session, limit=20)
        print(f"Found {len(sessions)} chat sessions:")
        for session in sessions:
            session_docs = await ChatService.get_session_documents(db_session, session.id)
            doc_names = [doc.original_filename for doc in session_docs]
            print(f"  - Session {session.session_uuid}: {len(session_docs)} docs - {doc_names}")
        print()
        
        # 4. Test vector filtering for each session
        print("4. Testing vector filtering for each session...")
        test_query = "What is this document about?"
        
        for session in sessions[:3]:  # Test first 3 sessions
            session_docs = await ChatService.get_session_documents(db_session, session.id)
            if not session_docs:
                print(f"  - Session {session.session_uuid}: No documents, skipping")
                continue
                
            print(f"  - Testing session {session.session_uuid} with {len(session_docs)} documents:")
            
            # Get session document filter
            session_document_filter = await rag_service._get_session_document_filter(session.session_uuid)
            print(f"    Session document filter: {session_document_filter}")
            
            # Test direct vector store filtering
            if session_document_filter:
                if len(session_document_filter) == 1:
                    filter_dict = {"uuid_filename": session_document_filter[0]}
                else:
                    filter_dict = {"uuid_filename": {"$in": session_document_filter}}
                
                print(f"    Filter dict: {filter_dict}")
                
                # Test vector store search with filter
                try:
                    search_results = await vector_store_service.similarity_search(
                        query=test_query,
                        k=5,
                        filter_dict=filter_dict
                    )
                    
                    print(f"    Found {len(search_results)} filtered results:")
                    for i, result in enumerate(search_results):
                        metadata = result.get("metadata", {})
                        uuid_filename = metadata.get("uuid_filename", "Unknown")
                        filename = metadata.get("filename", "Unknown")
                        score = result.get("score", 0)
                        print(f"      {i+1}. {filename} ({uuid_filename}) - Score: {score:.3f}")
                        
                        # Check if this result belongs to the session documents
                        if uuid_filename not in session_document_filter:
                            print(f"        ⚠️  WARNING: Result from document NOT in session!")
                    
                    # Test without filter for comparison
                    unfiltered_results = await vector_store_service.similarity_search(
                        query=test_query,
                        k=5,
                        filter_dict=None
                    )
                    print(f"    Unfiltered search found {len(unfiltered_results)} results:")
                    for i, result in enumerate(unfiltered_results):
                        metadata = result.get("metadata", {})
                        uuid_filename = metadata.get("uuid_filename", "Unknown")
                        filename = metadata.get("filename", "Unknown")
                        score = result.get("score", 0)
                        in_session = uuid_filename in session_document_filter
                        marker = "✓" if in_session else "✗"
                        print(f"      {i+1}. {marker} {filename} ({uuid_filename}) - Score: {score:.3f}")
                    
                except Exception as e:
                    print(f"    ❌ Error testing vector filtering: {e}")
            
            print()
        
        # 5. Test RAG service hybrid search
        print("5. Testing RAG service hybrid search...")
        if sessions:
            test_session = sessions[0]
            session_docs = await ChatService.get_session_documents(db_session, test_session.id)

            if session_docs:
                print(f"Testing with session {test_session.session_uuid}")
                print(f"Session has documents: {[doc.original_filename for doc in session_docs]}")

                try:
                    # Test hybrid search with session filter
                    session_document_filter = [doc.uuid_filename for doc in session_docs]
                    hybrid_results = await rag_service._perform_hybrid_search(
                        query=test_query,
                        k=5,
                        session_document_filter=session_document_filter
                    )

                    print(f"Hybrid search found {len(hybrid_results)} results:")
                    for i, result in enumerate(hybrid_results):
                        metadata = result.get("metadata", {})
                        uuid_filename = metadata.get("uuid_filename", "Unknown")
                        filename = metadata.get("filename", "Unknown")
                        score = result.get("score", 0)
                        in_session = uuid_filename in session_document_filter
                        marker = "✓" if in_session else "✗"
                        print(f"  {i+1}. {marker} {filename} ({uuid_filename}) - Score: {score:.3f}")

                        if not in_session:
                            print(f"      ⚠️  WARNING: Result from document NOT in session!")

                except Exception as e:
                    print(f"❌ Error testing hybrid search: {e}")

        # 6. Test the _extract_query_metadata function
        print("\n6. Testing query metadata extraction...")
        test_queries = [
            "What is this document about?",
            "Tell me about the PDF file",
            "What's in the presentation?",
            "Explain the notebook content"
        ]

        for query in test_queries:
            try:
                metadata = await rag_service._extract_query_metadata(query)
                print(f"Query: '{query}' -> Metadata: {metadata}")
            except Exception as e:
                print(f"Query: '{query}' -> Error: {e}")

        # 7. Test complete generate_response flow
        print("\n7. Testing complete generate_response flow...")
        if sessions:
            test_session = None
            for session in sessions:
                session_docs = await ChatService.get_session_documents(db_session, session.id)
                if session_docs:
                    test_session = session
                    break

            if test_session:
                print(f"Testing complete flow with session {test_session.session_uuid}")

                # Create a mock QueryRequest
                from app.models.schemas import QueryRequest
                query_request = QueryRequest(
                    question="What is this document about?",
                    context_window=3
                )

                print("Generating response...")
                response_chunks = []
                try:
                    async for chunk in rag_service.generate_response(query_request, session_uuid=test_session.session_uuid):
                        response_chunks.append(chunk)
                        if len(response_chunks) > 10:  # Limit output
                            break

                    print(f"Generated {len(response_chunks)} response chunks")
                    for i, chunk in enumerate(response_chunks[:5]):
                        print(f"  Chunk {i+1}: {chunk[:100]}...")

                except Exception as e:
                    print(f"❌ Error in generate_response: {e}")

        print("\n=== Debug Complete ===")

if __name__ == "__main__":
    asyncio.run(debug_vector_filtering())
