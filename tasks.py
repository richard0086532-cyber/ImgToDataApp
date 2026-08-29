import threading
import uuid
import traceback
import os
from datetime import datetime
from storage import save_task, TaskStatus, RESULTS_DIR

# 导入真实的图表提取器
try:
    from chart_extractor_web import ChartExtractorAgent
    _REAL_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] 真实提取器导入失败: {e}")
    _REAL_EXTRACTOR_AVAILABLE = False

def run_ocr_task(task_id, image_bytes):
    """在后台线程中执行真实的图表提取"""

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
        "message": "任务已启动，正在初始化引擎...",
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })

    try:
        if not _REAL_EXTRACTOR_AVAILABLE:
            raise Exception("图表提取引擎未正确加载，请检查依赖安装")

        # 创建提取器实例
        agent = ChartExtractorAgent()

        # 执行提取（使用临时目录保存中间文件）
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = agent.process(
                image_bytes, 
                output_dir=tmpdir,
                progress_callback=update_progress
            )

            # 转换为Web格式
            web_result = agent.to_web_dict(result)

        # 生成导出文件到持久化目录
        _generate_exports(task_id, web_result)

        # 标记完成
        save_task(task_id, {
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "message": "处理完成",
            "result": web_result,
            "completed_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[ERROR] 任务 {task_id} 处理失败: {e}")
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
    import json
    import os

    # JSON
    json_path = os.path.join(RESULTS_DIR, f"{task_id}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # CSV
    csv_path = os.path.join(RESULTS_DIR, f"{task_id}.csv")
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(result.get("csv_data", ""))

def start_background_task(image_bytes):
    """启动后台任务，返回 task_id"""
    task_id = str(uuid.uuid4())[:12]

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
