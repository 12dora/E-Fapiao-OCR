# 开发进度（PROGRESS）

> 维护规则：每次会话结束前，**必须**更新本文件。Agent 与人都按此执行。
> 日期一律 `YYYY-MM-DD`，状态用：✅ 已完成 / 🟡 进行中 / ⬜ 待办 / 🔴 阻塞。

---

## 当前里程碑

**M0 —— 项目骨架与契约**（2026-05-20 启动）

完成标志：
- 目录结构、Parser 抽象、Pydantic schema 占位、Dockerfile、健康检查可起服。
- AGENT_GUIDE.md / PROGRESS.md / DESIGN.md 三件套就绪。

下一个里程碑：**M1 —— PDF Parser + 数电普票 extractor**

---

## 总体里程碑

| 阶段 | 内容 | 状态 | 备注 |
|---|---|---|---|
| M0 | 项目骨架（目录 / 抽象 / Docker / git） | 🟡 进行中 | 本次会话产出 |
| M1 | API 框架 + PdfParser + 数电普票 extractor | ⬜ 待办 | 计划 1 周 |
| M2 | 数电专票 + 12306 + 多地版式适配 | ⬜ 待办 | 计划 1 周 |
| M3 | 透传 (Forwarder) + API Key 鉴权 + Docker 发布 | ⬜ 待办 | 计划 0.5 周 |
| M4 | OFD Parser 实装 | ⬜ 待办 | 视需求 |
| M5 | 图片 OCR Parser 实装 | ⬜ 待办 | 视需求 |

---

## 模块就绪度

| 模块 | 文件 | 状态 | 备注 |
|---|---|---|---|
| FastAPI 入口 | `app/main.py` | ✅ 已完成 | `create_app()` + `/v1` 路由挂载 |
| 健康检查 | `app/api/routes.py` | ✅ 已完成 | `GET /v1/health` |
| Pydantic schemas | `app/api/schemas.py` | 🟡 骨架 | 仅 `HealthResponse`；§6 模型待实现 |
| FormatDetector | `app/core/detector.py` | ⬜ 接口已定 | 待实现 magic bytes 识别 |
| Normalizer | `app/core/normalizer.py` | ⬜ 接口已定 | 待实现金额/日期归一化 |
| Forwarder | `app/core/forwarder.py` | ⬜ 接口已定 | M3 实装 |
| Parser 基类 | `app/parsers/base.py` | ✅ 已完成 | ABC + `parse(bytes) -> dict` |
| PdfParser | `app/parsers/pdf_parser.py` | ⬜ 占位 | M1 主战场 |
| OfdParser | `app/parsers/ofd_parser.py` | ✅ 占位（按设计） | 返回 501 |
| ImageParser | `app/parsers/image_parser.py` | ✅ 占位（按设计） | 返回 501 |
| VersionAdapter | `app/extractors/version_adapter.py` | ⬜ 接口已定 | 关键字+二维码分发 |
| Extractor: 数电普票 | `app/extractors/digital_general.py` | ⬜ 接口已定 | M1 |
| Extractor: 数电专票 | `app/extractors/digital_special.py` | ⬜ 接口已定 | M2 |
| Extractor: 12306 | `app/extractors/rail_12306.py` | ⬜ 接口已定 | M2 |
| Extractor: fallback | `app/extractors/fallback.py` | ⬜ 接口已定 | 二维码兜底 |
| 配置 | `app/config.py` | ✅ 已完成 | 环境变量读取 |
| 测试 | `tests/test_health.py` | ✅ 1 例 | 健康检查冒烟 |
| Docker | `Dockerfile` / `.dockerignore` | ✅ 已完成 | 含 libzbar0 系统依赖 |
| 文档 | `DESIGN.md` / `README.md` / `AGENT_GUIDE.md` | ✅ 已完成 | — |

---

## 已完成（按日期倒序）

### 2026-05-20
- 建立项目目录骨架（`app/{api,core,parsers,extractors}` + `tests/fixtures`）
- 写入 `pyproject.toml`（FastAPI / pdfplumber / pyzbar / httpx + dev 套件）
- 创建 Parser 抽象与 OFD/Image 占位 Parser
- 创建所有核心模块的接口签名（detector / normalizer / forwarder / version_adapter / 各 extractor）
- 实装 `/v1/health` + 测试
- 编写 `Dockerfile`（含 zbar 系统依赖）、`.dockerignore`、`.env.example`、`.gitignore`
- 编写 `AGENT_GUIDE.md`（开发期通用 Agent 提示词）
- 编写 `PROGRESS.md`（本文件）
- `git init` + 初始 commit

---

## 当前阻塞 / 决策点

- ⬜ **样本发票来源**：M1 开工前，需要 1-3 张脱敏的数电普票 PDF 放进 `tests/fixtures/`，否则没法做开发期回归。**待用户提供**。
- ⬜ **API Key 分发策略**：一期是静态 key，运维侧怎么轮换、是否走 K8s Secret —— 待与运维确认。
- ⬜ **部署目标平台**：K8s / 单机 Docker / 云函数？影响 health probe 配置与日志投递路径。**待确认**。

---

## 下一步建议（给下一个 Agent / 开发者）

1. **拿到样本**后，先填 `app/api/schemas.py` 中 `InvoiceData / Seller / Buyer / Item / ParseResponse` 等模型，与 DESIGN.md §6 完全对齐。
2. 实装 `app/core/detector.py`，覆盖 PDF / OFD（ZIP magic）/ JPEG / PNG 四种。
3. 实装 `app/parsers/pdf_parser.py` 的「文本层 → 版式识别 → 数电普票 extractor」最短路径，先跑通一张样本。
4. 补 `POST /v1/invoices/parse` 路由，串起：上传 → detector → PdfParser → VersionAdapter → extractor → normalizer → 响应。
5. 写一个用真实样本的集成测试。
6. 再加 §5.4 错误码的统一异常处理。

---

## 变更日志（重大决策）

| 日期 | 决策 | 原因 |
|---|---|---|
| 2026-05-20 | 选用 FastAPI + pdfplumber + pyzbar | DESIGN.md §8 已锁定 |
| 2026-05-20 | 一期不引入 Redis / MQ / DB | DESIGN.md §2.3 红线 |
| 2026-05-20 | 透传强制 HTTPS、禁内网地址 | 防 SSRF（DESIGN.md §12） |
