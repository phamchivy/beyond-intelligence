FROM python:3.11-slim

# onnxruntime (rembg's backend) needs libgomp on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the matting weights in at build time -- otherwise the first
# request downloads u2netp.onnx from GitHub, and a cold container on
# venue wifi is a dead demo.
RUN python -c "from rembg import new_session; new_session('u2netp')"

COPY service/ service/

EXPOSE 8002
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8002"]
