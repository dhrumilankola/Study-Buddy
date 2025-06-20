#!/usr/bin/env python3
"""
Test script to verify session creation and document association.
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import AsyncSessionLocal
from app.database.services import DocumentService, ChatService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_session_creation():
    """Test session creation and document association"""
    
    print("=== Testing Session Creation and Document Association ===\n")
    
    async with AsyncSessionLocal() as db_session:
        # Get available documents
        documents = await DocumentService.get_all_documents(db_session)
        print(f"Available documents:")
        for doc in documents:
            print(f"  - ID: {doc.id}, File: {doc.original_filename}, Status: {doc.processing_status}")
        
        if not documents:
            print("No documents available for testing!")
            return
        
        # Use the first document for testing
        test_doc = documents[0]
        print(f"\nUsing document for test: {test_doc.original_filename} (ID: {test_doc.id})")
        
        # Create a new session with this document
        print("\n1. Creating new session with document...")
        session = await ChatService.create_session(
            db_session,
            title="Test Session",
            document_ids=[test_doc.id]
        )
        
        # Commit the transaction
        await db_session.commit()
        print(f"   Created session: {session.session_uuid}")
        
        # Verify the document association
        print("\n2. Verifying document association...")
        session_docs = await ChatService.get_session_documents(db_session, session.id)
        
        print(f"   Session has {len(session_docs)} associated documents:")
        for doc in session_docs:
            print(f"     - {doc.original_filename} (ID: {doc.id}, UUID: {doc.uuid_filename})")
        
        if len(session_docs) == 1 and session_docs[0].id == test_doc.id:
            print("   ✅ Document association successful!")
        else:
            print("   ❌ Document association failed!")
        
        # Test the RAG service document filter retrieval
        print("\n3. Testing RAG service document filter...")
        from app.services.rag_service import EnhancedRAGService
        rag_service = EnhancedRAGService()
        
        session_filter = await rag_service._get_session_document_filter(session.session_uuid)
        print(f"   RAG service retrieved filter: {session_filter}")
        
        expected_uuid = test_doc.uuid_filename
        if session_filter and len(session_filter) == 1 and session_filter[0] == expected_uuid:
            print("   ✅ RAG service document filter working!")
        else:
            print(f"   ❌ RAG service document filter failed! Expected: [{expected_uuid}]")
        
        # Test hybrid search with the session
        print("\n4. Testing hybrid search with session filter...")
        try:
            search_results = await rag_service._perform_hybrid_search(
                query="test query",
                k=3,
                session_document_filter=session_filter
            )
            
            print(f"   Search returned {len(search_results)} results:")
            all_correct = True
            for i, result in enumerate(search_results):
                metadata = result.get("metadata", {})
                uuid_filename = metadata.get("uuid_filename", "Unknown")
                filename = metadata.get("filename", "Unknown")
                
                is_correct = uuid_filename == expected_uuid
                marker = "✅" if is_correct else "❌"
                print(f"     {i+1}. {marker} {filename} ({uuid_filename})")
                
                if not is_correct:
                    all_correct = False
            
            if all_correct and len(search_results) > 0:
                print("   ✅ All search results are from the correct document!")
            elif len(search_results) == 0:
                print("   ⚠️  No search results found")
            else:
                print("   ❌ Some search results are from wrong documents!")
                
        except Exception as e:
            print(f"   ❌ Error in hybrid search: {e}")
        
        print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_session_creation())
