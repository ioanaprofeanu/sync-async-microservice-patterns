from fastapi import FastAPI
from pydantic import BaseModel
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CacheService", version="1.0.0")


class CacheInvalidationRequest(BaseModel):
    product_id: int


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cacheservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/invalidate_cache")
def invalidate_cache(request: CacheInvalidationRequest):
    """
    Scenario 3: Fan-Out Flow
    Receives product update and invalidates the cache
    """
    logger.info(f"Invalidating cache for product {request.product_id}")

    # Simulate cache invalidation operation (minimal delay)
    # In a real system, this would clear Redis, Memcached, etc.

    logger.info(f"Cache invalidated successfully for product {request.product_id}")

    return {
        "status": "ok",
        "product_id": request.product_id,
        "service": "cacheservice",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
