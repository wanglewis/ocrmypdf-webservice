FROM python:3.9-slim

# 安装最小依赖集
RUN apt-get update && apt-get install -y \
    ocrmypdf \
    tesseract-ocr-deu \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    ghostscript \ 
    poppler-utils \ 
	fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 ocruser
WORKDIR /app
RUN chown ocruser:ocruser /app

USER ocruser

COPY app/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY app/static ./static
COPY app/ .

# 性能优化
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UVICORN_WORKERS=4
	PATH="/home/ocruser/.local/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]