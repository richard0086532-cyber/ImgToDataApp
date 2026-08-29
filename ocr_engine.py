import os
import io
import time
from PIL import Image
import numpy as np

# 你的 RapidOCR 导入
# from rapidocr_onnxruntime import RapidOCR

class OCREngine:
    def __init__(self):
        self.ocr = None
        self._init_lock = False
    
    def _lazy_init(self):
        """延迟初始化，避免启动时就加载模型"""
        if self.ocr is None and not self._init_lock:
            self._init_lock = True
            print("[INFO] 正在初始化 RapidOCR 引擎...")
            # self.ocr = RapidOCR()
            print("[INFO] RapidOCR 引擎初始化完成")
    
    def preprocess_image(self, image_bytes, max_size=1200):
        """预处理：压缩、转换格式"""
        img = Image.open(io.BytesIO(image_bytes))
        
        # 等比例缩放
        if max(img.width, img.height) > max_size:
            ratio = max_size / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # 转 RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存为 bytes
        output = io.BytesIO()
        img.save(output, format='PNG', optimize=True)
        return output.getvalue(), (img.width, img.height)
    
    def process(self, image_bytes, task_id, progress_callback):
        """
        主处理流程
        progress_callback: 回调函数，用于更新进度
        """
        self._lazy_init()
        
        try:
            # 1. 预处理
            progress_callback(10, "正在预处理图片...")
            processed_bytes, (w, h) = self.preprocess_image(image_bytes)
            
            # 2. OCR 识别
            progress_callback(30, "正在执行 OCR...")
            # result, elapse = self.ocr(processed_bytes)
            
            # 3. 面板识别（模拟你的逻辑）
            progress_callback(50, "正在识别面板...")
            # panel_data = self._detect_panels(result)
            
            # 4. 坐标轴标定
            progress_callback(60, "正在标定坐标轴...")
            # axis_data = self._calibrate_axis(panel_data)
            
            # 5. 曲线提取
            progress_callback(80, "正在提取曲线数据...")
            # curves = self._extract_curves(axis_data, image_bytes)
            
            # 模拟结果
            time.sleep(2)  # 模拟处理时间
            
            curves = [
                {"name": "green", "points": [(0.15, 1000), (5.5, 800), (10.0, 600), (15.2, 400), (22.87, 200)]},
                {"name": "blue", "points": [(0.15, 900), (5.5, 700), (10.0, 500), (15.2, 300), (22.87, 100)]}
            ]
            
            progress_callback(100, "处理完成")
            
            return {
                "success": True,
                "image_size": {"width": w, "height": h},
                "panels": [{"name": "price_2026-05-10", "rect": [6, 17, 509, 388]}],
                "axis": {"x": [0.15, 22.87], "y": [-198.95, 999.33]},
                "curves": curves,
                "total_curves": len(curves),
                "download": {
                    "csv": f"/download/{task_id}.csv",
                    "json": f"/download/{task_id}.json"
                }
            }
            
        except Exception as e:
            raise Exception(f"处理失败: {str(e)}")

# 全局单例
engine = OCREngine()