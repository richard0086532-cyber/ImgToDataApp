import os
import time
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from tasks import start_background_task
from storage import get_task, cleanup_old_tasks, TaskStatus, RESULTS_DIR

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# 配置
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/upload', methods=['POST'])
def upload():
    """接收图片，立即返回 task_id"""
    if 'image' not in request.files:
        return jsonify({"error": "没有上传文件"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "文件名为空"}), 400
    
    # 读取文件内容
    image_bytes = file.read()
    if len(image_bytes) > MAX_CONTENT_LENGTH:
        return jsonify({"error": "文件超过 5MB 限制"}), 413
    
    # 启动后台任务
    task_id = start_background_task(image_bytes)
    
    return jsonify({
        "task_id": task_id,
        "message": "任务已创建",
        "check_url": f"/api/status/{task_id}"
    })

@app.route('/api/status/<task_id>', methods=['GET'])
def status(task_id):
    """查询任务状态"""
    task = get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    
    # 清理敏感信息
    response = {
        "task_id": task_id,
        "status": task.get("status"),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at")
    }
    
    # 只有完成或失败才返回详细结果
    if task.get("status") == TaskStatus.COMPLETED:
        response["result"] = task.get("result")
    elif task.get("status") == TaskStatus.FAILED:
        response["error"] = task.get("message")
        # 生产环境不要返回完整 traceback
        if os.getenv('FLASK_DEBUG'):
            response["traceback"] = task.get("error")
    
    return jsonify(response)

@app.route('/api/download/<task_id>/<format>', methods=['GET'])
def download(task_id, format):
    """下载结果文件"""
    if format not in ['csv', 'json']:
        return jsonify({"error": "格式不支持"}), 400
    
    filepath = os.path.join(RESULTS_DIR, f"{task_id}.{format}")
    if not os.path.exists(filepath):
        return jsonify({"error": "文件不存在"}), 404
    
    mime_types = {'csv': 'text/csv', 'json': 'application/json'}
    return send_file(
        filepath,
        mimetype=mime_types[format],
        as_attachment=True,
        download_name=f"result_{task_id}.{format}"
    )

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """手动清理旧任务（可选，也可加定时器）"""
    cleanup_old_tasks()
    return jsonify({"message": "清理完成"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
