FROM python:3.10-slim

WORKDIR /app

COPY common /app/common
COPY analyticsservice/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyticsservice/*.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
