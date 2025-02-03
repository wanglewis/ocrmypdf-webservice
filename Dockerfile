# 使用官方 Python 精简镜像
FROM python:3.11-slim-bookworm as builder

# 第一阶段：构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 第二阶段：运行时镜像
FROM python:3.11-slim-bookworm

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-chi-sim \
    ghostscript \
    poppler-utils \
    fonts-wqy-zenhei \
    # 前端渲染依赖
    libgl1 \
    libxcb-xinerama0 \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户和目录
RUN useradd -m -u 1000 ocruser && \
    mkdir -p /app/uploads && \
    chown -R ocruser:ocruser /app/uploads

WORKDIR /app
USER ocruser

# 从构建阶段复制依赖
COPY --from=builder /root/.local /home/ocruser/.local
ENV PATH="/home/ocruser/.local/bin:${PATH}"

# 复制应用文件
COPY --chown=ocruser:ocruser app/ ./app
COPY --chown=ocruser:ocruser app/static/ ./static

# 环境配置
ENV PYTHONPATH=/app \
    OCR_ARGS="-l eng+fra+chi_sim --rotate-pages --deskew --jobs 4 --output-type pdfa" \
    UPLOAD_DIR=/app/uploads \
    MAX_FILE_SIZE=52428800

EXPOSE 8000

# 使用高性能 ASGI 服务器
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--loop", "uvloop"]