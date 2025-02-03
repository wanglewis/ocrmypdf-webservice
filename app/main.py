import os
import uuid
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Optional
from app.ocr_processor import OCRProcessor
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ocr-service")

app = FastAPI(title="OCR PDF Web Service")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 环境变量配置
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/uploads"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 默认50MB
OCR_ARGS = os.getenv("OCR_ARGS", "-l eng+chi_sim --rotate-pages --deskew --jobs 4").split()

# 初始化目录
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class OCRProcessor:
    """OCR 处理核心类"""
    
    def __init__(
        self,
        task_id: str,
        input_path: Path,
        output_path: Path,
        websocket: Optional[WebSocket] = None
    ):
        self.task_id = task_id
        self.input_path = input_path
        self.output_path = output_path
        self.websocket = websocket
        self.progress = 0
        
    async def _update_progress(self, message: str, progress: int):
        """更新处理进度"""
        self.progress = progress
        if self.websocket:
            try:
                await self.websocket.send_json({
                    "task_id": self.task_id,
                    "status": "processing",
                    "message": message,
                    "progress": progress
                })
            except WebSocketDisconnect:
                logger.warning("WebSocket 连接已断开")

    async def process(self, input_path: Path, output_path: Path):
        """执行 OCR 处理流程"""
        try:
            await self._update_progress("开始处理文件", 10)
            
            # 验证输入文件
            if not input_path.exists():
                raise FileNotFoundError("输入文件不存在")
                
            await self._update_progress("执行OCR识别", 30)
            
            # 构建 ocrmypdf 命令
            cmd = [
                "ocrmypdf",
                *OCR_ARGS,
                str(input_path),
                str(output_path)
            ]
            
            # 异步执行处理
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 实时读取输出
            async def read_stream(stream, is_error=False):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    msg = line.decode().strip()
                    logger.debug(f"{'ERROR' if is_error else 'INFO'}: {msg}")
                    
            await asyncio.gather(
                read_stream(process.stdout),
                read_stream(process.stderr, is_error=True)
            )
            
            exit_code = await process.wait()
            if exit_code != 0:
                raise RuntimeError(f"OCR处理失败，退出码：{exit_code}")
                
            await self._update_progress("优化输出文件", 90)
            
            if not output_path.exists():
                raise FileNotFoundError("输出文件生成失败")
            
            await self._update_progress("处理完成", 100)
            
        except Exception as e:
            logger.error(f"处理任务 {self.task_id} 失败：{str(e)}")
            await self._update_progress(f"处理失败：{str(e)}", 100)
            raise

@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """返回 Web 界面"""
    return FileResponse("static/index.html")

@app.websocket("/ws/progress")
async def progress_websocket(websocket: WebSocket):
    """WebSocket 进度通知"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 维持连接心跳
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WebSocket 连接断开")

@app.post("/ocr")
async def process_pdf(file: UploadFile = File(...), websocket: WebSocket = None):
    """处理 PDF 文件上传"""
    # 验证文件类型
    if file.content_type != "application/pdf":
        raise HTTPException(400, "仅支持 PDF 文件")
    
    # 验证文件大小
    file_bytes = await file.read(MAX_FILE_SIZE + 1)
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(413, f"文件大小超过 {MAX_FILE_SIZE//1024//1024}MB 限制")
    
    # 生成文件指纹
    file_hash = hashlib.md5(file_bytes).hexdigest()
    task_id = f"{file_hash}_{uuid.uuid4().hex[:8]}"
    input_path = UPLOAD_DIR / f"{task_id}_input.pdf"
    output_path = UPLOAD_DIR / f"{task_id}_output.pdf"
    
    # 保存文件到临时路径
    with open(input_path, "wb") as f:
        f.write(file_bytes)
    logger.info(f"文件已保存至 {input_path}")
    
    try:
        # 创建 OCRProcessor 实例
        processor = OCRProcessor(
            task_id=task_id,
            input_path=input_path,
            output_path=output_path,
            websocket=websocket
        )
        
        # 正确调用（无参数）
        success = await processor.process()

        if not success:
            raise HTTPException(500, "OCR处理失败")
        
        # 返回处理后的文件
        return FileResponse(
            output_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={task_id}_output.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"处理失败：{str(e)}")
        raise HTTPException(500, f"处理失败：{str(e)}")
        
    finally:
        # 清理临时文件
        for path in [input_path, output_path]:
            if path.exists():
                try:
                    path.unlink()
                    logger.debug(f"已清理临时文件：{path}")
                except Exception as clean_error:
                    logger.warning(f"文件清理失败：{clean_error}")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "OK", "version": "1.2.0"}