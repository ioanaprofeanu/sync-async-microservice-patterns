FROM python:3.10-slim

WORKDIR /app

# Copy common utilities
COPY common /app/common

# Copy service-specific files
COPY userservice/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY userservice/*.py .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
