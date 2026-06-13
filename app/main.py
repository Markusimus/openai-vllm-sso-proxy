from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .config import settings
from .routers import api_router
from .middleware import setup_middleware

app = FastAPI(
    title="OpenAI vLLM SSO Proxy",
    description="Secure proxy with SSO for vLLM backends",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup middleware (auth, logging, etc.)
setup_middleware(app)

# Include routers
app.include_router(api_router)

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
