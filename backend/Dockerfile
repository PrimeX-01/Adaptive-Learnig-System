FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY models/ /app/models/
COPY . .
ENV MODEL_PATH=/app/models/adaptive_model.joblib
ENV PREPROCESSOR_PATH=/app/models/preprocessor.joblib
ENV BKT_CONFIG_PATH=/app/models/bkt_config.json
ENV FCL_MAPPING_PATH=/app/models/fcl_mapping.json
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
