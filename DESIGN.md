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
- 当前只做 PDF（数电发票），但接口形状一次设计到位，OFD 和图片 OCR 后续可无缝补齐。

---

## 2. 范围与边界

### 2.1 一期开发（MVP）

| 能力 | 说明 |
|---|---|
| 数电普票 PDF 解析 | 全国统一的数电普通发票 |
| 数电专票 PDF 解析 | 全国统一的数电增值税专用发票 |
| 12306 电子客票 PDF 解析 | 报销凭证（火车票） |
| 多地版式兼容 | 不同税务局版式差异通过解析策略适配 |
| 统一 JSON 输出 | 见第 6 节 schema |
| 透传 / 转发能力 | 解析结果可按配置 POST 到下游应用（webhook 模式） |

### 2.2 接口预留（不开发）

| 能力 | 处理方式 |
|---|---|
| OFD 发票解析 | 路由 + Parser 接口预留，返回 `501 Not Implemented` |
| 图片格式发票 OCR | 路由 + Parser 接口预留，返回 `501 Not Implemented` |

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
  │ (MVP)     │    │ (501)     │      │ (501)     │
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

- **Parser 抽象**：所有解析器实现同一个接口 `Parser.parse(bytes) -> RawInvoice`，OFD/IMG 预留空实现即可。
- **版式适配**：先用关键字 / 二维码 / 文字坐标特征识别版式，再分发到对应 extractor，避免一个 if-else 怪兽。
- **解析策略**：PDF 优先走"文本层抽取"（pdfplumber / pdfminer），失败则降级到二维码解析；二维码包含发票核心字段，是最稳的兜底。

---

## 5. API 设计

### 5.1 同步解析

```
POST /v1/invoices/parse
Content-Type: multipart/form-data | application/json

# 二选一
- file: <binary>                                # multipart 上传
- file_url: "https://..."                       # 或远程 URL
- file_base64: "..."                            # 或 base64

# 可选
- hint_type: "pdf" | "ofd" | "image" | "auto"   # 默认 auto
```

**响应**

```json
{
  "request_id": "uuid",
  "status": "ok",
  "format": "pdf",
  "invoice_type": "digital_general",
  "data": { /* 见 §6 */ },
  "elapsed_ms": 128
}
```

### 5.2 解析并透传

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

### 5.3 元信息

```
GET /v1/health           # 健康检查
GET /v1/capabilities     # 返回当前支持的 format / invoice_type 列表
```

`/v1/capabilities` 用于让调用方知道 OFD/图片目前是 `not_implemented`，避免业务方误用。

### 5.4 错误码

| HTTP | code | 含义 |
|---|---|---|
| 400 | `invalid_input` | 文件为空 / 参数缺失 |
| 415 | `unsupported_format` | 文件不是 PDF/OFD/图片 |
| 422 | `parse_failed` | 能识别格式但抽不出字段 |
| 501 | `not_implemented` | OFD / 图片暂未实现 |
| 500 | `internal_error` | 兜底 |

---

## 6. 统一发票 JSON Schema

设计原则：**所有发票类型共用一套字段**，类型特有字段放 `extra`，避免下游分支爆炸。

```json
{
  "invoice_type": "digital_general | digital_special | rail_12306",
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
    }
  },
  "source": {
    "format": "pdf",
    "parser_version": "0.1.0",
    "extracted_by": "text_layer | qrcode | ocr"
  }
}
```

- 金额一律用字符串表达，避免浮点精度问题。
- 日期一律 `YYYY-MM-DD`。
- 缺字段一律 `null`，不要省略键，方便下游解析。

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
| 二维码 | pyzbar / opencv | 用作兜底 extractor |
| 部署 | 单容器 Docker | 无状态，水平扩展即可 |
| 配置 | 环境变量 | 不引入复杂配置中心 |

---

## 9. 非功能需求

| 维度 | 目标 |
|---|---|
| 单张 PDF 解析延迟 | P95 < 500ms |
| 并发 | 单实例 ≥ 20 QPS |
| 文件大小上限 | 10 MB |
| 日志 | 仅记录 request_id / 类型 / 耗时 / 是否成功，不记录发票内容 |
| 安全 | 全程内存处理，处理完释放，不落盘 |
| 鉴权 | API Key（Header `X-API-Key`），一期支持单一静态 key 即可 |

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
│   │   ├── ofd_parser.py      # 占位，raise NotImplementedError
│   │   └── image_parser.py    # 占位，raise NotImplementedError
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
| M4（后续） | OFD Parser 实装 | 视需求 |
| M5（后续） | 图片 OCR Parser 实装 | 视需求 |

---

## 12. 风险与对策

| 风险 | 对策 |
|---|---|
| 各地版式差异大 | 用二维码做兜底，文本抽不出时降级 |
| 用户上传被加密 / 扫描版 PDF | 明确返回 `parse_failed`，提示走图片 OCR（后续能力） |
| 透传地址不可信 | 不允许内网地址、强制 HTTPS、超时 5s |
| 一期被业务方滥用为存储/审批系统 | 明确文档：本服务只做解析，无状态 |
