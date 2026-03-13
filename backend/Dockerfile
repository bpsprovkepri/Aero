# Runtime stage
FROM python:3.11-slim as runner

WORKDIR /app

# Install runtime + Playwright system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Set PATH BEFORE running playwright install
ENV PATH=/root/.local/bin:$PATH

# Copy app code
COPY . .

# Now playwright binary is on PATH — install browser
RUN playwright install chromium

# Environment variables
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
