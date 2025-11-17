from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import time
import uuid
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PaymentService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)


class PaymentRequest(BaseModel):
    order_id: int = None
    amount: float = 100.0
    product_id: int = None
    quantity: int = 1


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "paymentservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/process_payment")
def process_payment(request: PaymentRequest):
    """
    Scenario 2: Simulated Long-Running Process (External API)
    Simulates a call to an external payment API (e.g., Stripe) with a 2-second delay
    """
    logger.info(f"Processing payment for order {request.order_id}, amount: ${request.amount}")

    # Simulate external API call delay (2 seconds)
    time.sleep(2)

    transaction_id = str(uuid.uuid4())
    logger.info(f"Payment processed successfully. Transaction ID: {transaction_id}")

    return {
        "status": "success",
        "transaction_id": transaction_id,
        "amount": request.amount,
        "order_id": request.order_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/process_payment_fail", status_code=400)
def process_payment_fail(request: PaymentRequest):
    """
    Scenario 5: Compensation (Saga Pattern)
    Simulates a payment failure for testing compensation logic
    """
    logger.warning(f"Payment failed for order {request.order_id}")

    raise HTTPException(
        status_code=400,
        detail={
            "status": "failed",
            "reason": "Insufficient funds",
            "order_id": request.order_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
