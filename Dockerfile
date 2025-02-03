FROM python:3.9-slim

# 系统依赖 + 中文字体
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    ghostscript \
    poppler-utils \
    fonts-wqy-zenhei \  # 文泉驿中文字体
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 ocruser
WORKDIR /app
RUN chown ocruser:ocruser /app

USER ocruser

COPY --chown=ocruser:ocruser app/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=ocruser:ocruser app/ .

# 性能优化
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UVICORN_WORKERS=4

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]