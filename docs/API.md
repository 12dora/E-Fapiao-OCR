# E-Fapiao-OCR API 文档

本文档描述当前已实现的稳定接口。服务默认只监听本机，可通过 Python 库、CLI 或 HTTP
三种方式集成；三者共享同一套解析 pipeline。

## 1. 能力边界

| 类型 | `document_type` | `invoice_type` | 状态 |
|---|---|---|---|
| PDF 数电普票 | `pdf-fapiao` | `digital_general` | 支持 |
| PDF 数电专票 | `pdf-fapiao` | `digital_special` | 支持 |
| PDF 铁路电子客票 | `pdf-rail-12306` | `rail_12306` | 支持 |
| OFD 航空运输电子客票行程单 | `ofd-air-itinerary` | `air_itinerary` | 支持 |
| 图片航空运输电子客票行程单 | `image-air-itinerary` | `air_itinerary` | 需配置 OCR vendor |
| OFD 发票 | `ofd-fapiao` | `null` | 只识别类型，返回 501，不解析字段 |
| 图片发票 | `image-fapiao` | `digital_general` / `digital_special` | 需配置 OCR vendor |

默认不配置 OCR 时，PDF 文本层、PDF 二维码、OFD XML/TextCode 均可由规则引擎解析。

## 2. OCR 策略

`ocr_mode` 控制单次调用是否允许 OCR：

| 值 | 行为 |
|---|---|
| `auto` | 默认。先用规则引擎；图片或需 OCR 的路径在 vendor 已配置时使用 OCR。 |
| `disabled` | 纯规则模式。不调用本地或在线 OCR。规则无法处理时返回 `rule_unhandled`。 |
| `required` | 图片输入要求 OCR；未配置 OCR vendor 时返回 `501 not_implemented`。 |

OCR vendor 由环境变量 `EFAPIAO_OCR_VENDOR` 配置，可选 `none` / `cnocr` / `http` /
`tencent`。腾讯云、第三方 HTTP 与 CnOCR 的详细鉴权和部署参数见 [DESIGN.md](../DESIGN.md)。

## 3. HTTP 接口

### 3.1 健康检查

```http
GET /v1/health
```

响应：

```json
{"status": "ok"}
```

### 3.2 能力查询

```http
GET /v1/capabilities
```

响应字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `version` | string | 服务版本 |
| `formats` | object | `pdf` / `ofd` / `image` 当前状态 |
| `document_types` | string[] | 可返回的单据大类 |
| `invoice_types` | string[] | 可返回的票据细分类型 |
| `parse_modes.ocr_mode` | object | `ocr_mode` 可选值说明 |

### 3.3 解析文件

```http
POST /v1/invoices/parse
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `file` | binary | 是 | 无 | PDF / OFD / 图片文件 |
| `hint_type` | string | 否 | `auto` | `pdf` / `ofd` / `image` / `auto` |
| `ocr_mode` | string | 否 | `auto` | `auto` / `disabled` / `required` |

成功响应：

```json
{
  "request_id": "uuid",
  "status": "ok",
  "format": "pdf",
  "document_type": "pdf-fapiao",
  "invoice_type": "digital_general",
  "data": {
    "document_type": "pdf-fapiao",
    "invoice_type": "digital_general",
    "invoice_number": "26317000001791661472",
    "invoice_code": null,
    "issue_date": "2026-05-17",
    "seller": {"name": "...", "tax_id": "...", "address": null, "bank": null},
    "buyer": {"name": "...", "tax_id": "...", "address": null, "bank": null},
    "items": [],
    "amount_without_tax": "199.06",
    "tax_amount": "11.94",
    "amount_with_tax": "211.00",
    "amount_in_words": "贰佰壹拾壹圆整",
    "remark": null,
    "checksum": null,
    "extra": {"rail_12306": null, "air_itinerary": null},
    "source": {
      "format": "pdf",
      "parser_version": "0.1.0",
      "extracted_by": "text_layer",
      "ocr_vendor": null
    }
  },
  "engine": {
    "rule_engine": "attempted",
    "ocr_mode": "auto",
    "ocr_enabled": false,
    "ocr_used": false,
    "ocr_required": false,
    "ocr_vendor": null
  },
  "elapsed_ms": 21
}
```

### 3.4 批量解析文件

```http
POST /v1/invoices/parse-batch
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `files` | binary[] | 是 | 无 | 多个 PDF / OFD / 图片文件，字段名重复传入 |
| `hint_type` | string | 否 | `auto` | 整批共享：`pdf` / `ofd` / `image` / `auto` |
| `ocr_mode` | string | 否 | `auto` | 整批共享：`auto` / `disabled` / `required` |

示例：

```bash
curl -F "files=@invoice-1.pdf" \
     -F "files=@invoice-2.pdf" \
     -F "hint_type=auto" \
     -F "ocr_mode=disabled" \
     http://127.0.0.1:8000/v1/invoices/parse-batch
```

批量接口按文件返回结果。单个文件失败不会让整批请求失败；整体 HTTP 状态仍为
`200`，调用方根据 `items[].status` / `items[].code` 分流。

```json
{
  "request_id": "uuid",
  "status": "ok",
  "total": 2,
  "succeeded": 1,
  "failed": 1,
  "items": [
    {
      "index": 0,
      "filename": "invoice-1.pdf",
      "status": "ok",
      "format": "pdf",
      "document_type": "pdf-fapiao",
      "invoice_type": "digital_general",
      "data": { "invoice_number": "26100000000000000001" },
      "code": null,
      "message": null,
      "engine": {
        "rule_engine": "attempted",
        "ocr_mode": "disabled",
        "ocr_enabled": false,
        "ocr_used": false,
        "ocr_required": false,
        "ocr_vendor": null
      },
      "elapsed_ms": 18
    },
    {
      "index": 1,
      "filename": "unknown.bin",
      "status": "error",
      "format": null,
      "document_type": null,
      "invoice_type": null,
      "data": null,
      "code": "unsupported_format",
      "message": "无法识别的文件格式",
      "engine": {
        "rule_engine": "attempted",
        "ocr_mode": "disabled",
        "ocr_enabled": false,
        "ocr_used": false,
        "ocr_required": false,
        "ocr_vendor": null
      },
      "elapsed_ms": 1
    }
  ],
  "elapsed_ms": 19
}
```

批量接口当前在服务进程内串行处理每个文件。它的主要收益是减少上游多次 HTTP
握手和请求管理成本；如需提高吞吐，建议上游以有限并发调用批量接口，或后续引入服务端
worker 队列。

### 3.5 错误响应

FastAPI 返回时错误体位于 `detail`：

```json
{
  "detail": {
    "request_id": "uuid",
    "status": "error",
    "code": "rule_unhandled",
    "message": "规则引擎无法解析该 PDF：文本层内容过少且未找到二维码；当前未配置 OCR vendor",
    "document_type": null,
    "invoice_type": null,
    "engine": {
      "rule_engine": "attempted",
      "ocr_mode": "disabled",
      "ocr_enabled": false,
      "ocr_used": false,
      "ocr_required": true,
      "ocr_vendor": null
    }
  }
}
```

错误码：

| HTTP | `code` | 说明 | 建议处理 |
|---|---|---|---|
| 400 | `invalid_input` | 文件为空、参数缺失或参数非法 | 修正请求 |
| 415 | `unsupported_format` | 不是 PDF/OFD/图片 | 不进入发票解析队列 |
| 422 | `rule_unhandled` | 规则引擎已尝试但无法处理 | 若 `ocr_required=true`，进入 OCR 或人工队列 |
| 422 | `parse_failed` | 格式支持，但字段抽取失败 | 人工核对或提交样本校准 |
| 501 | `not_implemented` | 当前类型未实现或 OCR 未启用 | 根据 `document_type` / `engine` 分流 |
| 500 | `internal_error` | 服务内部错误 | 保留 `request_id` 排查 |

## 4. Python SDK

```python
from app.sdk import parse_invoice

with open("invoice.pdf", "rb") as f:
    result = parse_invoice(f.read(), hint_type="auto", ocr_mode="disabled")
```

异常映射：

| 异常 | 含义 |
|---|---|
| `InvalidInput` | 入参为空或非法 |
| `UnsupportedFormat` | 文件格式不支持 |
| `RuleEngineUnhandled` | 规则引擎无法处理，可读取 `ocr_required` |
| `ParseFailed` | 字段解析失败 |
| `UnsupportedDocumentType` | 已识别单据类型但当前不解析 |
| `NotImplementedError` | 能力未启用或未实现 |

## 5. CLI

```bash
efapiao parse invoice.pdf --hint auto --ocr-mode disabled --pretty
cat invoice.pdf | efapiao parse - --ocr-mode auto
efapiao capabilities
efapiao serve --host 127.0.0.1 --port 8000
```

退出码：

| 退出码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 未捕获错误 |
| 2 | `invalid_input` |
| 3 | `unsupported_format` |
| 4 | `rule_unhandled` 或 `parse_failed` |
| 5 | `not_implemented` |

CLI 成功 JSON 写到 stdout；错误 JSON 写到 stderr，结构同样包含 `engine`。

## 6. 鉴权

本机集成默认不启用 API Key。设置环境变量后，`/v1/invoices/*` 需要携带
`X-API-Key`：

```bash
export EFAPIAO_API_KEY=your-key
curl -H "X-API-Key: your-key" -F "file=@invoice.pdf" \
  http://127.0.0.1:8000/v1/invoices/parse
```

未设置 `EFAPIAO_API_KEY` 时不校验该 header。

## 7. Release 二进制

发布二进制遵循 SemVer tag 规则：

- 稳定版：`vMAJOR.MINOR.PATCH`，例如 `v0.1.0`
- 预发布：`vMAJOR.MINOR.PATCH-rc.N`，例如 `v0.2.0-rc.1`

GitHub Release 资产命名：

| 平台 | 资产名 |
|---|---|
| Linux x86_64 | `efapiao-<version>-linux-x86_64.tar.gz` |
| Linux arm64 | `efapiao-<version>-linux-arm64.tar.gz` |
| macOS arm64 | `efapiao-<version>-darwin-arm64.tar.gz` |
| Windows x86_64 | `efapiao-<version>-windows-x86_64.zip` |

`darwin-x86_64` 可在 Intel Mac 本地用 `scripts/build_binary.py` 构建；默认 GitHub
Release 资产优先发布当前更常用且 runner 可用性更稳定的平台组合。

二进制提供与 CLI 相同的命令：

```bash
efapiao --version
efapiao capabilities
efapiao parse invoice.pdf --pretty
efapiao serve --host 127.0.0.1 --port 8000
```
