# ChartExtractor 真实引擎部署说明

## 文件变更清单

1. **chart_extractor_web.py** → 项目根目录（Web适配版ChartExtractorAgent）
2. **tasks.py** → 替换为 tasks_v2.py 的内容（使用真实提取器）
3. **requirements.txt** → 替换为 requirements_v2.txt 的内容

## 关键修改点

### 1. chart_extractor_web.py（原ChartExtractorAgentV1.py的Web适配版）
- `preprocess_image()` 现在支持 `bytes` 输入（Web上传的图片）
- `process()` 添加 `progress_callback` 参数，实时报告进度
- 新增 `to_web_dict()` 方法，返回标准化的JSON/CSV格式
- 保留全部原始提取逻辑（OCR、面板检测、坐标轴标定、曲线提取、插值）

### 2. tasks.py
- 使用 `ChartExtractorAgent` 替代原来的mock `OCREngine`
- 通过 `tempfile.TemporaryDirectory()` 管理中间文件
- 自动调用 `to_web_dict()` 生成Web友好的结果

## Render 部署注意事项

### ⚠️ 内存警告（非常重要）
PaddleOCR + PaddlePaddle 模型文件很大，初始化时需要 **300~500MB** 内存。
Render 免费版只有 **512MB**，可能出现：
- 启动时内存不足崩溃（OOM）
- 并发处理时第二个任务必然失败

**解决方案：**
1. **升级到 Render Starter**（$7/月，1GB内存）—— 最推荐
2. **使用轻量版 OCR**（把 paddleocr 换成 rapidocr-onnxruntime，但需重写OCR调用部分）
3. **限制并发**：确保同时只处理1个任务（当前代码已限制为单线程）

### 部署步骤

```bash
# 1. 把生成的文件放入项目
git add chart_extractor_web.py tasks.py requirements.txt

# 2. 提交推送
git commit -m "集成真实ChartExtractorAgent图表提取引擎"
git push origin main

# 3. Render会自动重新部署
# 首次部署可能需要 3~5 分钟（PaddleOCR模型下载）
```

### 冷启动说明
- PaddleOCR 引擎初始化需要 **20~40 秒**
- 首次访问时，上传图片后需要等待引擎初始化 + 图片处理
- 建议上传后耐心等待，不要刷新页面

## 测试验证

上传 "出清price.png" 后，预期输出：
- **日前出清电价**（绿色曲线）
- **实时出清电价**（蓝色曲线）
- 96个时点（00:15 ~ 24:00）
- CSV 下载包含精确的电价数值

如果结果仍不准确，请检查：
1. 图片是否被压缩过度（建议上传原图或高质量截图）
2. 面板检测是否识别到正确的 "市场出清" 面板
3. Render Logs 中是否有 OCR 识别错误的警告
