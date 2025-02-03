import os
import asyncio
from fastapi import WebSocket

class OCRProcessor:
    def __init__(self, websocket: WebSocket = None):
        self.websocket = websocket
        self.progress = 0

    async def update_progress(self, message: str, percentage: int):
        self.progress = percentage
        if self.websocket:
            await self.websocket.send_json({
                "status": "processing",
                "message": message,
                "percentage": percentage
            })

    async def process(self, input_path: str, output_path: str):
        # 模拟分阶段进度更新
        await self.update_progress("开始解析PDF", 10)
        await asyncio.sleep(1)  # 实际替换为解析操作
        
        await self.update_progress("进行文字识别", 30)
        await asyncio.sleep(2)  # 实际替换为OCR操作
        
        await self.update_progress("优化输出文件", 70)
        os.system(f"ocrmypdf -l chi_sim+eng --force-ocr {input_path} {output_path}")
        
        await self.update_progress("处理完成", 100)
        await asyncio.sleep(0.5)