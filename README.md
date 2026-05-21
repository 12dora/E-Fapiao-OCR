# E-Fapiao-OCR

轻量级**数电发票 PDF 解析 API 服务**。把发票文件 → 结构化 JSON，仅此一事。

- 设计文档：见 [DESIGN.md](DESIGN.md)
- API 文档：见 [docs/API.md](docs/API.md)
- 开发进度：见 [PROGRESS.md](PROGRESS.md)
- Coding Agent 提示词：见 [AGENT_GUIDE.md](AGENT_GUIDE.md)

## 快速开始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

访问 <http://localhost:8000/docs> 查看自动生成的 OpenAPI 文档。

## 规则引擎与 OCR

默认安装即可解析带文本层的 PDF 发票、12306 客票和航空行程单 OFD，不依赖在线 OCR 或本地 OCR 模型。图片、扫描件 PDF、轮廓/图片型 OFD 只有在规则引擎无法读取文本时才需要 OCR。

HTTP 与 CLI 都支持 `ocr_mode`：

- `auto`：默认。先用规则引擎；只有图片或需 OCR 的路径会尝试已配置的 vendor。
- `disabled`：纯规则模式。不调用本地/在线 OCR；规则无法处理时返回 `rule_unhandled` 或 `not_implemented`。
- `required`：要求 OCR 能力的场景使用；图片输入未配置 OCR 时直接返回 `not_implemented`。

规则引擎未能处理时，API 会在错误响应的 `engine` 字段中告知 `ocr_required=true`、`ocr_enabled` 和本次 `ocr_mode`，上游可据此放入 OCR 队列或人工核对队列。

## OCR vendor（可选）

如需启用 OCR，选择一个 vendor：

```bash
# 本地 CnOCR，纯 CPU / x86_64 / arm64 推荐 ONNX backend
pip install -e ".[ocr-cnocr]"
export EFAPIAO_OCR_VENDOR=cnocr
export EFAPIAO_CNOCR_DET_MODEL=ch_PP-OCRv5_det
export EFAPIAO_CNOCR_REC_MODEL=doc-densenet_lite_136-gru
```

或使用第三方 OCR API：

```bash
export EFAPIAO_OCR_VENDOR=http
export EFAPIAO_OCR_HTTP_URL=https://example.com/ocr
export EFAPIAO_OCR_HTTP_HEADERS='Authorization:Bearer xxx'
```

第三方 HTTP OCR 默认强制 HTTPS，并拒绝 localhost / 内网地址；本地 mock 服务调试时才设置：

```bash
export EFAPIAO_OCR_HTTP_ALLOW_HTTP=true
```

或使用腾讯云通用票据识别高级版：

```bash
export EFAPIAO_OCR_VENDOR=tencent
export EFAPIAO_TENCENT_SECRET_ID=AKID...
export EFAPIAO_TENCENT_SECRET_KEY=...
export EFAPIAO_TENCENT_REGION=ap-guangzhou
```

二进制 / 子进程集成时，推荐用环境变量或凭据文件传入腾讯云密钥，避免出现在命令行参数中：

```bash
export EFAPIAO_TENCENT_CREDENTIALS_FILE=/run/secrets/tencent-ocr.json
```

凭据文件格式：

```json
{
  "secret_id": "AKID...",
  "secret_key": "...",
  "token": "临时密钥可选",
  "region": "ap-guangzhou"
}
```

Python 源码集成时，可用 context 为当前调用临时注入密钥，适合多租户或宿主应用自行管理 KMS/STS：

```python
from app.ocr import tencent_ocr_credentials
from app.sdk import parse_invoice

with tencent_ocr_credentials(secret_id="AKID...", secret_key="...", token=None):
    result = parse_invoice(image_bytes, hint_type="image")
```

启用 OCR 后，解析结果会在 `data.source.ocr_vendor` 标出实际 vendor（`cnocr` / `http` / `tencent`），便于调用方做审计、灰度或效果对比。

第三方 OCR API 返回以下任一 JSON：

```json
{"text": "整页 OCR 文本"}
```

```json
{"lines": [{"text": "电子发票(普通发票)", "score": 0.99, "bbox": [[0, 0], [1, 0], [1, 1], [0, 1]]}]}
```

## 一期范围（MVP）

- 数电普票 / 数电专票 / 12306 客票 PDF 解析
- 成功响应返回 `document_type` 表示单据大类；例如 PDF 发票为 `pdf-fapiao`，再用 `invoice_type=digital_general` / `digital_special` 区分普票 / 专票
- 航空运输电子客票行程单 OFD 解析（按 OFD 内部 XBRL/OFD 内容识别，不依赖文件名）
- 图片航空运输电子客票行程单可在启用 OCR vendor 后解析，返回 `document_type=image-air-itinerary`
- OFD 发票内容识别：可按 OFD 内容判断为发票，但不解析字段，接口返回 `501 not_implemented`
  - 已识别为 OFD 发票时，错误响应返回 `document_type=ofd-fapiao`
  - 文本层 OFD 直接按内部文本识别
  - 轮廓 / 图片型 OFD 需要配置 OCR vendor 才能按图片内容识别
- 统一 JSON Schema 输出
- Webhook 透传
- API Key 鉴权
- OCR vendor 接口预留：CnOCR / 第三方 HTTP API / 腾讯云，默认关闭

## 二进制发布

项目支持把 CLI/HTTP 服务入口编译为单文件二进制：

```bash
pip install -e ".[build-bin]"
python scripts/build_binary.py --version v0.1.0
```

产物位于 `dist/`，命名遵循：

```text
efapiao-<semver>-<os>-<arch>.tar.gz
efapiao-<semver>-windows-x86_64.zip
```

GitHub Release 使用 SemVer tag 触发，例如：

```bash
git tag v0.1.0
git push origin v0.1.0
```

Release workflow 会构建 `linux-x86_64`、`linux-arm64`、`darwin-x86_64`、`darwin-arm64`、`windows-x86_64`，并上传 `SHA256SUMS`。默认二进制包含规则引擎与 HTTP/腾讯 OCR vendor；本地 CnOCR 模型不打入默认 release 产物。

## 不做

- 发票验真、持久化、报销审批、用户体系、前端 UI
