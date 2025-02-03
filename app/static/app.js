// app.js
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const progressBar = document.getElementById('progressBar');
const statusText = document.getElementById('statusText');
const resultArea = document.getElementById('resultArea');
const downloadBtn = document.getElementById('downloadBtn');
const pdfPreview = document.getElementById('pdfPreview');

let currentTaskId = null;

// 文件处理函数
async function handleFile(file) {
    if (!file.type.includes('pdf')) {
        showError('仅支持PDF文件');
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        showError('文件大小超过50MB限制');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    
    try {
        startUpload();
        const response = await fetch('/ocr', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('处理失败');
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        showResult(url);
    } catch (error) {
        showError(error.message);
    } finally {
        endUpload();
    }
}

// 可视化反馈函数
function startUpload() {
    progressBar.style.width = '0%';
    statusText.textContent = '开始上传...';
    resultArea.style.display = 'none';
}

function updateProgress(percentage, message) {
    progressBar.style.width = `${percentage}%`;
    statusText.textContent = message;
}

function showResult(url) {
    downloadBtn.href = url;
    pdfPreview.src = url;
    resultArea.style.display = 'block';
    updateProgress(100, '处理完成');
}

function showError(message) {
    statusText.textContent = `错误：${message}`;
    progressBar.style.backgroundColor = '#dc3545';
}

function endUpload() {
    setTimeout(() => {
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = '#4a90e2';
    }, 2000);
}

// 事件监听
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.backgroundColor = '#f8f9fa';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.backgroundColor = '';
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
});

dropZone.addEventListener('click', () => fileInput.click());