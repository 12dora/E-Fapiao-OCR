FROM python:3.11-slim

# pyzbar 需要 zbar 系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
        libzbar0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY app ./app

EXPOSE 8000

# 单实例 ≥ 20 QPS 目标：4 worker 起步，可由编排平台调副本数横向扩展
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
