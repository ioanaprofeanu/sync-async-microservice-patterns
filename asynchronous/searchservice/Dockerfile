FROM python:3.10-slim

WORKDIR /app

COPY common /app/common
COPY searchservice/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY searchservice/*.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
