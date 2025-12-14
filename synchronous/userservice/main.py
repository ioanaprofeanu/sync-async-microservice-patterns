from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
import logging
import os
from datetime import datetime
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="UserService", version="1.0.0")

# Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dbuser:dbpass@postgres:5432/microservices_db")
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://emailservice:8000")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# User model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)


# Create tables
Base.metadata.create_all(bind=engine)


class UserRegistration(BaseModel):
    email: EmailStr


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "userservice",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/register", status_code=201)
def register_user(user_data: UserRegistration):
    """
    Scenario 1: Non-Critical Task Decoupling
    Registers a user and synchronously calls EmailService to send welcome email
    """
    db = SessionLocal()
    try:
        logger.info(f"Registering user with email: {user_data.email}")

        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Save user to database
        new_user = User(email=user_data.email)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"User {new_user.id} created successfully")

        # Synchronous blocking call to EmailService
        try:
            logger.info(f"Calling EmailService for user {new_user.id}")
            email_response = requests.post(
                f"{EMAIL_SERVICE_URL}/send_welcome_email",
                json={"email": user_data.email, "user_id": new_user.id},
                timeout=10
            )
            email_response.raise_for_status()
            logger.info(f"Email service responded: {email_response.json()}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            # In synchronous architecture, we continue despite email failure
            # but log the error

        return {
            "id": new_user.id,
            "email": new_user.email,
            "message": "User registered successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/users")
def get_users():
    """Get all registered users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return {
            "users": [{"id": user.id, "email": user.email} for user in users],
            "count": len(users)
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
