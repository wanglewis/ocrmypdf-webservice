import os
import uuid
import hashlib
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.websocket import WebSocket
import subprocess
import asyncio

# 安全中间件配置
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST"],
        max_age=600
    )
]

app = FastAPI(middleware=middleware)

@app.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            # 保持连接开放
            await asyncio.sleep(1)
            if await websocket.receive_text():
                continue
    except Exception as e:
        logger.error(f"WebSocket 连接异常: {str(e)}")
        await websocket.close()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

# 配置常量
UPLOAD_DIR = "/tmp/uploads"
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 默认50MB
ALLOWED_MIME = {'application/pdf'}

@app.get("/health")
async def health_check():
    return {"status": "OK"}

@app.post("/ocr")
async def process_pdf(file: UploadFile = File(...)):
    try:
        # 安全检查
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(400, "Invalid file type")

        # 内存安全读取
        file_bytes = await file.read(MAX_FILE_SIZE + 1)
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE} bytes limit")

        # 生成唯一ID
        file_id = hashlib.md5(file_bytes).hexdigest()

        input_path = os.path.join(UPLOAD_DIR, f"{file_id}_input.pdf")
        output_path = os.path.join(UPLOAD_DIR, f"{file_id}_output.pdf")

        # 写入临时文件
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        # 执行OCR命令
        ocr_process = await asyncio.create_subprocess_exec(
            'ocrmypdf',
            input_path,
            output_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 等待子进程完成
        stdout, stderr = await ocr_process.communicate()

        if ocr_process.returncode != 0:
            raise Exception(f"OCR 失败，错误信息: {stderr.decode()}")

        # 发送响应
        with open(output_path, "rb") as f:
            file_content = f.read()
        
        return FileResponse(
            content=file_content,
            filename=f"output_{file_id}.pdf",
            media_type="application/pdf"
        )

    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 删除临时文件
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            logger.error(f"删除临时文件时出错: {str(e)}")