import time
from collections import defaultdict
from fastapi import HTTPException

# In-memory store: { ip_address: [timestamp1, timestamp2, ...] }
_rate_limits = defaultdict(list)

def check_rate_limit(client_ip: str, limit: int = 60, window_sec: int = 60):
    """
    Sliding window rate limiter.
    Raises HTTPException 429 if limit is exceeded.
    """
    now = time.time()
    
    # Filter out old timestamps
    _rate_limits[client_ip] = [ts for ts in _rate_limits[client_ip] if now - ts < window_sec]
    
    if len(_rate_limits[client_ip]) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(window_sec)}
        )
        
    _rate_limits[client_ip].append(now)
