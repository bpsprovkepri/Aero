FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Use python3 -m pip to ensure correct interpreter
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Use python3 -m uvicorn to ensure correct interpreter
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
