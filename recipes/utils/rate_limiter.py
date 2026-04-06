import time
from django.core.cache import cache

class RateLimiter:
    def __init__(self, key_prefix, max_requests=100, window_seconds=60):
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, identifier):
        key = f"{self.key_prefix}:{identifier}"
        current_time = time.time()
        
        # Get current window data
        window_data = cache.get(key, [])
        
        # Filter out requests outside the window
        window_data = [req_time for req_time in window_data 
                      if current_time - req_time < self.window_seconds]
        
        # Check if under limit
        if len(window_data) < self.max_requests:
            window_data.append(current_time)
            cache.set(key, window_data, self.window_seconds)
            return True
        
        # Update cache even when denied (to maintain accurate count)
        cache.set(key, window_data, self.window_seconds)
        return False

# Usage in service
rate_limiter = RateLimiter("spoonacular", max_requests=50, window_seconds=60)

def search_recipes(self, query, number=10, offset=0):
    if not rate_limiter.is_allowed("global"):
        raise Exception("Rate limit exceeded")
    # ... rest of method