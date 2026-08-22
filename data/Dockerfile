FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/opt/fastembed

WORKDIR /app
# Only the API's own runtime deps -- not the Dagster pipeline / ingestion
# scripts / test suite, which pull in docling, dagster, dlt, scikit-learn
# and friends that this image never imports. See requirements-api.txt.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Bake the embedding model. A 200 MB download on first use at the venue
# is a self-inflicted outage.
RUN python -c "from fastembed import TextEmbedding; \
    TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Only what api.py's import graph actually touches (see lib/*.py) --
# not contracts/, defs/, scripts/, tests/, business/, evaluation/.
COPY api.py .
COPY lib/ lib/
COPY sql/ sql/
EXPOSE 8002
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
