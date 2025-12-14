from fastapi import FastAPI
from pydantic import BaseModel
import logging
import time
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="EmailService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


class EmailRequest(BaseModel):
    email: str
    user_id: int = None


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "emailservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/send_welcome_email")
def send_welcome_email(request: EmailRequest):
    """
    Scenario 1: Non-Critical Task Decoupling
    Simulates sending a welcome email with a 500ms delay
    """
    logger.info(f"Sending welcome email to {request.email}")

    # Simulate email sending delay (500ms)
    time.sleep(0.5)

    logger.info(f"Welcome email sent successfully to {request.email}")

    return {
        "message": "Email sent",
        "email": request.email,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
