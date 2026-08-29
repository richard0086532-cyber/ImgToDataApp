import json
import os
import threading
from datetime import datetime, timedelta

# 内存中的任务状态
_tasks = {}
_lock = threading.RLock()
RESULTS_DIR = "/tmp/imgtodata_results"

os.makedirs(RESULTS_DIR, exist_ok=True)

class TaskStatus:
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败

def save_task(task_id, data):
    """保存任务状态到内存+文件"""
    with _lock:
        _tasks[task_id] = data
        # 同时写入文件，防止实例重启丢失
        filepath = os.path.join(RESULTS_DIR, f"{task_id}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"保存任务文件失败: {e}")

def get_task(task_id):
    """获取任务状态"""
    with _lock:
        # 先查内存
        if task_id in _tasks:
            return _tasks[task_id]
        
        # 内存没有，查文件（实例重启后）
        filepath = os.path.join(RESULTS_DIR, f"{task_id}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                _tasks[task_id] = data
                return data
            except Exception as e:
                print(f"读取任务文件失败: {e}")
                return None
        return None

def cleanup_old_tasks():
    """清理 24 小时前的任务文件"""
    cutoff = datetime.now() - timedelta(hours=24)
    for filename in os.listdir(RESULTS_DIR):
        filepath = os.path.join(RESULTS_DIR, filename)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
        except Exception:
            pass