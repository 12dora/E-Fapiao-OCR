# 开发进度（PROGRESS）

> 维护规则：每次会话结束前，**必须**更新本文件。Agent 与人都按此执行。
> 日期一律 `YYYY-MM-DD`，状态用：✅ 已完成 / 🟡 进行中 / ⬜ 待办 / 🔴 阻塞。

---

## 当前里程碑

**M1 —— PdfParser + 数电普票 extractor + 端到端打通**（2026-05-20，✅ 已完成）

下一个里程碑：**M2 —— 数电专票 + 12306 + 多地版式适配**

实测指标（单张 PDF，本机 Python 3.11）：
- `/v1/invoices/parse` 端到端 **21ms**（目标 P95 < 500ms ✅）
- 22 个测试全通过（含 2 个真样本集成 + 3 个 HTTP 端到端）

---

## 总体里程碑

| 阶段 | 内容 | 状态 | 备注 |
|---|---|---|---|
| M0 | 项目骨架 + 三形态入口（库/CLI/HTTP） | ✅ 已完成 | 2026-05-20 |
| M1 | sdk.parse_invoice 串通 + 数电普票 extractor + 真样本回归 | ✅ 已完成 | 2026-05-20 |
| M2 | 数电专票 + 12306 + 多地版式适配 | ⬜ 待办 | 计划 1 周 |
| M3 | 透传 (Forwarder) + 鉴权（可选启用）+ Docker | ⬜ 待办 | 计划 0.5 周 |
| M4 | OFD Parser 实装 | ⬜ 待办 | 视需求 |
| M5 | 图片 OCR Parser 实装 | ⬜ 待办 | 视需求 |

---

## 部署形态（DESIGN.md §12）

本服务面向**本机集成**场景，提供三种等价入口：

| 形态 | 入口 | 状态 |
|---|---|---|
| Python 库 | `from app.sdk import parse_invoice` | ✅ pipeline 全串通（PDF 普票） |
| CLI | `efapiao parse <file>` / `efapiao serve` / `efapiao capabilities` | ✅ 真样本验证通过，退出码合约就位 |
| HTTP 服务 | `uvicorn app.main:app` 或 `efapiao serve` | ✅ `/v1/health` `/v1/capabilities` `/v1/invoices/parse` 全可用 |

---

## 模块就绪度

| 模块 | 文件 | 状态 | 备注 |
|---|---|---|---|
| FastAPI 入口 | `app/main.py` | ✅ 已完成 | `create_app()` + `/v1` 路由挂载 |
| 路由 | `app/api/routes.py` | ✅ 已完成 | `health` / `capabilities` / `invoices/parse`；§5.4 五种状态码映射就绪 |
| Pydantic schemas | `app/api/schemas.py` | ✅ 已完成 | §6 全字段：Party/Item/InvoiceData/ParseResponse/ErrorResponse 等 |
| **SDK 门面** | `app/sdk.py` | ✅ 已完成 | `parse_invoice()` 串通 detector → parser → adapter → extractor → normalizer |
| **CLI** | `app/cli.py` | ✅ 已完成 | 真样本验证；异常→退出码（0/2/3/4/5）合约就位 |
| 自定义异常 | `app/errors.py` | ✅ 已完成 | InvalidInput / UnsupportedFormat / ParseFailed |
| FormatDetector | `app/core/detector.py` | ✅ 已完成 | PDF / OFD(ZIP+OFD.xml) / JPEG / PNG / GIF magic bytes |
| Normalizer | `app/core/normalizer.py` | ✅ 已完成 | 金额 Decimal→字符串两位、日期校验、§6 字段补 null |
| Forwarder | `app/core/forwarder.py` | ⬜ 接口已定 | M3 实装 |
| Parser 基类 | `app/parsers/base.py` | ✅ 已完成 | ABC + `parse(bytes) -> dict` |
| PdfParser | `app/parsers/pdf_parser.py` | ✅ M1 完成 | 文本层抽取；QR 兜底待 M2 |
| OfdParser | `app/parsers/ofd_parser.py` | ✅ 占位（按设计） | 抛 NotImplementedError → 501 |
| ImageParser | `app/parsers/image_parser.py` | ✅ 占位（按设计） | 抛 NotImplementedError → 501 |
| VersionAdapter | `app/extractors/version_adapter.py` | ✅ 已完成 | 关键字分发（半/全角括号兼容）；QR 分发待 M2 |
| Extractor: 数电普票 | `app/extractors/digital_general.py` | ✅ M1 完成 | 真样本 2/2 关键字段全过 |
| Extractor: 数电专票 | `app/extractors/digital_special.py` | ⬜ 接口已定 | M2 |
| Extractor: 12306 | `app/extractors/rail_12306.py` | ⬜ 接口已定 | M2 |
| Extractor: fallback | `app/extractors/fallback.py` | ⬜ 接口已定 | 二维码兜底（M2） |
| 配置 | `app/config.py` | ✅ 已完成 | 鉴权可选 / host / port 等环境变量 |
| 测试 | `tests/` | ✅ 22 例 | 单元 + 真样本集成 + HTTP 端到端 |
| Docker | `Dockerfile` / `.dockerignore` | ✅ 已完成 | 含 libzbar0 系统依赖 |
| 文档 | `DESIGN.md` / `README.md` / `AGENT_GUIDE.md` | ✅ 已完成 | DESIGN.md §12 已加部署形态 |
| 开发样本 | `docs/sample/*.pdf` (本地) | ✅ 已就绪 | 普票 ×2 / 专票 ×3 / 12306 ×2。**已 .gitignore，禁止入库** |

---

## 决策与确认（来自用户）

| 决策点 | 结论 | 日期 |
|---|---|---|
| 样本位置 | `docs/sample/` 真发票，**已 .gitignore**；脱敏样本走 `tests/fixtures/` 入库 | 2026-05-20 |
| 鉴权策略 | 可选：`EFAPIAO_API_KEY` 留空 = 关闭；填值 = 强制 `X-API-Key` 校验 | 2026-05-20 |
| 部署目标 | **本机集成**，三种等价形态：库 / CLI / HTTP（DESIGN.md §12） | 2026-05-20 |
| 监听默认值 | `127.0.0.1:8000`；对外开放需显式 `EFAPIAO_HOST=0.0.0.0` | 2026-05-20 |

---

## 已完成（按日期倒序）

### 2026-05-20（M1）
- 实装 §6 完整 Pydantic schema（`app/api/schemas.py`）
- FormatDetector：PDF / OFD（ZIP+OFD.xml 嗅探）/ JPEG / PNG / GIF
- PdfParser：pdfplumber 文本层抽取，多页拼接
- VersionAdapter：关键字分发（半/全角括号都兼容）
- digital_general extractor：发票号 / 日期 / 双方名称及税号 / 行项目 / 金额 / 大小写合计 / 开票人
- Normalizer：金额 Decimal 两位、日期校验、§6 字段补 null 不省略键
- `sdk.parse_invoice` 全链路串通；HTTP `POST /v1/invoices/parse` 上线（含 400/415/422/501/500 映射）
- `/v1/capabilities` 上线
- 测试集扩到 22 例（detector / normalizer / version_adapter / 真样本集成 / HTTP 端到端）
- **真样本验证**：`普票1.pdf` 与 `普票2.pdf` 关键字段全通；端到端 P50 ≈ 21ms
- CLI 真样本验证：`efapiao parse docs/sample/普票1.pdf --pretty` 成功

### 2026-05-20（M0）
- 建立项目目录骨架（`app/{api,core,parsers,extractors}` + `tests/fixtures`）
- `pyproject.toml`：FastAPI / pdfplumber / pyzbar / httpx + dev 套件；注册 `efapiao` CLI 入口
- Parser 抽象 + OFD/Image 占位（抛 NotImplementedError）
- 所有核心模块的接口签名（detector / normalizer / forwarder / version_adapter / 各 extractor）
- `/v1/health` + 冒烟测试
- `Dockerfile`（libzbar0 系统依赖）、`.dockerignore`、`.env.example`、`.gitignore`
- `AGENT_GUIDE.md`（开发期通用 Agent 提示词）+ `PROGRESS.md`
- `git init` + 初始 commit `1103b13`
- **三形态入口落地**（用户决策后补）：
  - `app/sdk.py` —— 唯一业务入口 `parse_invoice()`
  - `app/cli.py` —— `efapiao parse | serve | capabilities` 子命令
  - `app/errors.py` —— 统一异常类型 → HTTP code / CLI exit code
  - `app/config.py` —— 鉴权可选，新增 host/port
  - `DESIGN.md §12` —— 部署形态章节
  - `docs/sample/` —— 已收到 7 份真样本，整目录 .gitignore，附 README 写明禁忌
- 修订 `AGENT_GUIDE.md`：固化"唯一业务入口"契约 + 样本隐私红线

---

## 当前阻塞 / 决策点

- ⬜ 暂无阻塞。

## 已知遗留（不阻塞 M1 收口，记入 M2 backlog）

- **items 名称含尾部数字**：尾部金额正则之前的 prefix 仍包含 `数量`/`单价`，理想是用 pdfplumber 的 `extract_tables()` 分列。M2 处理（专票表格也同款问题）。
- **QR 兜底未启用**：PdfParser 文本层失败时直接抛 ParseFailed，二维码降级路径与 fallback extractor 未串通，留待 M2。
- **专票 ¥ 渲染为 ´**：某些版式 PDF 字体把 `¥` 映射成 `´`，正则已对 `[¥￥´]` 三种字符兼容；M2 数电专票 extractor 复用此约定。

---

## 下一步建议（M2 启动 checklist）

1. **专票 extractor**：复用 digital_general 80% 正则；差异点是表头多 `单位` 字段、`¥` 可能渲染成 `´`、备注区可能含交易流水。
2. **12306 extractor**：版式完全不同；提取 `passenger_name / id_no_masked / train_no / from_station / to_station / depart_time / seat_type / 票价(amount_with_tax)`；票价行 `￥396.00` 在文本中作单独一行出现。
3. **VersionAdapter QR 分发**：当文本层关键字未命中时，用 pyzbar 解二维码 payload 的前缀字段做识别。
4. **PdfParser QR 兜底**：文本层失败时调 pyzbar 抽 QR → fallback extractor。
5. **items 分列改造**：试用 `pdfplumber.Page.extract_tables()`；若噪声多则退回基于坐标的简单分列。
6. **多地版式**：找两份不同税局出具的普票/专票，验证现有正则在 `名称 / 销 / 售 / 信` 终止符上的鲁棒性。
7. **fallback.extract**：基于二维码 payload 字段返回最小可用 RawInvoice（只填 invoice_number / issue_date / amount_with_tax）。

---

## 变更日志（重大决策）

| 日期 | 决策 | 原因 |
|---|---|---|
| 2026-05-20 | 选用 FastAPI + pdfplumber + pyzbar | DESIGN.md §8 已锁定 |
| 2026-05-20 | 一期不引入 Redis / MQ / DB | DESIGN.md §2.3 红线 |
| 2026-05-20 | 透传强制 HTTPS、禁内网地址 | 防 SSRF（DESIGN.md §13） |
| 2026-05-20 | 三形态等价入口（库/CLI/HTTP） | 用户决策：面向本机集成，需多语言宿主支持 |
| 2026-05-20 | API Key 改为可选 | 用户决策：本机集成默认无需鉴权 |
| 2026-05-20 | 默认监听 127.0.0.1 | 本机集成场景的安全默认；对外服务需显式打开 |
| 2026-05-20 | `docs/sample/` 真发票整目录 .gitignore | 隐私底线（DESIGN.md §9） |
| 2026-05-20 | M1 启用 Python 3.11.15 venv 开发（系统 3.14 不锁版本） | 依赖兼容性；pyproject 已限定 `>=3.11`，3.14 无需阻塞 |
