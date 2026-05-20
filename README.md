# E-Fapiao-OCR

轻量级**数电发票 PDF 解析 API 服务**。把发票文件 → 结构化 JSON，仅此一事。

- 设计文档：见 [DESIGN.md](DESIGN.md)
- 开发进度：见 [PROGRESS.md](PROGRESS.md)
- Coding Agent 提示词：见 [AGENT_GUIDE.md](AGENT_GUIDE.md)

## 快速开始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

访问 <http://localhost:8000/docs> 查看自动生成的 OpenAPI 文档。

## 一期范围（MVP）

- 数电普票 / 数电专票 / 12306 客票 PDF 解析
- 统一 JSON Schema 输出
- Webhook 透传
- API Key 鉴权

## 不做

- 发票验真、持久化、报销审批、用户体系、前端 UI
