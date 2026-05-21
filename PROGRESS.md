# 开发进度（PROGRESS）

> 维护规则：每次会话结束前，**必须**更新本文件。Agent 与人都按此执行。
> 日期一律 `YYYY-MM-DD`，状态用：✅ 已完成 / 🟡 进行中 / ⬜ 待办 / 🔴 阻塞。

---

## 当前里程碑

**M2 —— 数电专票 + 12306 + 多地版式适配**（2026-05-21，🟡 进行中）

上一里程碑：**M1 —— PdfParser + 数电普票 extractor + 端到端打通**（✅ 已完成）

实测指标（单张 PDF，本机 Python 3.11）：
- `/v1/invoices/parse` 端到端 **21ms**（目标 P95 < 500ms ✅）
- 65 个测试通过，0 skip；测试输入已全部改为脱敏合成数据，不依赖 `docs/sample` 真实发票

---

## 总体里程碑

| 阶段 | 内容 | 状态 | 备注 |
|---|---|---|---|
| M0 | 项目骨架 + 三形态入口（库/CLI/HTTP） | ✅ 已完成 | 2026-05-20 |
| M1 | sdk.parse_invoice 串通 + 数电普票 extractor + 脱敏回归 | ✅ 已完成 | 2026-05-20 |
| M2 | 数电专票 + 12306 + 多地版式适配 | 🟡 进行中 | 40 份本地真样本 + 腾讯 OCR 对照通过 |
| M3 | 透传 (Forwarder) + 鉴权（可选启用）+ Docker | ⬜ 待办 | 计划 0.5 周 |
| M4 | 更多 OFD 发票类型 | ⬜ 待办 | 当前仅识别 OFD 发票，不解析字段；航空行程单 OFD 已支持 |
| M5 | 图片 OCR Parser 实装 | 🟡 接口预研 | OCR vendor 层已就绪，默认关闭 |

---

## 部署形态（DESIGN.md §12）

本服务面向**本机集成**场景，提供三种等价入口：

| 形态 | 入口 | 状态 |
|---|---|---|
| Python 库 | `from app.sdk import parse_invoice` | ✅ pipeline 全串通（PDF 普票） |
| CLI | `efapiao parse <file>` / `efapiao serve` / `efapiao capabilities` | ✅ 脱敏回归通过，退出码合约就位 |
| HTTP 服务 | `uvicorn app.main:app` 或 `efapiao serve` | ✅ `/v1/health` `/v1/capabilities` `/v1/invoices/parse` 全可用 |

---

## 模块就绪度

| 模块 | 文件 | 状态 | 备注 |
|---|---|---|---|
| FastAPI 入口 | `app/main.py` | ✅ 已完成 | `create_app()` + `/v1` 路由挂载 |
| 路由 | `app/api/routes.py` | ✅ 已完成 | `health` / `capabilities` / `invoices/parse`；错误体返回 `engine` 便于上游分流 |
| Pydantic schemas | `app/api/schemas.py` | ✅ 已完成 | §6 全字段：Party/Item/InvoiceData/ParseResponse/ErrorResponse/EngineStatus 等 |
| **SDK 门面** | `app/sdk.py` | ✅ 已完成 | `parse_invoice()` 串通 detector → parser → adapter → extractor → normalizer；支持 `ocr_mode` |
| **CLI** | `app/cli.py` | ✅ 已完成 | 脱敏回归；异常→退出码（0/2/3/4/5）合约就位；支持 `--ocr-mode` |
| 自定义异常 | `app/errors.py` | ✅ 已完成 | InvalidInput / UnsupportedFormat / ParseFailed / RuleEngineUnhandled |
| FormatDetector | `app/core/detector.py` | ✅ 已完成 | PDF / OFD(ZIP+OFD.xml) / JPEG / PNG / GIF magic bytes |
| Normalizer | `app/core/normalizer.py` | ✅ 已完成 | 金额 Decimal→字符串两位、日期校验、§6 字段补 null |
| Forwarder | `app/core/forwarder.py` | ⬜ 接口已定 | M3 实装 |
| Parser 基类 | `app/parsers/base.py` | ✅ 已完成 | ABC + `parse(bytes) -> dict` |
| PdfParser | `app/parsers/pdf_parser.py` | 🟡 M2 增强 | 文本层抽取；文本过短时尝试 QR 最小兜底 |
| OfdParser | `app/parsers/ofd_parser.py` | 🟡 部分支持 | 支持航空运输电子客票行程单 OFD 解析；OFD 发票仅按内容识别并返回 501，不解析字段 |
| ImageParser | `app/parsers/image_parser.py` | 🟡 vendor 接口已接 | 默认关闭返回 501；配置 OCR vendor 后走 OCR 文本层 |
| VersionAdapter | `app/extractors/version_adapter.py` | 🟡 进行中 | 关键字分发（半/全角括号、康熙部首兼容）；QR fallback 已接 |
| Extractor: 数电普票 | `app/extractors/digital_general.py` | ✅ M2 增强 | manifest 普票 22/22 关键字段全过 |
| Extractor: 数电专票 | `app/extractors/digital_special.py` | ✅ 文本层完成 | manifest 专票 6/6 关键字段全过 |
| Extractor: 12306 | `app/extractors/rail_12306.py` | ✅ 文本层完成 | manifest 铁路 12/12 关键字段全过 |
| Extractor: 航空行程单 | `app/extractors/air_itinerary.py` | ✅ OFD 完成 | Itinerary OFD 样本 4/4 关键字段全过 |
| Extractor: fallback | `app/extractors/fallback.py` | 🟡 最小可用 | 二维码兜底提取发票号 / 日期 / 金额 / 校验码 |
| OCR vendor | `app/ocr/` | 🟡 接口已定 | 支持 CnOCR / 第三方 HTTP API / 腾讯云；CnOCR 为可选依赖 |
| 配置 | `app/config.py` | ✅ 已完成 | 鉴权可选 / host / port 等环境变量 |
| 测试 | `tests/` | ✅ 65 通过 / 0 skip | 单元 + 脱敏合成 PDF/OFD 集成 + HTTP/CLI 端到端 + OCR vendor + QR fallback + URL 安全 |
| Docker | `Dockerfile` / `.dockerignore` | ✅ 已完成 | 含 libzbar0 系统依赖 |
| Release 二进制 | `.github/workflows/release.yml` / `scripts/build_binary.py` | ✅ 已接入 | PyInstaller 本地构建 + GitHub Actions 多平台 Release |
| 文档 | `DESIGN.md` / `README.md` / `AGENT_GUIDE.md` | ✅ 已完成 | DESIGN.md §12 已加部署形态 |
| 开发样本 | `docs/sample/*.pdf` (本地) | ✅ 已整理 | 普票 ×22 / 专票 ×6 / 12306 ×12；含腾讯 OCR raw/compare report。**已 .gitignore，禁止入库** |
| 行程单样本 | `docs/sample/Itinerary/*.ofd` (本地) | ✅ 已就绪 | 航空运输电子客票行程单 ×4。**已 .gitignore，禁止入库** |
| OFD 发票样本 | `docs/sample/ofd-fapiao/*.ofd` (本地) | ✅ 已用于识别验证 | 文本层样本按内部文本识别；轮廓/图片型样本配置 OCR vendor 后可按内嵌图片识别；识别后统一返回 501，不解析字段。**已 .gitignore，禁止入库** |

---

## 决策与确认（来自用户）

| 决策点 | 结论 | 日期 |
|---|---|---|
| 样本位置 | `docs/sample/` 真发票，**已 .gitignore**；脱敏样本走 `tests/fixtures/` 入库 | 2026-05-20 |
| 鉴权策略 | 可选：`EFAPIAO_API_KEY` 留空 = 关闭；填值 = 强制 `X-API-Key` 校验 | 2026-05-20 |
| 部署目标 | **本机集成**，三种等价形态：库 / CLI / HTTP（DESIGN.md §12） | 2026-05-20 |
| 监听默认值 | `127.0.0.1:8000`；对外开放需显式 `EFAPIAO_HOST=0.0.0.0` | 2026-05-20 |
| OFD 支持范围 | OFD 只解析航空运输电子客票行程单；OFD 发票仅做内容识别，字段解析不在当前支持范围内 | 2026-05-21 |

---

## 已完成（按日期倒序）

### 2026-05-21（M2 继续）
- 新增多平台二进制发布能力：本地 `scripts/build_binary.py` 可构建当前平台单文件二进制；GitHub Actions 在 SemVer tag 上构建 linux-x86_64 / linux-arm64 / darwin-arm64 / windows-x86_64 并发布到 GitHub Release；darwin-x86_64 可在 Intel Mac 本地构建
- Release 产物命名统一为 `efapiao-<version>-<os>-<arch>.tar.gz` 或 Windows `.zip`，并生成 `SHA256SUMS`
- 测试套件全面改为脱敏合成数据源：移除 `tests/` 对 `docs/sample` 真实发票/OFD 的读取依赖，新增 `tests/fixtures/sanitized.py` 统一生成脱敏文本和最小 OFD 容器
- 新增 CLI 回归测试、HTTP 鉴权/文件大小契约测试、OFD magic bytes 检测测试，以及测试套件策略测试，防止未来重新依赖 `docs/sample`
- 脱敏集成覆盖数电普票、免税普票、跨行合计专票、bare-token 专票、12306 客票、OFD 航空行程单、OFD 发票识别不解析等关键分支
- 新增纯规则模式 API 契约：`ocr_mode=disabled` 时不调用本地/在线 OCR，规则引擎无法处理时返回 `rule_unhandled` 与机器可读 `engine.ocr_required`
- HTTP/CLI 成功与错误响应补充 `engine`：包含 `rule_engine`、`ocr_mode`、`ocr_enabled`、`ocr_used`、`ocr_required`、`ocr_vendor`
- `/v1/capabilities` 补充 `parse_modes.ocr_mode`，文档说明无 OCR 部署、OCR 队列与人工队列的分流方式
- 新增 `docs/API.md`，完整描述 HTTP / Python SDK / CLI 契约、错误码、`ocr_mode` 与无 OCR 场景处理方式
- 对 `docs/sample/mixed-sample/` 728 个混合样本执行批量解析与腾讯 OCR 对照；本地报告保存到 `docs/sample/mixed-sample-results/`（已被 `docs/sample/*` 忽略，不入库）
- 校准旧版增值税电子普通发票、浙江通用（电子）发票、区块链/机打类发票文本层解析：支持 8 位发票号、12 位发票代码、分散日期、旧版金额行、通用电子发票行项目
- 修复铁路电子客票被 `pdf-fapiao` 兜底误分流的问题，优先识别 `pdf-rail-12306`
- 腾讯 OCR 结构化响应保留 `key: value` 文本，图片航空行程单可解析为 `document_type=image-air-itinerary`
- 统一新增 `document_type` 字段，用于返回单据大类：`pdf-fapiao` / `ofd-fapiao` / `pdf-rail-12306` / `ofd-air-itinerary` / `image-air-itinerary` / `image-fapiao`；`invoice_type` 保留为细分类型，例如 PDF 发票下的 `digital_general` / `digital_special`
- HTTP 成功响应外层同步返回 `document_type`；已识别但不支持解析的 OFD 发票 501 错误体返回 `document_type=ofd-fapiao`
- 根据用户确认收敛 OFD 支持范围：OFD 只解析航空运输电子客票行程单；OFD 发票仅按内部字段/文本识别，轮廓/图片型 OFD 可在配置 OCR vendor 后按内嵌图片识别，字段解析返回 `501 not_implemented`
- 移除 `extra.ofd_invoice` schema 与 OFD 发票 extractor 功能路径，避免上游误认为 OFD 发票字段已受支持
- 更新 `tests/test_ofd_invoice.py`：覆盖 `docs/sample/ofd-fapiao` 中 OFD 发票样本，确认按内容识别后统一返回不支持
- 实装 OFD 航空运输电子客票行程单解析：读取 OFD ZIP 内 XML/XBRL `atr:*` 字段，按内容识别 `air_itinerary`，不依赖文件名
- 统一 schema 新增 `invoice_type=air_itinerary` 与 `extra.air_itinerary` 字段，保留航班号、航段、旅客、证件掩码、电子客票号、票价/燃油/民航基金等字段
- `/v1/capabilities` 中 OFD 状态改为 `partial_supported`，表示当前仅支持航空行程单 OFD
- 新增 `tests/test_ofd_air_itinerary.py`，覆盖 4 份本地 OFD 行程单样本；内容识别路径验证通过
- 将 `docs/sample/` 中 40 份 PDF 按类型与票号重命名为 `general_###_票号.pdf` / `special_###_票号.pdf` / `rail_###_票号.pdf`
- 生成本地 `docs/sample/manifest.json`，记录原始文件名、规范文件名、票种与票号；目录继续由 `.gitignore` 排除
- 使用腾讯云 `RecognizeGeneralInvoice` 对 40 份样本首页逐一识别，40/40 成功；raw JSON 保存到 `docs/sample/tencent_ocr_raw/`
- 生成 `docs/sample/tencent_ocr_raw/summary.json` 与 `compare_report.json`，本地 parser 与腾讯结构化字段在票种、票号、日期、金额、购销方关键字段上 40/40 对齐
- 增强 `app/extractors/_shared.py`：普票/专票共享 bare-token 兜底，支持水印/红章版式中票号、日期、购销方跨列或标签缺失的情况
- 增强行项目解析：支持 `不征税` / `免税` / `零税率` 行尾，不再要求税率一定是百分号
- 修复购销方名称清洗：去掉列标题残留（如 `销`），长度过短的标签残片会触发 bare-name fallback
- `tests/test_integration_samples.py` 改为 manifest 驱动；新增样本后自动验证三类算法核心字段
- 验证：`pytest -q` 为 91 passed / 1 skipped；相关 extractor 与集成测试 targeted ruff 通过

### 2026-05-20（M2 进行中）
- 抽出 `app/extractors/_shared.py`，复用普票 / 专票字段抽取逻辑
- `digital_special`：支持数电专票文本层解析，覆盖标准版、跨行合计版、红章版三类样本
- `rail_12306`：支持 12306 电子客票文本层解析，提取票号、开票日期、购方、票价、车次、起止站、发车时间、座席、旅客及证件掩码
- VersionAdapter：兼容康熙部首字符（如 `电⼦发票`）与更宽松的发票类型关键字识别
- 集成测试扩到 27 例：新增专票 3 例、12306 电子客票 2 例；全量通过
- 新增 `app/ocr/` vendor 层：统一 OCR 输出结构，支持 CnOCR 本地 vendor、第三方 HTTP OCR vendor 与腾讯云 OCR vendor；默认 `EFAPIAO_OCR_VENDOR=none`，不影响现有 PDF 路径
- `ImageParser` 接入 OCR vendor 后复用 VersionAdapter / extractor pipeline；未配置 OCR 时保持 501 语义
- `pyproject.toml` 新增 `ocr-cnocr` 可选依赖组，避免默认安装引入大模型依赖
- 腾讯云 OCR vendor 采用 API 3.0 TC3-HMAC-SHA256 签名；密钥支持源码 context、凭据文件、环境变量三种传入方式
- 新增 `app/core/url_security.py`：第三方 HTTP OCR 默认强制 HTTPS，拒绝 localhost / 内网 / 链路本地等地址；仅本地调试可显式允许 HTTP
- OCR vendor 与 URL 安全测试扩充，总测试数扩到 47 例；全量通过
- 新增 `app/core/capabilities.py`，HTTP `/v1/capabilities` 与 CLI `efapiao capabilities` 共用同一份能力描述
- Normalizer 保留 `source.ocr_vendor`，OCR 结果可审计实际 vendor
- `fallback.extract` 实装二维码最小字段解析；`PdfParser` 在文本层过短时尝试 pyzbar QR 兜底，成功时标记 `source.extracted_by=qrcode`
- 测试总数扩到 52 例；全量 pytest 通过，OCR/QR/capabilities 相关文件 targeted ruff 通过

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
- **QR 兜底仅最小可用**：当前只填 invoice_number / issue_date / amount_with_tax / checksum；复杂二维码字段语义、票种细分和真实扫描件矩阵仍需继续实测。
- **12306 暂未拆分价税**：电子客票样本文本只提供票价/退票费，当前填入 `amount_with_tax` 与行项目金额，`amount_without_tax` / `tax_amount` 仍为 null。
- **路径轮廓型 OFD 暂未 OCR**：`docs/sample/ofd-fapiao/电子发票.ofd` 文字被转为 PathObject 轮廓，无 TextCode 文本层；需后续接 OFD 渲染或 OCR vendor。

---

## 下一步建议（M2 收口 checklist）

1. **QR 真实样本回归**：补扫描件 / 无文本层 PDF 样本，验证 pyzbar 渲染分辨率与字段位置。
2. **QR 字段语义细化**：确认不同税务二维码中金额字段是含税、未税还是价税合计，必要时按版本号分支。
3. **items 分列改造**：试用 `pdfplumber.Page.extract_tables()`；若噪声多则退回基于坐标的简单分列。
4. **多地版式**：找两份不同税局出具的普票/专票，验证现有正则在 `名称 / 销 / 售 / 信` 终止符上的鲁棒性。
5. **12306 票价语义**：若下游需要区分票价 / 退票费 / 差额退票，需确认是否放入 `remark` 或 `extra.rail_12306`（会涉及 schema 扩展）。
6. **OCR vendor 实测**：在 amd64 / arm64 纯 CPU 容器内实测 CnOCR 冷启动、单页延迟和模型缓存策略。

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
