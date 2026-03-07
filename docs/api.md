# API 接口文档

> 说明：API 服务器模式为后续扩展功能。当前版本以 CLI 模式为主。

## 启动服务

```bash
uv run python main.py --serve --port 8000
```

## 接口列表

### POST /research

发起深度研究任务。

**请求体：**
```json
{
  "topic": "研究主题",
  "max_loops": 3
}
```

**响应：**
```json
{
  "status": "completed",
  "report": "Markdown 格式的研究报告",
  "metrics": {
    "word_count": 5000,
    "source_coverage": 8,
    "citation_accuracy": 0.9
  }
}
```

### GET /health

健康检查。

**响应：**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```
