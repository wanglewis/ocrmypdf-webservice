# 第一阶段：构建依赖
FROM python:3.11-slim-bookworm as builder

# 设置构建参数
ARG DEBIAN_FRONTEND=noninteractive

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    libssl-dev=3.0.11-1~deb12u2 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --user --no-cache-dir -r requirements.txt

# 第二阶段：运行时镜像
FROM python:3.11-slim-bookworm

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr=5.3.0-1 \
    tesseract-ocr-eng=1:5.3.0-1 \
    tesseract-ocr-deu=1:5.3.0-1 \
    tesseract-ocr-chi-sim=1:5.3.0-1 \
    ghostscript=10.0.0~dfsg-11 \
    poppler-utils=22.12.0-2 \
    fonts-wqy-zenhei=0.9.45-8 \
    libgl1=1.6.0-1 \
    libxcb-xinerama0=1.15-1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非 root 用户
RUN useradd -m -u 1000 ocruser

# 创建必要的目录并设置权限
RUN mkdir -p /app/uploads \
    && chown -R ocruser:ocruser /app \
    && chmod 755 /app \
    && chmod 775 /app/uploads

WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=builder --chown=ocruser:ocruser /root/.local /home/ocruser/.local

# 复制应用文件（static 文件夹在 app 目录下）
COPY --chown=ocruser:ocruser app/ ./app
COPY --chown=ocruser:ocruser requirements.txt .

# 设置环境变量
ENV PATH="/home/ocruser/.local/bin:$PATH" \
    PYTHONPATH="/app" \
    PORT=8000

# 切换到非 root 用户
USER ocruser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]