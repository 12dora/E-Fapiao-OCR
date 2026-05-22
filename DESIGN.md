# E-Fapiao-OCR 产品设计文档

> 版本: v0.1
> 日期: 2026-05-20
> 类型: API 服务（无 GUI）

---

## 1. 产品定位

一个**轻量级发票解析 API 服务**，专注于从数电发票（电子发票）PDF 中提取结构化数据，并以标准 JSON 形式返回，便于被其他业务系统（报销、ERP、财务、对账等）直接消费或透传。

**核心定位三句话**

- 只做一件事：把发票文件 → 结构化 JSON。
- 不做界面、不做存储、不做业务逻辑。
- 当前支持 PDF 数电发票 / 12306 客票，以及 OFD 航空运输电子客票行程单；OFD 发票仅做内容识别，不解析字段；图片 OCR 通过 vendor 可选启用。

---

## 2. 范围与边界

### 2.1 一期开发（MVP）

| 能力 | 说明 |
|---|---|
| 数电普票 PDF 解析 | 全国统一的数电普通发票 |
| 数电专票 PDF 解析 | 全国统一的数电增值税专用发票 |
| 12306 电子客票 PDF 解析 | 报销凭证（火车票） |
| 航空运输电子客票行程单 OFD 解析 | 电子行程单，按 OFD 内部 XBRL/OFD 内容判断，不依赖文件名 |
| 航空运输电子客票行程单图片解析 | 配置 OCR vendor 后支持图片行程单，返回 `document_type=image-air-itinerary` |
| OFD 发票内容识别 | 按 OFD 内部字段/文本判断为发票；轮廓/图片型 OFD 需配置 OCR vendor 才能识别；字段解析不在一期支持范围内 |
| 多地版式兼容 | 不同税务局版式差异通过解析策略适配 |
| 统一 JSON 输出 | 见第 6 节 schema |
| 透传 / 转发能力 | 解析结果可按配置 POST 到下游应用（webhook 模式） |

### 2.2 接口预留（不开发）

| 能力 | 处理方式 |
|---|---|
| OFD 发票解析 | 当前仅识别是否为发票，不解析字段；接口返回 `501 Not Implemented` |
| 图片格式发票 OCR | Parser + OCR vendor 接口已预留；默认关闭返回 `501 Not Implemented`，配置 vendor 后启用 |

### 2.3 明确不做

- 不做发票真伪验证（不对接税局验真接口，避免合规与配额问题）
- 不做发票去重 / 入账 / 报销审批
- 不做用户体系、不做前端 UI
- 不持久化发票文件（处理完即丢，仅可选日志中保留摘要）

---

## 3. 用户与场景

**主要使用方**：内部其他后端服务 / 第三方应用的开发者。

**典型场景**

1. 报销系统：员工上传 PDF → 报销系统调用本 API → 拿到金额/抬头/税号 → 入库。
2. 财务对账：批量遍历邮箱附件 PDF → 调用本 API → 与 ERP 订单匹配。
3. SaaS 透传：客户系统 POST 给本 API，本 API 解析后再 POST 到客户指定的回调地址。

---

## 4. 系统架构

```
                ┌─────────────────────────────────────────┐
   PDF/OFD/IMG  │              API Gateway                │
   ──────────►  │   POST /v1/invoices/parse               │
                │   POST /v1/invoices/parse-batch         │
                │   POST /v1/invoices/parse-and-forward   │
                └────────────────┬────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │   FormatDetector             │  根据 magic bytes / 后缀
                  │   (pdf | ofd | image)        │  判断走哪个 Parser
                  └──────┬───────────────────────┘
                         │
        ┌────────────────┼──────────────────┐
        ▼                ▼                  ▼
  ┌───────────┐    ┌───────────┐      ┌───────────┐
  │ PdfParser │    │ OfdParser │      │ ImgParser │
  │ (MVP)     │    │ air itin. │      │ OCR vendor│
  └─────┬─────┘    └───────────┘      └───────────┘
        │
        ▼
  ┌──────────────────────────┐
  │  VersionAdapter          │  按版式选择不同 extractor
  │  - 全国统一数电普票       │
  │  - 全国统一数电专票       │
  │  - 12306 客票            │
  │  - 兜底通用 extractor     │
  └─────┬────────────────────┘
        │
        ▼
  ┌──────────────────────────┐
  │  Normalizer              │  统一字段名 / 金额 / 日期格式
  └─────┬────────────────────┘
        │
        ▼
  ┌──────────────────────────┐
  │  Forwarder (可选)         │  POST 到客户指定 URL
  └──────────────────────────┘
```

### 4.1 关键设计点

- **Parser 抽象**：所有解析器实现同一个接口 `Parser.parse(bytes) -> RawInvoice`；OFD 解析仅支持航空运输电子客票行程单，OFD 发票只做内容识别并返回 501，IMG 由 OCR vendor 可选启用。
- **版式适配**：先用关键字 / 二维码 / 文字坐标特征识别版式，再分发到对应 extractor，避免一个 if-else 怪兽。
- **解析策略**：PDF 优先走"文本层抽取"（pdfplumber / pdfminer），失败则降级到二维码解析；二维码包含发票核心字段，是最稳的兜底。
- **OCR vendor 抽象**：图片 OCR 不绑定单一实现。`ImageParser` 只依赖 `app.ocr` 统一接口，本地 CnOCR 与第三方 HTTP OCR 都作为 vendor 插件接入；默认 vendor 为 `none`，保持 501 语义。
- **OCR 使用边界**：OCR 是图片发票 / 扫描件 PDF 的最后兜底，不替代可复制文本层 PDF 和二维码路径，避免纯 CPU 场景下无谓增大延迟。

---

## 5. API 设计

### 5.1 同步解析

```
POST /v1/invoices/parse
Content-Type: multipart/form-data

- file: <binary>                                # 必填，multipart 上传
- hint_type: "pdf" | "ofd" | "image" | "auto"   # 默认 auto
- ocr_mode: "auto" | "disabled" | "required"    # 默认 auto
```

当前实现只接收 multipart 文件上传；URL 拉取、base64 入参可作为上游自行处理或后续
API 扩展。`ocr_mode=disabled` 是纯规则模式：不会调用本地 CnOCR、第三方 HTTP
OCR 或腾讯云 OCR。规则引擎包括 PDF 文本层、PDF 二维码、OFD XML/XBRL/TextCode
内容解析，适合用户未配置任何 OCR 能力的部署场景。

**响应**

```json
{
  "request_id": "uuid",
  "status": "ok",
  "format": "pdf",
  "document_type": "pdf-fapiao",
  "invoice_type": "digital_general",
  "data": { /* 见 §6 */ },
  "engine": {
    "rule_engine": "attempted",
    "ocr_mode": "auto",
    "ocr_enabled": false,
    "ocr_used": false,
    "ocr_required": false,
    "ocr_vendor": null
  },
  "elapsed_ms": 128
}
```

### 5.2 批量同步解析

```
POST /v1/invoices/parse-batch
Content-Type: multipart/form-data

- files: <binary>[]                             # 必填，重复字段名上传多个文件
- hint_type: "pdf" | "ofd" | "image" | "auto"   # 默认 auto，整批共享
- ocr_mode: "auto" | "disabled" | "required"    # 默认 auto，整批共享
```

批量接口面向邮件附件、报销批量导入等场景。每个文件独立返回 `status=ok/error`、
`data` 或 `code/message`，单个失败不会让整批 HTTP 请求失败。当前实现为服务进程内串行
解析，主要减少上游多次 HTTP 请求成本；高吞吐场景由上游以有限并发调用，或后续引入
服务端 worker 队列。

### 5.3 解析并透传

```
POST /v1/invoices/parse-and-forward
{
  "file_url": "...",
  "forward_to": "https://customer.example.com/webhook",
  "forward_headers": { "X-Auth": "..." },
  "forward_mode": "fire_and_forget" | "wait"
}
```

- `fire_and_forget`：立即返回解析结果，后台异步 POST。
- `wait`：等下游响应，把下游 status/body 一并回传。

### 5.4 元信息

```
GET /v1/health           # 健康检查
GET /v1/capabilities     # 返回当前支持的 format / document_type / invoice_type 列表
```

`/v1/capabilities` 用于让调用方知道 OFD/图片当前状态。OFD 当前返回
`partial_supported`，表示支持航空运输电子客票行程单解析；OFD 发票仅做内容识别，
识别后返回 `501 not_implemented`，不返回发票字段。轮廓/图片型 OFD 没有可复制文本时，
需配置 OCR vendor 后才能按图片内容识别为发票。
图片 OCR 在
`EFAPIAO_OCR_VENDOR=none` 时返回 `not_implemented`，配置 `cnocr` / `http` / `tencent`
vendor 后返回 `supported`。

### 5.5 错误码

| HTTP | code | 含义 |
|---|---|---|
| 400 | `invalid_input` | 文件为空 / 参数缺失 |
| 415 | `unsupported_format` | 文件不是 PDF/OFD/图片 |
| 422 | `rule_unhandled` | 规则引擎已尝试但无法处理；错误体 `engine.ocr_required` 指示是否建议走 OCR |
| 422 | `parse_failed` | 能识别格式但抽不出字段 |
| 501 | `not_implemented` | 当前 OFD 类型未支持 / 图片 OCR 未启用；若已识别出单据类型，会在错误体返回 `document_type` / `invoice_type` |
| 500 | `internal_error` | 兜底 |

错误响应固定结构：

```json
{
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
```

调用方推荐分流：

- `status=ok`：直接消费 `data`。
- `code=rule_unhandled` 且 `engine.ocr_required=true`：文件已保存但规则无法处理，可进入
  OCR 队列；若 `engine.ocr_enabled=false`，提示用户配置 OCR vendor 或人工处理。
- `code=not_implemented` 且 `document_type=ofd-fapiao`：已识别为 OFD 发票，但当前范围只
  做类型识别，不解析字段。
- `code=unsupported_format`：非支持附件，不应进入发票解析队列。

---

## 6. 统一发票 JSON Schema

设计原则：**所有发票类型共用一套字段**，类型特有字段放 `extra`，避免下游分支爆炸。
`document_type` 表示文件/单据大类，`invoice_type` 表示发票或票据细分类型。

```json
{
  "document_type": "pdf-fapiao | ofd-fapiao | pdf-rail-12306 | ofd-air-itinerary | image-air-itinerary | image-fapiao",
  "invoice_type": "digital_general | digital_special | rail_12306 | air_itinerary",
  "invoice_number": "24XXXXXXXXXXXXXXXXXX",
  "invoice_code": null,
  "issue_date": "2026-05-18",
  "seller": {
    "name": "...",
    "tax_id": "...",
    "address": null,
    "bank": null
  },
  "buyer": {
    "name": "...",
    "tax_id": "...",
    "address": null,
    "bank": null
  },
  "items": [
    {
      "name": "...",
      "spec": null,
      "unit": null,
      "quantity": null,
      "unit_price": null,
      "amount": "100.00",
      "tax_rate": "0.06",
      "tax_amount": "6.00"
    }
  ],
  "amount_without_tax": "100.00",
  "tax_amount": "6.00",
  "amount_with_tax": "106.00",
  "amount_in_words": "壹佰零陆元整",
  "remark": null,
  "checksum": null,
  "extra": {
    "rail_12306": {
      "passenger_name": "...",
      "id_no_masked": "...",
      "train_no": "...",
      "from_station": "...",
      "to_station": "...",
      "depart_time": "2026-05-18 09:00",
      "seat_type": "..."
    },
    "air_itinerary": {
      "passenger_name": "...",
      "id_no_masked": "...",
      "e_ticket_number": "...",
      "flight_no": "...",
      "carrier": "...",
      "cabin_class": "...",
      "from_station": "...",
      "to_station": "...",
      "depart_time": "2025-07-04 08:15:00",
      "fare": "550.46",
      "fuel_surcharge": "9.17",
      "civil_aviation_fund": "50.00",
      "other_taxes": "0.00",
      "tax_rate": "0.09"
    }
  },
  "source": {
    "format": "pdf",
    "parser_version": "0.1.0",
    "extracted_by": "text_layer | qrcode | ocr",
    "ocr_vendor": "cnocr | http | tencent | null"
  }
}
```

- 金额一律用字符串表达，避免浮点精度问题。
- 日期一律 `YYYY-MM-DD`。
- 缺字段一律 `null`，不要省略键，方便下游解析。
- PDF 数电发票统一 `document_type=pdf-fapiao`，并用 `invoice_type=digital_general`
  / `digital_special` 区分普票 / 专票。
- OFD 发票识别成功但不解析时，错误响应返回 `document_type=ofd-fapiao`。
- `source.ocr_vendor` 仅在 `extracted_by=ocr` 时填充，用于下游审计和灰度对比。

### 6.1 引擎状态字段

`ParseResponse.engine` 与 `ErrorResponse.engine` 用于告诉上游本次是否只依赖规则、是否需要
OCR：

| 字段 | 类型 | 含义 |
|---|---|---|
| `rule_engine` | `attempted | skipped` | 当前实现中始终先尝试规则引擎，除非未来增加强制直走 OCR |
| `ocr_mode` | `auto | disabled | required` | 本次调用传入的 OCR 策略 |
| `ocr_enabled` | bool | 服务端是否已配置 OCR vendor |
| `ocr_used` | bool | 本次是否实际调用 OCR |
| `ocr_required` | bool | 规则无法覆盖，后续是否需要 OCR 才可能继续 |
| `ocr_vendor` | string/null | 实际使用 vendor，可能为 `cnocr` / `http` / `tencent` |

`ocr_mode` 语义：

| 模式 | 行为 | 适用场景 |
|---|---|---|
| `auto` | 默认；PDF/OFD 先走规则，图片或需 OCR 的路径在 vendor 已配置时走 OCR | 普通在线服务 |
| `disabled` | 纯规则；不调用任何本地/在线 OCR | 用户未配置 OCR、离线部署、成本敏感批处理 |
| `required` | 图片输入要求 OCR；未配置 vendor 时返回 `501 not_implemented` | 上游显式把文件放入 OCR 队列 |

---

## 7. 透传机制（Forwarder）

- 简单的 webhook 转发，不做重试队列（一期不引入消息中间件）。
- 失败仅在响应里告知（`wait` 模式）或日志中告知（`fire_and_forget`）。
- 若客户需要更可靠的转发，由客户在自己侧做队列。**避免一期把本服务做成消息系统。**

---

## 8. 技术选型建议

| 项 | 选择 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | PDF/发票生态最完善（pdfplumber、invoice2data、pyzbar） |
| Web 框架 | FastAPI | 自动 OpenAPI、类型友好、异步原生 |
| PDF 文本层 | pdfplumber | 坐标 + 文本兼顾 |
| OFD 行程单 | ZIP + XML/XBRL 解析 | 直接读 `atr:*` 结构化字段，内容判断票种 |
| OFD 发票识别 | ZIP + XML/TextCode 关键字识别；必要时对内嵌图片走 OCR vendor | 仅判断是否为发票，不解析字段，返回 501 |
| 二维码 | pyzbar / opencv | 用作兜底 extractor |
| OCR vendor | CnOCR(ONNX CPU) / 第三方 HTTP API / 腾讯云 OCR | 图片发票与扫描件兜底；默认关闭，避免默认依赖膨胀 |
| 部署 | 单容器 Docker | 无状态，水平扩展即可 |
| 配置 | 环境变量 | 不引入复杂配置中心 |

### 8.1 OCR vendor 设计

OCR 是独立 vendor 层，不进入 extractor，也不绕过统一 pipeline：

```
ImageParser
  └─ app.ocr.create_ocr_vendor()
       ├─ CnOcrVendor       # 本地 CnOCR，纯 CPU默认 ONNX backend
       ├─ HttpOcrVendor     # 第三方 OCR API
       └─ TencentOcrVendor  # 腾讯云通用票据识别高级版
  └─ OCR text → VersionAdapter → extractor → Normalizer
```

**配置项**

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `EFAPIAO_OCR_VENDOR` | `none` | `none` / `cnocr` / `http` / `tencent` |
| `EFAPIAO_CNOCR_MODEL_PROFILE` | `invoice-lite` | CnOCR 模型 profile，支持 `invoice-lite` / `general-lite` / `scene-lite` / `mobile-lite` |
| `EFAPIAO_CNOCR_DET_MODEL` | `ch_PP-OCRv5_det` | CnOCR 检测模型 |
| `EFAPIAO_CNOCR_REC_MODEL` | `doc-densenet_lite_136-gru` | CnOCR 识别模型 |
| `EFAPIAO_CNOCR_DET_BACKEND` | `onnx` | 纯 CPU / 多架构默认使用 ONNX |
| `EFAPIAO_CNOCR_REC_BACKEND` | `onnx` | 纯 CPU / 多架构默认使用 ONNX |
| `EFAPIAO_OCR_HTTP_URL` | 空 | 第三方 OCR API 地址 |
| `EFAPIAO_OCR_HTTP_HEADERS` | 空 | 第三方 OCR API Header，格式 `A:B;C:D` |
| `EFAPIAO_OCR_HTTP_TIMEOUT` | `10` | 第三方 OCR 超时秒数 |
| `EFAPIAO_OCR_HTTP_ALLOW_HTTP` | `false` | 是否允许第三方 OCR 使用明文 HTTP；仅本地调试开启 |
| `EFAPIAO_TENCENT_SECRET_ID` | 空 | 腾讯云 SecretId；也兼容 `TENCENTCLOUD_SECRET_ID` |
| `EFAPIAO_TENCENT_SECRET_KEY` | 空 | 腾讯云 SecretKey；也兼容 `TENCENTCLOUD_SECRET_KEY` |
| `EFAPIAO_TENCENT_TOKEN` | 空 | 腾讯云临时密钥 Token；也兼容 `TENCENTCLOUD_TOKEN` |
| `EFAPIAO_TENCENT_CREDENTIALS_FILE` | 空 | 腾讯云凭据 JSON 文件路径 |
| `EFAPIAO_TENCENT_REGION` | `ap-guangzhou` | 腾讯云地域 |
| `EFAPIAO_TENCENT_OCR_ENDPOINT` | `ocr.tencentcloudapi.com` | 腾讯云 OCR API 域名 |
| `EFAPIAO_TENCENT_OCR_ACTION` | `RecognizeGeneralInvoice` | 腾讯云通用票据识别高级版 Action |
| `EFAPIAO_TENCENT_OCR_VERSION` | `2018-11-19` | 腾讯云 OCR API 版本 |
| `EFAPIAO_TENCENT_OCR_TIMEOUT` | `10` | 腾讯云 OCR 超时秒数 |

本地 CnOCR 默认组合选用轻量模型：检测 `ch_PP-OCRv5_det`，识别
`doc-densenet_lite_136-gru`，后端均为 `onnx`。这一路径用于图片/扫描件兜底，
OCR 文本仍回到 `VersionAdapter -> extractor -> Normalizer`，不直接输出结构化字段。
运行时通过 `EFAPIAO_CNOCR_MODEL_PROFILE` 支持多模型 selection；显式
`EFAPIAO_CNOCR_DET_MODEL` / `EFAPIAO_CNOCR_REC_MODEL` 会覆盖 profile 默认值。

Release 产物分为两类：

- `lite`：不包含 CnOCR 依赖和模型，适合规则引擎、HTTP OCR 和腾讯云 OCR。
- `with-model`：内置 `invoice-lite` 的 CnOCR ONNX 模型目录。包内模型以相对路径
  `models/cnocr` / `models/cnstd` 随二进制发布，运行时优先从包内读取；同一构建
  逻辑覆盖 Windows / Linux / macOS 与 x86_64 / arm64 架构。

**第三方 HTTP OCR 响应约定**

第三方 HTTP OCR vendor 默认强制 HTTPS，并拒绝 localhost、内网、链路本地、
multicast、reserved、unspecified 地址，避免把 OCR 回调配置变成 SSRF 通道。
`EFAPIAO_OCR_HTTP_ALLOW_HTTP=true` 仅用于本地调试 mock 服务，生产不得开启。

```json
{"text": "整页 OCR 文本"}
```

或：

```json
{
  "lines": [
    {"text": "电子发票(普通发票)", "score": 0.99, "bbox": [[0, 0], [1, 0], [1, 1], [0, 1]]}
  ]
}
```

**腾讯云 OCR 鉴权传入方式**

腾讯云 vendor 使用腾讯云 API 3.0 `TC3-HMAC-SHA256` 签名，请求
`ocr.tencentcloudapi.com` 的 `RecognizeGeneralInvoice`，图片以 `ImageBase64`
传入。为兼顾二进制、源码和多租户集成，密钥来源按以下优先级解析：

1. **源码集成 context override**：宿主 Python 应用用
   `app.ocr.tencent_ocr_credentials()` 为当前调用临时注入 `secret_id` /
   `secret_key` / `token` / `region`。适合宿主应用从 KMS、STS 或租户配置中取密钥。
2. **凭据文件**：设置 `EFAPIAO_TENCENT_CREDENTIALS_FILE=/path/to/tencent.json`。
   适合 Docker secret、Kubernetes Secret volume、二进制或子进程集成。
3. **环境变量**：设置 `EFAPIAO_TENCENT_SECRET_ID` /
   `EFAPIAO_TENCENT_SECRET_KEY` / `EFAPIAO_TENCENT_TOKEN`，或腾讯云标准
   `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_TOKEN`。

凭据文件格式：

```json
{
  "secret_id": "AKID...",
  "secret_key": "...",
  "token": "临时密钥可选",
  "region": "ap-guangzhou"
}
```

集成建议：

- 不支持也不建议通过 CLI 参数传入 `SecretKey`，避免被 shell history、进程列表或日志捕获。
- 二进制 / 子进程集成优先使用环境变量或凭据文件；宿主应用负责密钥生命周期。
- 源码集成优先使用 context override，可为不同请求传入不同租户凭据，而不污染全局进程环境。
- 生产环境优先使用临时密钥 Token；日志和异常不得输出 SecretId、SecretKey、Token。

**CPU / 多架构原则**

- CnOCR 作为可选依赖组 `ocr-cnocr`，默认安装不引入大模型依赖。
- Docker 多架构目标为 `linux/amd64` 与 `linux/arm64`，OCR 默认使用 ONNX CPU backend。
- 模型应在镜像构建或部署初始化阶段预下载到缓存目录，避免首次请求联网下载。
- OCR vendor 不落盘发票文件；如未来 PDF 渲染图片需要临时文件，必须限定 `/tmp` 并 `try/finally` 删除。

---

## 9. 非功能需求

| 维度 | 目标 |
|---|---|
| 单张 PDF 解析延迟 | P95 < 500ms |
| 并发 | 单实例 ≥ 20 QPS |
| 文件大小上限 | 10 MB |
| 日志 | 仅记录 request_id / 类型 / 耗时 / 是否成功，不记录发票内容 |
| 安全 | 全程内存处理，处理完释放，不落盘 |
| 鉴权 | API Key（Header `X-API-Key`），**可选**：未设置环境变量时关闭鉴权（本机集成默认）；设置后强制校验 |

---

## 10. 目录结构（建议）

```
E-Fapiao-OCR/
├── DESIGN.md                  # 本文件
├── app/
│   ├── main.py                # FastAPI 入口
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py         # Pydantic 模型
│   ├── core/
│   │   ├── detector.py        # 格式识别
│   │   ├── normalizer.py      # 字段归一化
│   │   └── forwarder.py       # 透传
│   ├── parsers/
│   │   ├── base.py            # Parser 抽象基类
│   │   ├── pdf_parser.py      # MVP
│   │   ├── ofd_parser.py      # 航空运输电子客票行程单（内容识别）
│   │   └── image_parser.py    # OCR vendor 入口，默认关闭
│   ├── ocr/
│   │   ├── base.py            # OCR 统一结果结构 / Protocol
│   │   ├── factory.py         # 根据配置选择 vendor
│   │   └── vendors/
│   │       ├── cnocr_vendor.py
│   │       └── http_vendor.py
│   └── extractors/
│       ├── digital_general.py
│       ├── digital_special.py
│       ├── rail_12306.py
│       └── fallback.py
├── tests/
│   └── fixtures/              # 样本发票
└── pyproject.toml
```

---

## 11. 里程碑

| 阶段 | 内容 | 预计 |
|---|---|---|
| M1 | API 框架 + PDF Parser + 数电普票 extractor | 1 周 |
| M2 | 数电专票 + 12306 + 多地版式适配 | 1 周 |
| M3 | 透传 + 鉴权 + 文档 + Docker | 0.5 周 |
| M4（后续） | 更多 OFD 发票类型 | 视需求 |
| M5（后续） | 图片 OCR Parser 实装 | 视需求；vendor 接口已预研 |

---

## 12. 部署形态（2026-05-20 补充）

本服务面向**本机集成**场景。提供三种等价形态，共享同一套 pipeline：

```
                ┌──────────────────────────────────────────────┐
                │           核心 pipeline（无状态）              │
                │  detect → parse → version_adapter → normalize │
                └──────────────────────────────────────────────┘
                                ▲           ▲           ▲
                                │           │           │
                       ┌────────┴───┐  ┌────┴────┐  ┌──┴─────────┐
                       │  HTTP 服务   │  │  CLI 进程 │  │ Python 库   │
                       │ app.main:app │  │ app.cli  │  │ app.sdk    │
                       └──────────────┘  └─────────┘  └────────────┘
                            ▲                ▲              ▲
                            │                │              │
                       任意语言通过      任意宿主语言       Python 宿主
                       HTTP localhost    fork CLI 进程     直接 import
```

| 形态 | 适用场景 | 通信方式 | 进入点 |
|---|---|---|---|
| **库 (in-process)** | Python 宿主程序集成，零进程开销 | 函数调用 | `from app.sdk import parse_invoice` |
| **CLI** | 任意语言 / 二进制宿主集成 | 子进程 + stdin/stdout/exit code | `efapiao parse <file>` |
| **HTTP 服务** | 跨进程 / 跨主机 / 多语言客户端 | HTTP/JSON | `uvicorn app.main:app` 或 `efapiao serve` |

**关键设计点**：

- 三种形态共享 `app.sdk.parse_invoice()` 作为唯一业务入口，避免分叉。
- HTTP 层只是 sdk 之上的薄壳：负责协议转换、参数校验、异常→HTTP code 映射。
- CLI 层同样是 sdk 之上的薄壳：负责 stdin/argv 读取、JSON 输出、异常→退出码映射。
- 默认监听 `127.0.0.1`（仅本机），需要对外服务时显式设 `EFAPIAO_HOST=0.0.0.0`。
- 鉴权（API Key）默认关闭，本机集成场景无需配。需要时设 `EFAPIAO_API_KEY=<value>` 即启用。
- 单容器 Docker 仍然支持，但定位是"可选的分发方式"而非"唯一形态"。

**集成示例**：

```python
# 形态一：库
from app.sdk import parse_invoice
with open("invoice.pdf", "rb") as f:
    data = parse_invoice(f.read())
```

```bash
# 形态二：CLI（适合 Go / Rust / Node / shell 宿主）
efapiao parse invoice.pdf | jq .data.invoice_number
cat invoice.pdf | efapiao parse - --pretty
```

```bash
# 形态三：HTTP 服务（适合任意 HTTP 客户端）
efapiao serve --host 127.0.0.1 --port 8000 &
curl -F "file=@invoice.pdf" http://127.0.0.1:8000/v1/invoices/parse
```

---

## 13. 风险与对策

| 风险 | 对策 |
|---|---|
| 各地版式差异大 | 用二维码做兜底，文本抽不出时降级 |
| 用户上传被加密 / 扫描版 PDF | 明确返回 `parse_failed`，提示走图片 OCR（后续能力） |
| 透传地址不可信 | 不允许内网地址、强制 HTTPS、超时 5s |
| 一期被业务方滥用为存储/审批系统 | 明确文档：本服务只做解析，无状态 |
