import time
import functools
import logging
from typing import Callable, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 60, period: int = 60):
        self.max_calls = max_calls  # Max calls per period
        self.period = period  # Period in seconds
        self.calls = []  # Timestamp of calls
        
    def _cleanup_old_calls(self):
        """Remove calls older than the period"""
        current_time = time.time()
        self.calls = [call_time for call_time in self.calls 
                     if current_time - call_time < self.period]
    
    def can_make_call(self) -> bool:
        """Check if a call can be made within rate limits"""
        self._cleanup_old_calls()
        return len(self.calls) < self.max_calls
    
    def add_call(self):
        """Record a call"""
        self.calls.append(time.time())
    
    def time_until_available(self) -> float:
        """Get seconds until a call slot becomes available"""
        if self.can_make_call():
            return 0
        
        self._cleanup_old_calls()
        oldest_call = min(self.calls)
        return oldest_call + self.period - time.time()

# Global rate limiter for Gemini API - Conservative limits for free tier
gemini_limiter = RateLimiter(max_calls=15, period=60)  # 15 calls per minute for free tier

def rate_limited(func: Callable) -> Callable:
    """Decorator to rate limit synchronous functions"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not gemini_limiter.can_make_call():
            wait_time = gemini_limiter.time_until_available()
            logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        gemini_limiter.add_call()
        return func(*args, **kwargs)
    
    return wrapper

def async_rate_limited(func: Callable) -> Callable:
    """Decorator to rate limit async functions"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not gemini_limiter.can_make_call():
            wait_time = gemini_limiter.time_until_available()
            logger.warning(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        gemini_limiter.add_call()
        return await func(*args, **kwargs)
    
    return wrapper