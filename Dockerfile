FROM python:3.9-slim

# 安装最小依赖集
RUN apt-get update && apt-get install -y \
    ocrmypdf \  # 核心依赖
    ghostscript \  # PDF处理
    poppler-utils \  # PDF工具
    && rm -rf /var/lib/apt/lists/*

# 创建非特权用户
RUN useradd -m ocruser
USER ocruser
WORKDIR /app

# 安装Python依赖
COPY --chown=ocruser requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=ocruser app/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]