from flask import Flask, render_template, request, send_file
import os
import uuid
import subprocess
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file uploaded', 400
            
        file = request.files['file']
        if file.filename == '':
            return 'No selected file', 400
            
        if file and allowed_file(file.filename):
            # 创建临时目录
            upload_id = str(uuid.uuid4())
            upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
            os.makedirs(upload_dir, exist_ok=True)
            
            # 保存原始文件
            original_path = os.path.join(upload_dir, secure_filename(file.filename))
            file.save(original_path)
            
            # 处理文件
            output_path = os.path.join(upload_dir, 'output.pdf')
            try:
                # 确保输出目录存在
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir, exist_ok=True)
                
                # 使用绝对路径处理文件
                original_path = os.path.abspath(os.path.join(upload_dir, secure_filename(file.filename)))
                output_path = os.path.abspath(os.path.join(upload_dir, 'output.pdf'))
                
                # 保存文件时验证路径
                file.save(original_path)
                if not os.path.exists(original_path):
                    raise Exception("Failed to save uploaded file")
                
                # 添加详细的日志记录
                app.logger.info(f"Processing file: {original_path}")
                app.logger.info(f"Output path: {output_path}")
                
                # 使用 subprocess 替代 os.system
                result = subprocess.run(
                    ['ocrmypdf', '-l', 'eng+chi_sim', '--deskew', original_path, output_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # 验证输出文件
                if not os.path.exists(output_path):
                    app.logger.error(f"OCR output not found at {output_path}")
                    raise Exception("OCR processing failed to create output file")
                    
            except subprocess.CalledProcessError as e:
                error_msg = f"""
                OCR Processing Failed!
                Command: {e.cmd}
                Exit code: {e.returncode}
                Error output:
                {e.stderr}
                """
                app.logger.error(error_msg)
                return error_msg, 500
            
            # 返回处理后的文件
            return send_file(
                output_path,
                as_attachment=True,
                download_name='processed.pdf'
            )
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)