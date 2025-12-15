"""
Event schemas for RabbitMQ messages.
All events use Pydantic for validation and JSON serialization.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ==================== Scenario 1: User Registration ====================

class UserRegisteredEvent(BaseModel):
    """Published by UserService when a new user registers."""
    user_id: int
    email: EmailStr
    timestamp: datetime = datetime.utcnow()

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "email": "user@example.com",
                "timestamp": "2025-01-01T12:00:00"
            }
        }


# ==================== Scenario 2: Payment Processing ====================

class PaymentInitiatedEvent(BaseModel):
    """Published by PaymentService to trigger async payment processing."""
    payment_id: str
    amount: float
    currency: str = "USD"
    timestamp: datetime = datetime.utcnow()


class PaymentCompletedEvent(BaseModel):
    """Published after payment processing completes."""
    payment_id: str
    transaction_id: str
    status: str  # "success" or "failed"
    timestamp: datetime = datetime.utcnow()


class PaymentFailedEvent(BaseModel):
    """Published when payment fails (Scenario 5 Saga)."""
    payment_id: Optional[str] = None
    order_id: int
    reason: str
    timestamp: datetime = datetime.utcnow()


# ==================== Scenario 3: Product Updates (Fan-Out) ====================

class ProductUpdatedEvent(BaseModel):
    """Published by ProductService to fanout exchange."""
    product_id: int
    name: str
    stock: int
    timestamp: datetime = datetime.utcnow()


# ==================== Scenario 4: Report Generation ====================

class GenerateReportJobEvent(BaseModel):
    """Published to trigger CPU-intensive report generation."""
    job_id: str
    report_type: str
    parameters: dict = {}
    timestamp: datetime = datetime.utcnow()


class ReportGeneratedEvent(BaseModel):
    """Published when report generation completes."""
    job_id: str
    report_hash: str
    duration_seconds: float
    timestamp: datetime = datetime.utcnow()


# ==================== Scenario 5: Saga Pattern (Choreography) ====================

class OrderCreatedEvent(BaseModel):
    """Published by OrderService to start saga."""
    order_id: int
    product_id: int
    quantity: int
    timestamp: datetime = datetime.utcnow()


class StockReservedEvent(BaseModel):
    """Published by InventoryService after reserving stock."""
    order_id: int
    product_id: int
    quantity: int
    reserved_at: datetime = datetime.utcnow()


class StockReleasedEvent(BaseModel):
    """Published by InventoryService during compensation."""
    order_id: int
    product_id: int
    quantity: int
    reason: str  # "payment_failed" or "order_cancelled"
    released_at: datetime = datetime.utcnow()


# ==================== Scenario 6: High-Throughput Analytics ====================

class ClickTrackedEvent(BaseModel):
    """Published for high-throughput click tracking."""
    user_id: int
    page: str
    session_id: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class AnalyticsProcessedEvent(BaseModel):
    """Published after batch processing analytics events."""
    batch_id: str
    events_count: int
    processed_at: datetime = datetime.utcnow()


# ==================== Helper Functions ====================

def event_to_json(event: BaseModel) -> str:
    """
    Convert Pydantic event to JSON string for RabbitMQ.

    Args:
        event: Any Pydantic event model

    Returns:
        JSON string
    """
    return event.model_dump_json()


def json_to_event(json_str: str, event_class: type[BaseModel]) -> BaseModel:
    """
    Parse JSON string from RabbitMQ into Pydantic event.

    Args:
        json_str: JSON string from message body
        event_class: Target Pydantic model class

    Returns:
        Validated event object
    """
    return event_class.model_validate_json(json_str)
