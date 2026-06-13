import asyncio
import json
from datetime import datetime, timedelta
import httpx
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class JWKSCache:
    def __init__(self, cache_ttl_minutes: int = 60):
        self.cache: Dict = {}
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.last_fetch: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def get_keys(self, jwks_url: str) -> Dict:
        """Get JWKS with caching and fallback"""
        async with self._lock:
            now = datetime.utcnow()
            
            # Return cached keys if still valid
            if (self.last_fetch and 
                now - self.last_fetch < self.cache_ttl and 
                jwks_url in self.cache):
                return self.cache[jwks_url]

            # Fetch fresh JWKS
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(jwks_url, timeout=10.0)
                    response.raise_for_status()
                    jwks = response.json()
                    
                    # Store keys by kid
                    keys = {key["kid"]: key for key in jwks.get("keys", []) if "kid" in key}
                    self.cache[jwks_url] = keys
                    self.last_fetch = now
                    
                    logger.info(f"Fetched and cached JWKS from {jwks_url} ({len(keys)} keys)")
                    return keys
                    
            except Exception as e:
                logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
                # Return stale cache if available
                if jwks_url in self.cache:
                    logger.warning("Using stale JWKS cache")
                    return self.cache[jwks_url]
                raise

jwks_cache = JWKSCache()
