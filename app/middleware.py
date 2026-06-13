from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
import json
import httpx
from .config import settings
from .database import get_db
from .jwks import jwks_cache
import time
import uuid

async def jwt_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing or invalid Authorization header"})
    
    token = auth_header.split(" ")[1]
    
    try:
        if settings.JWKS_URL:
            # Use cached JWKS
            jwks = await jwks_cache.get_keys(settings.JWKS_URL)
            
            # Get kid from token header
            unverified_headers = jwt.get_unverified_header(token)
            kid = unverified_headers.get("kid")
            
            if not kid or kid not in jwks:
                raise HTTPException(status_code=401, detail="Invalid token: unknown key ID")
            
            key = jwks[kid]
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            
            payload = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
            )
        else:
            # Fallback to static public key / secret
            payload = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY or settings.JWT_ISSUER,
                algorithms=["RS256", "HS256"],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
            )
        
        user_id = payload.get("sub") or payload.get("email")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        request.state.user_id = user_id
        request.state.token_payload = payload
        
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"error": "Token expired"})
    except jwt.InvalidTokenError as e:
        return JSONResponse(status_code=401, content={"error": f"Invalid token: {str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=401, content={"error": f"Authentication failed: {str(e)}"})
    
    # Check approved users
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM approved_users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        return JSONResponse(status_code=403, content={"error": "User not approved"})
    
    return await call_next(request)

def setup_middleware(app):
    @app.middleware("http")
    async def combined_middleware(request: Request, call_next):
        start_time = time.time()
        request.state.request_id = str(uuid.uuid4())
        
        # Auth + approval
        response = await jwt_auth_middleware(request, call_next)
        
        # TODO: Add rate limit, quota, usage logging in future middleware layers
        return response
