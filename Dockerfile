FROM python:3.9-slim

# 设置非交互模式，防止 tzdata 之类的软件包安装时卡住
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 设定工作目录
WORKDIR /app

# 复制并安装 Python 依赖
COPY app/requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# 复制应用代码
COPY app/ .

# 设置 Python 运行环境
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 暴露端口
EXPOSE 8000

# 运行 FastAPI 服务器
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
