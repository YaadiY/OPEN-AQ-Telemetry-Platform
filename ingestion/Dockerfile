# ==========================================
# STAGE 1: Builder (Compiles dependencies)
# ==========================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build essentials if C-extensions are needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ingestion/requirements.txt .

# Install dependencies using uv for parallel, resilient downloads
RUN pip install --no-cache-dir uv && \
    uv pip install --no-cache --system --prefix /root/.local -r requirements.txt


# ==========================================
# STAGE 2: Runtime (Minimal production image)
# ==========================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Ensure user packages are accessible in PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json

# Copy GCP credentials into standard ADC path
COPY gcp_credentials.json /root/.config/gcloud/application_default_credentials.json

# Copy source code and dbt models
COPY ingestion/ /app/ingestion/
COPY dbt/ /app/dbt/

# Set working directory to project root for module imports
WORKDIR /app

# Default command
CMD ["python", "ingestion/run_pipeline.py"]
