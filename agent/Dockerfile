# Vi tri file nay: agent/Dockerfile
#
# Dong goi agent/ thanh 1 Docker image doc lap -- theo dung quy uoc da
# chot trong docs/architecture/integration-architecture.md muc 2:
# base image python:3.12-slim, port noi bo 8001.

FROM python:3.12-slim

WORKDIR /app

# Cai dependency truoc, tan dung Docker layer cache -- code doi thuong
# xuyen hon requirements.txt, tach rieng buoc nay giup build lai nhanh hon.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toan bo source code cua agent/ vao /app -- tuong duong WORKDIR
# ben trong container CHINH LA thu muc agent/ ben ngoai, dung dung quy
# uoc "luon chay tu agent/" da thong nhat tu dau du an.
COPY . .

# KHONG copy .env that vao image (da co trong .dockerignore) -- gia tri
# that truyen vao luc `docker run`/docker-compose qua environment,
# khong bao gio bake cung image.

EXPOSE 8001

# Healthcheck o muc Docker (bo sung cho /health endpoint da co) -- Docker
# tu dong danh dau container "unhealthy" neu /health tra ve loi, giup
# docker-compose depends_on: condition: service_healthy hoat dong dung.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

CMD ["uvicorn", "interface.api.main:app", "--host", "0.0.0.0", "--port", "8001"]