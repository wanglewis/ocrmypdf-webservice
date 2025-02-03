import os
import asyncio
import logging
from pathlib import Path
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger("ocr-processor")

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

    async def _send_progress_update(self, message: str, progress: int):
        """发送进度更新到WebSocket"""
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
                logger.warning(f"任务 {self.task_id} 的WebSocket连接已断开")

    async def _execute_ocrmypdf(self):
        """执行ocrmypdf命令"""
        ocr_args = [
            "ocrmypdf",
            *os.getenv("OCR_ARGS", "-l eng+chi_sim --rotate-pages").split(),
            str(self.input_path),
            str(self.output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ocr_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 实时读取输出流
        async def log_stream(stream, prefix: str):
            while True:
                line = await stream.readline()
                if not line:
                    break
                logger.debug(f"[{self.task_id}] {prefix}: {line.decode().strip()}")

        await asyncio.gather(
            log_stream(process.stdout, "INFO"),
            log_stream(process.stderr, "ERROR")
        )

        return await process.wait()

    async def process(self):
        """完整处理流程"""
        try:
            # 阶段1: 初始化处理
            await self._send_progress_update("正在验证输入文件", 10)
            if not self.input_path.exists():
                raise FileNotFoundError(f"输入文件 {self.input_path} 不存在")

            # 阶段2: 执行OCR
            await self._send_progress_update("开始OCR文字识别", 30)
            exit_code = await self._execute_ocrmypdf()
            if exit_code != 0:
                raise RuntimeError(f"OCR处理失败，退出码：{exit_code}")

            # 阶段3: 验证输出
            await self._send_progress_update("正在验证输出结果", 90)
            if not self.output_path.exists():
                raise FileNotFoundError(f"输出文件 {self.output_path} 未生成")

            # 完成处理
            await self._send_progress_update("处理完成", 100)
            return True
            
        except Exception as e:
            logger.error(f"任务 {self.task_id} 处理失败: {str(e)}")
            await self._send_progress_update(f"处理失败: {str(e)}", 100)
            return False