import threading
import uuid
import traceback
from datetime import datetime
from storage import save_task, TaskStatus
from ocr_engine import engine

def run_ocr_task(task_id, image_bytes):
    """在后台线程中执行 OCR"""
    
    def update_progress(percent, message):
        save_task(task_id, {
            "status": TaskStatus.PROCESSING,
            "progress": percent,
            "message": message,
            "updated_at": datetime.now().isoformat()
        })
    
    # 标记为处理中
    save_task(task_id, {
        "status": TaskStatus.PROCESSING,
        "progress": 0,
        "message": "任务已启动",
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    
    try:
        # 执行 OCR
        result = engine.process(image_bytes, task_id, update_progress)
        
        # 生成导出文件
        _generate_exports(task_id, result)
        
        # 标记完成
        save_task(task_id, {
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "message": "处理完成",
            "result": result,
            "completed_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_trace = traceback.format_exc()
        save_task(task_id, {
            "status": TaskStatus.FAILED,
            "progress": 0,
            "message": str(e),
            "error": error_trace,
            "failed_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

def _generate_exports(task_id, result):
    """生成 CSV 和 JSON 导出文件"""
    import csv
    import json
    import os
    
    RESULTS_DIR = "/tmp/imgtodata_results"
    
    # JSON
    json_path = os.path.join(RESULTS_DIR, f"{task_id}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # CSV（每条曲线一个文件，或合并）
    csv_path = os.path.join(RESULTS_DIR, f"{task_id}.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["curve_name", "x", "y"])
        for curve in result.get("curves", []):
            for x, y in curve.get("points", []):
                writer.writerow([curve["name"], x, y])

def start_background_task(image_bytes):
    """启动后台任务，返回 task_id"""
    task_id = str(uuid.uuid4())[:12]  # 短 ID，方便使用
    
    # 先保存初始状态
    save_task(task_id, {
        "status": TaskStatus.PENDING,
        "progress": 0,
        "message": "等待处理",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    
    # 启动后台线程
    thread = threading.Thread(
        target=run_ocr_task,
        args=(task_id, image_bytes),
        daemon=True
    )
    thread.start()
    
    return task_id