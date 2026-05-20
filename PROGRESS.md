# 开发进度（PROGRESS）

> 维护规则：每次会话结束前，**必须**更新本文件。Agent 与人都按此执行。
> 日期一律 `YYYY-MM-DD`，状态用：✅ 已完成 / 🟡 进行中 / ⬜ 待办 / 🔴 阻塞。

---

## 当前里程碑

**M0 —— 项目骨架与契约**（2026-05-20，✅ 已完成）

下一个里程碑：**M1 —— PdfParser + 数电普票 extractor + 端到端打通**

---

## 总体里程碑

| 阶段 | 内容 | 状态 | 备注 |
|---|---|---|---|
| M0 | 项目骨架 + 三形态入口（库/CLI/HTTP） | ✅ 已完成 | 2026-05-20 |
| M1 | sdk.parse_invoice 串通 + 数电普票 extractor + 一张真样本回归 | ⬜ 待办 | 计划 1 周 |
| M2 | 数电专票 + 12306 + 多地版式适配 | ⬜ 待办 | 计划 1 周 |
| M3 | 透传 (Forwarder) + 鉴权（可选启用）+ Docker | ⬜ 待办 | 计划 0.5 周 |
| M4 | OFD Parser 实装 | ⬜ 待办 | 视需求 |
| M5 | 图片 OCR Parser 实装 | ⬜ 待办 | 视需求 |

---

## 部署形态（DESIGN.md §12）

本服务面向**本机集成**场景，提供三种等价入口：

| 形态 | 入口 | 状态 |
|---|---|---|
| Python 库 | `from app.sdk import parse_invoice` | 🟡 接口已定，pipeline 待串 |
| CLI | `efapiao parse <file>` / `efapiao serve` / `efapiao capabilities` | ✅ 入口与子命令就绪，依赖 sdk 实装 |
| HTTP 服务 | `uvicorn app.main:app` 或 `efapiao serve` | 🟡 `/v1/health` 已通，业务端点待补 |

---

## 模块就绪度

| 模块 | 文件 | 状态 | 备注 |
|---|---|---|---|
| FastAPI 入口 | `app/main.py` | ✅ 已完成 | `create_app()` + `/v1` 路由挂载 |
| 健康检查 | `app/api/routes.py` | ✅ 已完成 | `GET /v1/health` |
| Pydantic schemas | `app/api/schemas.py` | 🟡 骨架 | 仅 `HealthResponse`；§6 模型待实现 |
| **SDK 门面** | `app/sdk.py` | ⬜ 接口已定 | **唯一业务入口**，HTTP/CLI 皆依赖之 |
| **CLI** | `app/cli.py` | ✅ 入口完成 | `parse / serve / capabilities` 子命令；实际行为待 sdk 实装 |
| 自定义异常 | `app/errors.py` | ✅ 已完成 | HTTP/CLI 统一映射 |
| FormatDetector | `app/core/detector.py` | ⬜ 接口已定 | 待实现 magic bytes 识别 |
| Normalizer | `app/core/normalizer.py` | ⬜ 接口已定 | 待实现金额/日期归一化 |
| Forwarder | `app/core/forwarder.py` | ⬜ 接口已定 | M3 实装 |
| Parser 基类 | `app/parsers/base.py` | ✅ 已完成 | ABC + `parse(bytes) -> dict` |
| PdfParser | `app/parsers/pdf_parser.py` | ⬜ 占位 | M1 主战场 |
| OfdParser | `app/parsers/ofd_parser.py` | ✅ 占位（按设计） | 抛 NotImplementedError → 501 |
| ImageParser | `app/parsers/image_parser.py` | ✅ 占位（按设计） | 抛 NotImplementedError → 501 |
| VersionAdapter | `app/extractors/version_adapter.py` | ⬜ 接口已定 | 关键字+二维码分发 |
| Extractor: 数电普票 | `app/extractors/digital_general.py` | ⬜ 接口已定 | M1 |
| Extractor: 数电专票 | `app/extractors/digital_special.py` | ⬜ 接口已定 | M2 |
| Extractor: 12306 | `app/extractors/rail_12306.py` | ⬜ 接口已定 | M2 |
| Extractor: fallback | `app/extractors/fallback.py` | ⬜ 接口已定 | 二维码兜底 |
| 配置 | `app/config.py` | ✅ 已完成 | 鉴权可选 / host / port 等环境变量 |
| 测试 | `tests/test_health.py` | ✅ 1 例 | 健康检查冒烟 |
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

- ⬜ 暂无阻塞。M1 已具备所有前置条件（样本到位、入口契约定义完成）。

---

## 下一步建议（M1 启动 checklist）

1. **本地装环境**：`python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`，确认 `pytest` 跑过健康检查测试、`efapiao --version` 可执行。
2. **填 schemas.py**：按 DESIGN.md §6 写完 `Seller / Buyer / Item / InvoiceData / ParseResponse / ErrorResponse`。
3. **实装 detector.py**：PDF (`%PDF-`) / OFD (ZIP + 内含 OFD.xml) / JPEG / PNG 四种 magic bytes。
4. **实装 PdfParser**：先走文本层 (pdfplumber)，能抽出 raw text + qr_payload（pyzbar）即可。
5. **实装 version_adapter**：用关键字 + 二维码前缀分发到 `digital_general` extractor（M1 只做普票）。
6. **实装 digital_general.extract**：用 `docs/sample/普票1.pdf` 跑通后再适配 `普票2.pdf`。
7. **实装 normalizer**：金额 Decimal → 字符串、日期统一 ISO、补 null。
8. **串通 sdk.parse_invoice**：detector → parser → adapter → extractor → normalizer。
9. **补 POST /v1/invoices/parse 路由**：调 sdk，捕获 `EfapiaoError` 子类映射到 §5.4 HTTP code。
10. **补 CLI 集成测试**：`efapiao parse docs/sample/普票1.pdf` 应成功输出。
11. **写一个真样本的集成测试**（不入库的话用 `pytest.skip` 在样本缺失时跳过）。

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
