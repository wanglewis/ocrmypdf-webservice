FROM python:3.9-slim

# 安装必要的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ocrmypdf \
    tesseract-ocr-deu \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -u 1000 ocruser
WORKDIR /app
RUN chown ocruser:ocruser /app

USER ocruser

# 确保 pip 安装的包能被找到
ENV PATH="/home/ocruser/.local/bin:$PATH"

# 安装 Python 依赖
COPY --chown=ocruser:ocruser app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=ocruser:ocruser app/static ./static
COPY --chown=ocruser:ocruser app/ .

# 性能优化
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UVICORN_WORKERS=4

EXPOSE 8000

# 使用 python -m 运行 uvicorn，避免 PATH 问题
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
