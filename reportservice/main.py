from fastapi import FastAPI
from pydantic import BaseModel
import logging
import hashlib
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ReportService", version="1.0.0")


class ReportRequest(BaseModel):
    report_type: str = "monthly"


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "reportservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/generate_report")
def generate_report(request: ReportRequest):
    """
    Scenario 4: CPU-Intensive Task
    Performs a CPU-bound task for ~10 seconds using hash computations
    DO NOT use time.sleep() - this must be actual CPU work
    """
    logger.info(f"Starting CPU-intensive report generation: {request.report_type}")

    start_time = time.time()
    target_duration = 10  # 10 seconds

    # Perform actual CPU-intensive work (repeated hashing)
    text = b"compute_hash_for_report"
    iterations = 0

    while (time.time() - start_time) < target_duration:
        # Perform SHA-256 hashing repeatedly to consume CPU
        text = hashlib.sha256(text).digest()
        iterations += 1

    elapsed_time = time.time() - start_time

    logger.info(f"Report generation completed in {elapsed_time:.2f} seconds, {iterations} iterations")

    return {
        "status": "completed",
        "report_type": request.report_type,
        "report_hash": text.hex(),
        "computation_time_seconds": elapsed_time,
        "iterations": iterations,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
