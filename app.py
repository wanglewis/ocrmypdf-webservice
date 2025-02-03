from flask import Flask, render_template, request, send_file
import os
import uuid
import subprocess
import shutil  # 新增导入
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf'}

# === 新增安全保存函数 ===
def save_upload(file, save_path):
    """安全保存上传文件的核心方法"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 分块写入并验证
        with open(save_path, 'wb') as f:
            file.save(f)  # 使用 Werkzeug 的保存方法
            f.flush()     # 强制刷新缓冲区
            os.fsync(f.fileno())  # 确保写入物理磁盘
            
        # 二次验证文件完整性
        file_size = os.path.getsize(save_path)
        if file_size == 0:
            app.logger.error(f"文件保存后为空: {save_path}")
            os.remove(save_path)
            return False, 0
        return True, file_size
    except Exception as e:
        app.logger.error(f"保存失败: {str(e)}")
        if os.path.exists(save_path):
            os.remove(save_path)
        return False, 0

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        upload_dir = None  # 初始化用于 finally 清理
        try:
            # === 基础验证 ===
            if 'file' not in request.files:
                app.logger.error("请求中未包含文件")
                return 'No file uploaded', 400
                
            file = request.files['file']
            if file.filename == '':
                app.logger.error("文件名为空")
                return 'No selected file', 400
                
            if not allowed_file(file.filename):
                app.logger.error("不允许的文件类型")
                return 'Invalid file type', 400

            # === 创建临时目录 ===
            upload_id = str(uuid.uuid4())
            upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
            os.makedirs(upload_dir, exist_ok=True)

            # === 安全保存文件 ===
            original_filename = secure_filename(file.filename)
            original_path = os.path.abspath(os.path.join(upload_dir, original_filename))
            
            # 调用安全保存方法
            save_success, file_size = save_upload(file, original_path)
            if not save_success:
                return "文件保存失败，请检查存储权限", 500
                
            app.logger.info(f"文件保存成功: {original_path} ({file_size}字节)")

            # === OCR 处理 ===
            output_path = os.path.abspath(os.path.join(upload_dir, 'output.pdf'))
            app.logger.info(f"开始处理: {original_path} → {output_path}")

            # 执行 OCR 命令
            result = subprocess.run(
                ['ocrmypdf', '-l', 'eng+chi_sim', '--deskew', original_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )
            app.logger.debug(f"OCR输出: {result.stdout}")

            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise Exception("OCR 处理失败，输出文件无效")

            # === 返回结果 ===
            response = send_file(
                output_path,
                as_attachment=True,
                download_name='processed.pdf'
            )
            
            # 添加清理回调（在响应发送后清理）
            @response.call_on_close
            def cleanup():
                try:
                    if upload_dir and os.path.exists(upload_dir):
                        shutil.rmtree(upload_dir)
                        app.logger.info(f"已清理临时目录: {upload_dir}")
                except Exception as e:
                    app.logger.error(f"清理失败: {str(e)}")
                    
            return response

        except subprocess.CalledProcessError as e:
            error_msg = f"""OCR 处理失败！
            命令: {e.cmd}
            错误码: {e.returncode}
            错误输出:
            {e.stderr}
            """
            app.logger.error(error_msg)
            return error_msg, 500
            
        except Exception as e:
            app.logger.error(f"处理异常: {str(e)}", exc_info=True)
            return f"处理失败: {str(e)}", 500
            
        finally:
            # 双保险清理（如果回调未执行）
            try:
                if upload_dir and os.path.exists(upload_dir):
                    shutil.rmtree(upload_dir)
            except Exception as e:
                app.logger.error(f"最终清理失败: {str(e)}")

    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)