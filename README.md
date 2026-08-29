# 图片转数据工具 - RapidOCR轻量版部署说明

## 变更说明

本次更新将 OCR 引擎从 **PaddleOCR**（内存~400MB）替换为 **RapidOCR**（内存~100MB），
使应用能够在 **Render 免费版（512MB 内存）** 上稳定运行。

## 文件清单

| 文件 | 说明 | 操作 |
|------|------|------|
| `app.py` | 完整应用（Flask + 异步任务 + RapidOCR图表提取） | 替换根目录旧文件 |
| `requirements.txt` | 依赖列表（已移除 paddlepaddle/paddleocr） | 替换根目录旧文件 |
| `render.yaml` | Render 部署配置（可选） | 如使用Blueprint则替换 |

## 部署步骤

### 1. 下载文件

- [app.py](sandbox:///mnt/agents/output/app.py)
- [requirements.txt](sandbox:///mnt/agents/output/requirements.txt)
- [render.yaml](sandbox:///mnt/agents/output/render.yaml)（可选）

### 2. 替换项目文件

```bash
# 在你的 ImgToDataApp 项目根目录
# 用下载的新文件替换旧的 app.py 和 requirements.txt
```

确保项目结构：
```
ImgToDataApp/
├── app.py              ← 新文件（RapidOCR版）
├── requirements.txt    ← 新文件（轻量依赖）
├── render.yaml         ← 可选
└── static/
    └── index.html
```

### 3. 推送部署

```bash
git add app.py requirements.txt
git commit -m "替换PaddleOCR为RapidOCR轻量版，适配Render免费版内存"
git push origin main
```

Render 会自动检测到变更并重新部署。

## 关键改进

| 项目 | 旧版（PaddleOCR） | 新版（RapidOCR） |
|------|------------------|-----------------|
| 内存占用 | ~400MB | ~100MB |
| Render免费版兼容性 | ❌ 崩溃（OOM） | ✅ 稳定运行 |
| 模型下载时间 | 3-5分钟 | 30秒-1分钟 |
| 识别精度 | 高（复杂图表） | 中高（一般够用） |
| 启动速度 | 慢（20-40秒） | 快（5-10秒） |

## 注意事项

1. **首次部署**：RapidOCR 会自动下载 ONNX 模型（~50MB），首次构建可能需要 **1-2 分钟**
2. **冷启动**：Render 免费版 15 分钟无访问会休眠，首次访问需要 **5-10 秒** 唤醒
3. **识别精度**：RapidOCR 对复杂图表（如负荷面板的多曲线重叠）的识别精度可能略低于 PaddleOCR，但电价/电量等简单面板完全够用

## 本地测试（可选）

```bash
pip install -r requirements.txt
python app.py
# 访问 http://localhost:5000
```

## 故障排查

如果部署后仍有问题，请检查 Render Dashboard → Logs：

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'rapidocr_onnxruntime'` | 依赖未安装 | 确认 requirements.txt 已推送 |
| `OCR 引擎初始化失败` | 模型下载失败 | 重新部署或检查网络 |
| 处理结果为空 | 图片质量问题 | 上传更高质量的截图 |
