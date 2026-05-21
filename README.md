# E-Fapiao-OCR

E-Fapiao-OCR 是一个轻量级票据解析服务，用于把电子发票、铁路客票、航空行程单等文件解析成稳定的结构化 JSON。

它可以作为 Python 库直接嵌入，也可以通过 CLI 或本地 HTTP 服务被其他语言调用。默认优先使用规则引擎解析 PDF/OFD 文本层，不强制依赖在线 OCR 或本地 OCR 模型；当遇到图片、扫描件或轮廓型文档时，可按需接入 CnOCR、第三方 HTTP OCR 或腾讯云 OCR。

## 特性支持

| 能力 | 状态 | 说明 |
|---|---|---|
| PDF 数电普通发票 | 支持 | 返回 `document_type=pdf-fapiao`、`invoice_type=digital_general` |
| PDF 数电专用发票 | 支持 | 返回 `document_type=pdf-fapiao`、`invoice_type=digital_special` |
| PDF 12306 铁路电子客票 | 支持 | 返回 `document_type=pdf-rail-12306`、`invoice_type=rail_12306` |
| OFD 航空运输电子客票行程单 | 支持 | 按 OFD 内部 XML/XBRL 内容识别，不依赖文件名 |
| 图片航空行程单 / 图片发票 | 可选支持 | 需要启用 OCR vendor |
| OFD 发票 | 类型识别 | 可识别 `document_type=ofd-fapiao`，当前返回 501，不解析字段 |
| 纯规则模式 | 支持 | `ocr_mode=disabled` 时不会调用任何本地或在线 OCR |
| OCR vendor | 支持 | `cnocr` / `http` / `tencent`，默认关闭 |
| HTTP API | 支持 | FastAPI，内置 OpenAPI 文档 |
| CLI | 支持 | `efapiao parse` / `efapiao serve` / `efapiao capabilities` |
| Python SDK | 支持 | `from app.sdk import parse_invoice` |
| 单文件二进制 | 支持 | GitHub Release 提供多平台构建产物 |

## 安装

### 从源码运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

启动 HTTP 服务：

```bash
uvicorn app.main:app --reload
```

打开 <http://localhost:8000/docs> 查看 OpenAPI 文档。

### 使用 Release 二进制

从 [GitHub Releases](https://github.com/12dora/E-Fapiao-OCR/releases) 下载对应平台的压缩包：

```bash
efapiao --version
efapiao capabilities
efapiao parse invoice.pdf --pretty
efapiao serve --host 127.0.0.1 --port 8000
```

Linux 二进制在二维码兜底路径中需要系统提供 `libzbar`。

## 快速使用

### Python

```python
from app.sdk import parse_invoice

with open("invoice.pdf", "rb") as f:
    result = parse_invoice(f.read(), hint_type="auto", ocr_mode="auto")

print(result["document_type"], result["invoice_type"], result["invoice_number"])
```

### CLI

```bash
efapiao parse invoice.pdf --pretty
efapiao parse invoice.pdf --ocr-mode disabled
cat invoice.pdf | efapiao parse - --hint pdf
```

### HTTP

```bash
curl -F "file=@invoice.pdf" \
     -F "hint_type=auto" \
     -F "ocr_mode=auto" \
     http://127.0.0.1:8000/v1/invoices/parse
```

成功响应会包含外层类型字段，便于上游分流：

```json
{
  "status": "ok",
  "format": "pdf",
  "document_type": "pdf-fapiao",
  "invoice_type": "digital_general",
  "data": {
    "invoice_number": "26100000000000000001",
    "amount_with_tax": "211.00"
  },
  "engine": {
    "rule_engine": "attempted",
    "ocr_mode": "auto",
    "ocr_enabled": false,
    "ocr_used": false,
    "ocr_required": false,
    "ocr_vendor": null
  }
}
```

完整字段见 [API 文档](docs/API.md)。

## 实现原理

E-Fapiao-OCR 的核心是一个统一的解析流水线：

```text
bytes
  -> format detector
  -> parser(pdf / ofd / image)
  -> version adapter
  -> extractor
  -> normalizer
  -> JSON
```

各层职责尽量保持清晰：

| 模块 | 职责 |
|---|---|
| Format detector | 根据 magic bytes 和 OFD ZIP 结构判断 `pdf` / `ofd` / `image` |
| Parser | 从文件中提取可解析文本或结构化字段，例如 PDF 文本层、PDF 二维码、OFD XML |
| Version adapter | 根据标题和关键字选择具体 extractor，避免铁路客票、发票、行程单互相误分流 |
| Extractor | 针对具体票种抽取票号、日期、购销方、金额、行项目和特有字段 |
| Normalizer | 补齐统一 schema，规范金额、日期、`document_type`、`invoice_type` 和来源信息 |
| OCR vendor | 只作为图片/扫描件兜底输入，OCR 文本仍回到统一 pipeline 处理 |

规则引擎优先处理可复制文本和结构化 XML。这样在纯 CPU、离线或没有 OCR 凭据的场景下，文本层 PDF、二维码 PDF、航空行程单 OFD 仍可稳定解析。规则引擎无法覆盖时，错误响应会带上 `engine.ocr_required=true`，调用方可以把文件放入 OCR 队列或人工核对队列。

## OCR 配置

OCR 默认关闭：

```bash
export EFAPIAO_OCR_VENDOR=none
```

启用本地 CnOCR：

```bash
pip install -e ".[ocr-cnocr]"
export EFAPIAO_OCR_VENDOR=cnocr
export EFAPIAO_CNOCR_DET_BACKEND=onnx
export EFAPIAO_CNOCR_REC_BACKEND=onnx
```

启用第三方 HTTP OCR：

```bash
export EFAPIAO_OCR_VENDOR=http
export EFAPIAO_OCR_HTTP_URL=https://example.com/ocr
export EFAPIAO_OCR_HTTP_HEADERS='Authorization:Bearer xxx'
```

HTTP OCR 默认强制 HTTPS，并拒绝 localhost、内网和链路本地地址，避免把 OCR 配置变成 SSRF 通道。

启用腾讯云通用票据识别：

```bash
export EFAPIAO_OCR_VENDOR=tencent
export EFAPIAO_TENCENT_SECRET_ID=AKID...
export EFAPIAO_TENCENT_SECRET_KEY=...
export EFAPIAO_TENCENT_REGION=ap-guangzhou
```

二进制或子进程集成推荐使用凭据文件：

```bash
export EFAPIAO_TENCENT_CREDENTIALS_FILE=/run/secrets/tencent-ocr.json
```

```json
{
  "secret_id": "AKID...",
  "secret_key": "...",
  "token": "临时密钥可选",
  "region": "ap-guangzhou"
}
```

Python 源码集成可以用 context 临时注入密钥，适合多租户或宿主应用自行管理 KMS/STS：

```python
from app.ocr import tencent_ocr_credentials
from app.sdk import parse_invoice

with tencent_ocr_credentials(secret_id="AKID...", secret_key="...", token=None):
    result = parse_invoice(image_bytes, hint_type="image")
```

## 解析模式

HTTP、CLI 和 Python SDK 都支持 `ocr_mode`：

| `ocr_mode` | 行为 |
|---|---|
| `auto` | 默认。优先规则引擎；图片或需要 OCR 的路径在 vendor 已配置时使用 OCR |
| `disabled` | 纯规则模式。不调用本地或在线 OCR |
| `required` | 图片输入要求 OCR；未配置 OCR vendor 时返回 `not_implemented` |

规则未覆盖时的典型错误：

```json
{
  "status": "error",
  "code": "rule_unhandled",
  "message": "规则引擎无法解析该 PDF：文本层内容过少且未找到二维码；当前未配置 OCR vendor",
  "engine": {
    "ocr_mode": "disabled",
    "ocr_enabled": false,
    "ocr_used": false,
    "ocr_required": true
  }
}
```

## 鉴权

本机集成默认不启用 API Key。设置 `EFAPIAO_API_KEY` 后，`/v1/invoices/*` 需要携带 `X-API-Key`：

```bash
export EFAPIAO_API_KEY=your-key

curl -H "X-API-Key: your-key" \
     -F "file=@invoice.pdf" \
     http://127.0.0.1:8000/v1/invoices/parse
```

## 构建二进制

本地构建当前平台：

```bash
pip install -e ".[build-bin]"
python scripts/build_binary.py --version v0.1.2
```

产物位于 `dist/`：

```text
efapiao-<semver>-<os>-<arch>.tar.gz
efapiao-<semver>-windows-x86_64.zip
```

GitHub Release 由 SemVer tag 触发：

```bash
git tag v0.1.2
git push origin v0.1.2
```

默认发布 `linux-x86_64`、`linux-arm64`、`darwin-arm64`、`windows-x86_64`，并生成 `SHA256SUMS`。

Release 构建会排除开发工具、Uvicorn 热重载/WebSocket 扩展、Pillow 罕见图片格式插件等可选模块；PDF 文本抽取和渲染统一使用 `pypdfium2`，避免同时打包 `pdfminer/cryptography` 这类大依赖。

## 测试

测试集使用脱敏合成数据，不依赖真实发票样本：

```bash
pytest -q
ruff check app tests scripts
```

当前覆盖 PDF 发票、12306 客票、OFD 行程单、OFD 发票类型识别、OCR vendor、HTTP/CLI 契约、URL 安全和纯规则模式。

## 文档

- [API 文档](docs/API.md)
- [设计文档](DESIGN.md)
- [开发进度](PROGRESS.md)
