FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    tesseract-ocr-deu \ 
    ghostscript \
    poppler-utils \
    libxml2-dev \
    libxslt1-dev \
    libleptonica-dev \
    libjpeg-dev \
    zlib1g-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopenjp2-7-dev \
    libpng-dev \
    qpdf \
	pngquant \          
    unpaper \         
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建有写入权限的临时目录
RUN mkdir -p /tmp/uploads && \
    chown -R root:root /tmp/uploads && \
    chmod -R 777 /tmp/uploads
	
	
ENV OCRMYPDF_DISABLE_DOCKER=1  
ENV LIBVA_DRIVER_NAME=iHD
ENV INTEL_OPENCL_ALLOW_CPU=0 

EXPOSE 5000

CMD ["python", "app.py"]