import os
import uuid
import hashlib
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket
from ocr_processor import OCRProcessor
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
    except:
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

    try:
        # 创建 WebSocket 连接
        async with httpx.AsyncClient() as client:
            async with client.websocket_connect(
                f"ws://localhost:8000/ws/progress/{file_id}"
            ) as websocket:
                processor = OCRProcessor(websocket)
                await processor.process(input_path, output_path)
        # 写入文件
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        # 执行OCR
        ocr_args = os.getenv("OCRMYPDF_ARGS", "-l chi_sim+eng --force-ocr")
        exit_code = os.system(f"ocrmypdf {ocr_args} {input_path} {output_path}")
        
        if exit_code != 0 or not os.path.exists(output_path):
            raise HTTPException(500, detail=f"OCR failed with code {exit_code}")

        return FileResponse(
            output_path,
            headers={
                "X-OCR-Result": "success",
                "Content-Disposition": "attachment; filename=processed.pdf"
            }
        )
    finally:
        # 异步清理
        for path in [input_path, output_path]:
            if os.path.exists(path):
                os.unlink(path)