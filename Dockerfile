FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn

# Copy all the source code
COPY . .

# Run the app
CMD ["python", "fastapi_server.py"]
