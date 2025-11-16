from fastapi import FastAPI
from pydantic import BaseModel
import logging
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SearchService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


class ReindexRequest(BaseModel):
    product_id: int


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "searchservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/reindex")
def reindex(request: ReindexRequest):
    """
    Scenario 3: Fan-Out Flow
    Receives product update and reindexes the search engine
    """
    logger.info(f"Reindexing product {request.product_id} in search engine")

    # Simulate reindexing operation (minimal delay)
    # In a real system, this would update Elasticsearch, Algolia, etc.

    logger.info(f"Product {request.product_id} reindexed successfully")

    return {
        "status": "ok",
        "product_id": request.product_id,
        "service": "searchservice",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
