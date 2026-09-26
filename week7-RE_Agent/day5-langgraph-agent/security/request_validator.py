import json
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RequestValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Prevent oversized requests (>64KB)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 65536:
            return HTTPException(status_code=413, detail="Payload Too Large")
            
        # Optional: validate basic JSON format if method is POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        json.loads(body)
                except ValueError:
                    return HTTPException(status_code=400, detail="Invalid JSON Payload")
                    
        response = await call_next(request)
        return response
