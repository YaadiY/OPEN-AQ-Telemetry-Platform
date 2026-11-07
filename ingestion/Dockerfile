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

# Install dependencies into a separate wheels/wheels folder
RUN pip install --no-cache-dir --user -r requirements.txt


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

# Copy source code
COPY ingestion/ /app/ingestion/

# Set working directory to project root for module imports
WORKDIR /app

# Run the master pipeline on container startup
ENTRYPOINT ["python", "ingestion/run_pipeline.py"]
