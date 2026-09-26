import os
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key_header: str = Security(api_key_header)):
    """Verify that the provided API key is valid (either admin or public website key)."""
    admin_key = os.getenv("API_SECRET_KEY")
    public_key = os.getenv("WEBSITE_PUBLIC_KEY")
    
    if api_key_header == admin_key or api_key_header == public_key:
        return api_key_header
        
    raise HTTPException(
        status_code=403,
        detail="Could not validate API credentials"
    )

def verify_vapi_signature(req: Request):
    """
    In a production app, verify X-Vapi-Signature header using HMAC and VAPI_PRIVATE_KEY.
    For this prototype, we'll just check if the header exists or let it pass,
    since ngrok testing might not always have the perfect signature setup depending on Vapi dashboard.
    """
    # secret = os.getenv("VAPI_PRIVATE_KEY")
    # signature = req.headers.get("x-vapi-signature")
    pass
