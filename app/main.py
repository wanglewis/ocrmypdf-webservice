import os
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/ocr")
async def process_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are accepted")

    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_DIR, f"{file_id}_input.pdf")
    output_path = os.path.join(UPLOAD_DIR, f"{file_id}_output.pdf")

    # 保存上传文件
    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        # 执行 OCR 处理
        os.system(f"ocrmypdf -l chi_sim+eng --force-ocr {input_path} {output_path}")
        
        if not os.path.exists(output_path):
            raise HTTPException(500, "OCR processing failed")
            
        return FileResponse(
            output_path,
            media_type='application/pdf',
            filename="processed.pdf"
        )
    finally:
        # 清理临时文件
        for f in [input_path, output_path]:
            if os.path.exists(f):
                os.remove(f)