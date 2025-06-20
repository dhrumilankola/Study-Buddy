#!/usr/bin/env python3
"""
Diagnostic script to investigate vector database and document management issues
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database.connection import get_db_session_context
from app.database.services import DocumentService, ChatService
from app.services.vector_store import EnhancedVectorStoreService
from app.database.models import Document, ChatSession
from sqlalchemy import select, func
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def diagnose_vector_issues():
    """Main diagnostic function"""
    print("=" * 60)
    print("STUDY BUDDY VECTOR DATABASE DIAGNOSTIC")
    print("=" * 60)
    
    # Initialize vector store service
    vector_service = EnhancedVectorStoreService()
    
    # 1. Check vector store status
    print("\n1. VECTOR STORE STATUS")
    print("-" * 30)
    try:
        total_chunks = await vector_service.get_document_count()
        print(f"Total chunks in vector store: {total_chunks}")
        
        # Get collection details if possible
        if vector_service._vector_store is None:
            vector_service._initialize_vector_store()
        
        collection = vector_service._vector_store._collection
        print(f"Collection name: {collection.name}")
        print(f"Collection count: {collection.count()}")
        
    except Exception as e:
        print(f"Error checking vector store: {e}")
    
    # 2. Check database documents
    print("\n2. DATABASE DOCUMENTS")
    print("-" * 30)
    async with get_db_session_context() as db:
        try:
            # Get all documents
            documents = await DocumentService.get_all_documents(db, limit=100)
            print(f"Total documents in database: {len(documents)}")
            
            # Group by status
            status_counts = {}
            for doc in documents:
                status = doc.processing_status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("Documents by status:")
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
            
            # Show recent documents
            print("\nRecent documents (last 10):")
            recent_docs = sorted(documents, key=lambda x: x.created_at, reverse=True)[:10]
            for doc in recent_docs:
                print(f"  {doc.id}: {doc.original_filename} ({doc.processing_status.value}) - {doc.chunk_count} chunks")
                
        except Exception as e:
            print(f"Error checking database documents: {e}")
    
    # 3. Check document-chunk consistency
    print("\n3. DOCUMENT-CHUNK CONSISTENCY")
    print("-" * 30)
    async with get_db_session_context() as db:
        try:
            documents = await DocumentService.get_all_documents(db, limit=100)
            total_db_chunks = 0
            inconsistencies = []
            
            for doc in documents:
                if doc.processing_status.value == 'indexed':
                    # Get chunk count from vector store
                    vector_chunks = await vector_service.get_document_chunk_count(doc.uuid_filename)
                    db_chunks = doc.chunk_count
                    total_db_chunks += db_chunks
                    
                    if vector_chunks != db_chunks:
                        inconsistencies.append({
                            'doc_id': doc.id,
                            'filename': doc.original_filename,
                            'uuid': doc.uuid_filename,
                            'db_chunks': db_chunks,
                            'vector_chunks': vector_chunks
                        })
            
            print(f"Total chunks in database: {total_db_chunks}")
            print(f"Total chunks in vector store: {total_chunks}")
            print(f"Discrepancy: {total_chunks - total_db_chunks}")
            
            if inconsistencies:
                print(f"\nFound {len(inconsistencies)} documents with chunk count inconsistencies:")
                for inc in inconsistencies:
                    print(f"  {inc['filename']}: DB={inc['db_chunks']}, Vector={inc['vector_chunks']}")
            else:
                print("No chunk count inconsistencies found between individual documents")
                
        except Exception as e:
            print(f"Error checking consistency: {e}")
    
    # 4. Check chat sessions and document associations
    print("\n4. CHAT SESSIONS AND DOCUMENT ASSOCIATIONS")
    print("-" * 30)
    async with get_db_session_context() as db:
        try:
            # Get all chat sessions
            result = await db.execute(select(ChatSession))
            sessions = result.scalars().all()
            print(f"Total chat sessions: {len(sessions)}")
            
            # Check document associations
            total_associations = 0
            for session in sessions:
                docs = await ChatService.get_session_documents(db, session.id)
                total_associations += len(docs)
                if docs:
                    print(f"  Session {session.id} ({session.title}): {len(docs)} documents")
                    for doc in docs:
                        print(f"    - {doc.original_filename} ({doc.uuid_filename})")
            
            print(f"Total document-session associations: {total_associations}")
            
        except Exception as e:
            print(f"Error checking chat sessions: {e}")
    
    # 5. Check for orphaned chunks in vector store
    print("\n5. ORPHANED CHUNKS ANALYSIS")
    print("-" * 30)
    try:
        # Get all document UUIDs from database
        async with get_db_session_context() as db:
            documents = await DocumentService.get_all_documents(db, limit=100)
            db_uuids = {doc.uuid_filename for doc in documents}
        
        # Check vector store for chunks with unknown document UUIDs
        if vector_service._vector_store is None:
            vector_service._initialize_vector_store()
        
        collection = vector_service._vector_store._collection
        all_results = collection.get()
        
        if all_results and 'metadatas' in all_results:
            vector_uuids = set()
            orphaned_count = 0
            
            for metadata in all_results['metadatas']:
                if metadata and 'uuid_filename' in metadata:
                    uuid = metadata['uuid_filename']
                    vector_uuids.add(uuid)
                    if uuid not in db_uuids:
                        orphaned_count += 1
                elif metadata and 'filename' in metadata:
                    # Check if this is using old filename format
                    orphaned_count += 1
            
            print(f"Unique document UUIDs in vector store: {len(vector_uuids)}")
            print(f"Document UUIDs in database: {len(db_uuids)}")
            print(f"Orphaned chunks (no matching document): {orphaned_count}")
            
            # Show UUIDs that are in vector store but not in database
            orphaned_uuids = vector_uuids - db_uuids
            if orphaned_uuids:
                print(f"Orphaned UUIDs: {list(orphaned_uuids)[:5]}...")  # Show first 5
        
    except Exception as e:
        print(f"Error checking orphaned chunks: {e}")
    
    # 6. Sample metadata analysis
    print("\n6. SAMPLE METADATA ANALYSIS")
    print("-" * 30)
    try:
        if vector_service._vector_store is None:
            vector_service._initialize_vector_store()
        
        collection = vector_service._vector_store._collection
        sample_results = collection.get(limit=5)
        
        if sample_results and 'metadatas' in sample_results:
            print("Sample chunk metadata:")
            for i, metadata in enumerate(sample_results['metadatas'][:3]):
                print(f"  Chunk {i+1}: {metadata}")
        
    except Exception as e:
        print(f"Error analyzing metadata: {e}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(diagnose_vector_issues())
