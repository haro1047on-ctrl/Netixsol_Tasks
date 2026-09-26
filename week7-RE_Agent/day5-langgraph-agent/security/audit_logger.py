import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import os

# Ensure logs dir exists
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Separate logger for audit trails
audit_logger = logging.getLogger("AuditLogger")
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler(os.path.join(LOGS_DIR, "audit.log"))
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
if not audit_logger.handlers:
    audit_logger.addHandler(handler)

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "Unknown"
        method = request.method
        url = request.url.path
        
        # Don't log static assets excessively
        is_static = url.startswith("/assets") or url.endswith((".css", ".js", ".png", ".ico", ".svg"))
        
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        status_code = response.status_code
        
        if not is_static:
            audit_logger.info(f"IP: {client_ip} | Method: {method} | URL: {url} | Status: {status_code} | Time: {process_time:.2f}ms")
            
        return response
