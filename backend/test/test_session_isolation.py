#!/usr/bin/env python3
"""
Test script to verify session isolation is working correctly
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database.connection import get_db_session_context
from app.database.services import DocumentService, ChatService
from app.services.rag_service import EnhancedRAGService
from app.models.schemas import QueryRequest
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_session_isolation():
    """Test that session isolation is working correctly"""
    print("=" * 60)
    print("TESTING SESSION ISOLATION")
    print("=" * 60)
    
    rag_service = EnhancedRAGService()
    
    async with get_db_session_context() as db:
        try:
            # Get all chat sessions
            from sqlalchemy import select
            from app.database.models import ChatSession
            
            result = await db.execute(select(ChatSession))
            sessions = result.scalars().all()
            
            print(f"Found {len(sessions)} chat sessions")
            
            for session in sessions:
                print(f"\n--- Session: {session.title} ({session.session_uuid}) ---")
                
                # Get documents associated with this session
                docs = await ChatService.get_session_documents(db, session.id)
                print(f"Associated documents: {len(docs)}")
                
                for doc in docs:
                    print(f"  - {doc.original_filename} ({doc.uuid_filename})")
                
                # Test document filtering for this session
                session_filter = await rag_service._get_session_document_filter(session.session_uuid)
                print(f"Session document filter: {session_filter}")
                
                # Test a simple query to see what documents are retrieved
                if session_filter:
                    print("Testing document retrieval for this session...")
                    try:
                        search_results = await rag_service._perform_hybrid_search(
                            "test query",
                            k=3,
                            session_document_filter=session_filter
                        )
                        print(f"  Retrieved {len(search_results)} chunks from session documents")
                        
                        # Show which documents the chunks came from
                        doc_sources = set()
                        for result in search_results:
                            if 'metadata' in result and 'uuid_filename' in result['metadata']:
                                doc_sources.add(result['metadata']['uuid_filename'])
                        
                        print(f"  Chunks came from documents: {list(doc_sources)}")
                        
                    except Exception as e:
                        print(f"  Error testing retrieval: {e}")
                else:
                    print("  No documents associated - would search all documents")
            
            # Test global search (no session filter)
            print(f"\n--- Global Search (No Session Filter) ---")
            try:
                global_results = await rag_service._perform_hybrid_search("test query", k=5)
                print(f"Global search retrieved {len(global_results)} chunks")
                
                # Show all document sources
                all_doc_sources = set()
                for result in global_results:
                    if 'metadata' in result and 'uuid_filename' in result['metadata']:
                        all_doc_sources.add(result['metadata']['uuid_filename'])
                
                print(f"Global search found documents: {list(all_doc_sources)}")
                
            except Exception as e:
                print(f"Error in global search: {e}")
                
        except Exception as e:
            print(f"Error testing session isolation: {e}")
            raise

async def test_vector_store_filtering():
    """Test vector store filtering directly"""
    print(f"\n--- Testing Vector Store Filtering ---")
    
    from app.services.vector_store import EnhancedVectorStoreService
    
    vector_service = EnhancedVectorStoreService()
    
    try:
        # Get total document count
        total_count = await vector_service.get_document_count()
        print(f"Total chunks in vector store: {total_count}")
        
        # Test filtering by a specific uuid_filename
        async with get_db_session_context() as db:
            documents = await DocumentService.get_all_documents(db, limit=10)
            
            if documents:
                test_uuid = documents[0].uuid_filename
                print(f"Testing filter for UUID: {test_uuid}")
                
                # Test single document filter
                single_filter_results = await vector_service.similarity_search(
                    "test query",
                    k=10,
                    filter_dict={"uuid_filename": test_uuid}
                )
                print(f"Single UUID filter returned {len(single_filter_results)} chunks")
                
                # Test multiple document filter
                if len(documents) > 1:
                    test_uuids = [doc.uuid_filename for doc in documents[:2]]
                    multi_filter_results = await vector_service.similarity_search(
                        "test query",
                        k=10,
                        filter_dict={"uuid_filename": {"$in": test_uuids}}
                    )
                    print(f"Multi UUID filter returned {len(multi_filter_results)} chunks")
                
    except Exception as e:
        print(f"Error testing vector store filtering: {e}")

async def main():
    """Main test function"""
    try:
        await test_session_isolation()
        await test_vector_store_filtering()
        
        print("\n" + "=" * 60)
        print("SESSION ISOLATION TEST COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
