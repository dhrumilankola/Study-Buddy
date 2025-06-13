#!/usr/bin/env python3
"""
Test script to verify rate limiting and token management fixes
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.rag_service import EnhancedRAGService
from app.models.schemas import QueryRequest
from app.utils.rate_limiter import gemini_limiter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rate_limiting():
    """Test the rate limiting functionality"""
    logger.info("Testing rate limiting functionality...")
    
    # Initialize the RAG service
    rag_service = EnhancedRAGService()
    
    # Test rate limiter status
    logger.info(f"Rate limiter can make call: {gemini_limiter.can_make_call()}")
    logger.info(f"Current calls in window: {len(gemini_limiter.calls)}")
    
    # Create a simple test query
    test_query = QueryRequest(
        question="Hello, can you help me?",
        context_window=2,  # Use small context window
        model_provider="gemini"
    )
    
    try:
        logger.info("Sending test query...")
        response_parts = []
        
        async for response_chunk in rag_service.generate_response(test_query):
            response_parts.append(response_chunk)
            logger.info(f"Received chunk: {response_chunk[:100]}...")
            
            # Break after a few chunks to avoid long output
            if len(response_parts) > 5:
                break
                
        logger.info("Test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        return False

async def test_token_handler():
    """Test the token handler initialization"""
    logger.info("Testing token handler...")
    
    try:
        from app.services.rag_service import EnhancedTokenDebugHandler
        
        # Create token handler
        handler = EnhancedTokenDebugHandler()
        logger.info(f"Token handler initialized with limits:")
        logger.info(f"  Max tokens per minute: {handler.max_tokens_per_minute}")
        logger.info(f"  Max requests per minute: {handler.max_requests_per_minute}")
        logger.info(f"  Current tokens: {handler.total_tokens_per_minute}")
        logger.info(f"  Current requests: {handler.request_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Token handler test failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    logger.info("Starting rate limiting tests...")
    
    # Test token handler
    token_test = await test_token_handler()
    
    # Test rate limiting (only if token handler works)
    if token_test:
        rate_test = await test_rate_limiting()
        
        if rate_test:
            logger.info("✅ All tests passed!")
        else:
            logger.error("❌ Rate limiting test failed")
    else:
        logger.error("❌ Token handler test failed")

if __name__ == "__main__":
    asyncio.run(main())
