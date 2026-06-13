from fastapi import APIRouter, Request, HTTPException
import httpx
import json
import time
from datetime import datetime
from .config import settings
from .database import get_db
import asyncio

router = APIRouter(prefix="/v1")

async def proxy_request(request: Request, target_url: str):
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Forward the request
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        
        resp = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            follow_redirects=True,
        )
        
        return resp

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_vllm(request: Request, path: str):
    model = None
    try:
        body = await request.json()
        model = body.get("model")
    except:
        pass  # Non-JSON or no model (e.g. /models list)
    
    if not model and path == "models":
        # Return aggregated models from all backends or static list
        return {"object": "list", "data": [{"id": m, "object": "model"} for m in settings.MODEL_MAPPING.keys()]}
    
    if not model or model not in settings.MODEL_MAPPING:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    
    target_url = f"{settings.MODEL_MAPPING[model]}/v1/{path}"
    
    start_time = time.time()
    try:
        response = await proxy_request(request, target_url)
        
        # For streaming responses, we need special handling
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            return response  # Let FastAPI handle streaming
        
        # Non-streaming: extract usage
        try:
            data = response.json()
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # Async log usage
            asyncio.create_task(log_usage(
                request.state.request_id,
                request.state.user_id,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                int((time.time() - start_time) * 1000),
                "success"
            ))
        except:
            pass  # Ignore if can't parse usage
        
        return response.json()
        
    except Exception as e:
        asyncio.create_task(log_usage(
            request.state.request_id,
            request.state.user_id if hasattr(request.state, 'user_id') else "unknown",
            model or "unknown",
            0, 0, 0,
            int((time.time() - start_time) * 1000),
            "error"
        ))
        raise HTTPException(status_code=502, detail="Backend error")

async def log_usage(request_id, user_id, model, prompt_tokens, completion_tokens, total_tokens, duration_ms, status):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usage_logs 
        (request_id, user_id, model, prompt_tokens, completion_tokens, total_tokens, duration_ms, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (request_id, user_id, model, prompt_tokens, completion_tokens, total_tokens, duration_ms, status))
    
    # Update summary (simplified - monthly)
    month = datetime.now().strftime("%Y-%m")
    cursor.execute("""
        INSERT INTO user_usage_summary (user_id, month, total_tokens, request_count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET 
            total_tokens = total_tokens + ?,
            request_count = request_count + 1
    """, (user_id, month, total_tokens, total_tokens))
    
    conn.commit()
