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

app = FastAPI(title="AnalyticsService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


class LogUpdateRequest(BaseModel):
    product_id: int


class ClickTrackingRequest(BaseModel):
    user_id: int
    page: str


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "analyticsservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/log_update")
def log_update(request: LogUpdateRequest):
    """
    Scenario 3: Fan-Out Flow
    Receives product update and logs it for analytics
    """
    logger.info(f"Logging product update for product {request.product_id}")

    # Simulate analytics logging operation (minimal delay)
    # In a real system, this would send to analytics platform

    return {
        "status": "ok",
        "product_id": request.product_id,
        "service": "analyticsservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/track_click")
def track_click(request: ClickTrackingRequest):
    """
    Scenario 6: High-Throughput Data Ingestion
    Minimal endpoint for tracking user clicks with minimal processing
    """
    # Minimal logging - just print to demonstrate ingestion
    logger.info(f"Click tracked: user={request.user_id}, page={request.page}")

    # Return immediately with minimal processing
    return {
        "status": "tracked"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
