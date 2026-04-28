# Paperclaw Development Task Table

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Paperclaw 从“可查看的研究控制台 + 脚本流水线”推进为“具备审核、导出治理、可操作 API 与可观测性”的可用运营系统。

**Architecture:** 先补齐内容草稿的领域模型与状态流转，再为前端补写操作型 API，随后把查询、运行控制、导出审计和渠道追踪逐步下沉到后端。整体保持当前 Python + FastAPI + Next.js 分层，不做激进重构，优先沿用现有 `app/api/*`、`app/editorial/*`、`frontend/lib/*` 与 `frontend/app/*` 模式扩展。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, SQLite, Next.js App Router, React, TypeScript

---

## 1. Epic 概览

| Epic | 名称 | 目标 | 优先级 | 依赖 |
|---|---|---|---|---|
| E1 | 草稿审核与状态流转 | 让草稿从文件升级为可审核资产 | P0 | 无 |
| E2 | 导出治理与审计 | 仅允许 approved 草稿导出，并保留审计记录 | P0 | E1 |
| E3 | 可操作 API | 增加审核、导出、通知、流水线触发写接口 | P1 | E1, E2 |
| E4 | 查询接口完善 | 单篇详情、搜索、筛选、分页后端化 | P1 | 无 |
| E5 | 前端运营化 | 增加草稿审核与导出管理界面 | P2 | E1, E2, E3, E4 |
| E6 | 可观测性 | 增加 crawl/summarization/editorial run 遥测 | P3 | E3 |
| E7 | 多渠道闭环 | 增加导出/发布去向记录与渠道结果追踪 | P4 | E2, E6 |
| E8 | 工程化收尾 | 补齐 start、部署说明、缓存清理策略 | P5 | 可并行 |

---

## 2. 正式开发任务表

| ID | 模块 | 任务 | 说明 | 主要文件 | 交付物 | 验收标准 | 优先级 |
|---|---|---|---|---|---|---|---|
| T01 | Editorial Domain | 设计 editorial draft 数据模型 | 为草稿引入持久化模型，而不是仅靠扫描 markdown 文件 | `app/models.py`, `app/storage.py` | `EditorialDraft` 表/模型 | 数据库可保存草稿状态、责任人、审核信息 | P0 |
| T02 | Editorial Domain | 定义草稿状态机 | 规范 `generated/in_review/approved/rejected/exported` 等状态流转 | `app/editorial/*`, `app/api/schemas.py` | 状态枚举与流转规则 | 非法状态迁移被拒绝 | P0 |
| T03 | Editorial Domain | 为内容流水线写入草稿记录 | 生成 markdown 时同步写入/更新草稿表 | `scripts/run_content_pipeline.py`, `app/editorial/pipeline.py` | 生成逻辑与 DB 同步 | 新草稿生成后数据库可查 | P0 |
| T04 | API | 增加草稿读取接口 | 提供草稿列表、详情、按状态筛选接口 | `app/api/routes/`, `app/api/services/` | `/drafts`, `/drafts/{id}` | 前端无需扫文件即可读草稿 | P0 |
| T05 | API | 增加草稿审核接口 | 支持 review/approve/reject/assign | `app/api/routes/`, `app/api/services/` | 写接口 | 可从 API 修改状态并持久化 | P0 |
| T06 | Export | 为导出增加状态校验 | 只允许 approved 草稿导出 | `app/publish/exporter.py`, `scripts/export_for_publish.py` | 导出约束 | 未审核草稿导出失败并给出原因 | P0 |
| T07 | Export | 记录导出审计日志 | 记录谁、何时、导出哪些草稿、结果如何 | `app/models.py`, `app/publish/*`, `app/api/*` | `ExportRecord` 模型/API | 可追踪导出历史 | P0 |
| T08 | API | 增加导出触发接口 | 前端可发起按日期/平台/草稿导出 | `app/api/routes/`, `app/api/services/` | `/exports` | 导出结果可通过 API 获取 | P1 |
| T09 | Papers API | 增加单篇论文详情接口 | 后端直接返回 paper + insight + notifications + drafts | `app/api/routes/papers.py`, `app/api/services/read_models.py` | `/papers/{paperId}` | 前端详情页不再前端拼装 | P1 |
| T10 | Papers API | 实现服务端搜索/筛选/分页 | 支持 q/source/category/venue/hasInsight/hasDraft | `app/api/routes/papers.py`, `app/api/services/read_models.py` | 查询参数支持 | `/papers` 按参数返回正确结果 | P1 |
| T11 | Notifications API | 增加通知重试接口 | 支持单篇重试和批量重试 | `run_notify_once.py`, `app/api/routes/notifications.py`, `app/api/services/notifications.py` | `/notifications/retry` | 前端可直接重试通知 | P1 |
| T12 | Pipeline API | 增加流水线触发接口 | 支持 fetch/insight/editorial/notify/export 的受控触发 | `app/api/routes/pipeline.py`, `app/api/services/` | `/pipeline/*` 写接口 | 手动操作不依赖 shell | P1 |
| T13 | Frontend | 草稿列表页 | 展示状态、责任人、更新时间、平台 | `frontend/app/`, `frontend/components/`, `frontend/lib/` | `/drafts` | 支持筛选和进入详情 | P2 |
| T14 | Frontend | 草稿详情与审核页 | 支持 approve/reject/review/assign | `frontend/app/`, `frontend/components/`, `frontend/lib/` | `/drafts/[draftId]` | 可在 UI 完成审核 | P2 |
| T15 | Frontend | 导出管理页 | 发起导出、查看导出记录、查看失败原因 | `frontend/app/`, `frontend/components/`, `frontend/lib/` | `/exports` | 导出可在 UI 操作与追踪 | P2 |
| T16 | Frontend | 论文列表高级检索 | 搜索、分页、筛选完全接后端参数 | `frontend/app/papers`, `frontend/lib/repositories/papers.ts` | UI 查询能力 | 搜索结果与后端一致 | P2 |
| T17 | Observability | 增加 crawl run 列表接口 | 展示每个 source 最近 N 次抓取状态 | `app/models.py`, `app/api/services/`, `app/api/routes/pipeline.py` | `/pipeline/runs/crawl` | 可查看历史抓取状态 | P3 |
| T18 | Observability | 增加 summarization/editorial run 记录 | 记录每次摘要/草稿生成运行情况 | `app/models.py`, `app/summarization/`, `app/editorial/` | run tables + API | 失败率、耗时可查 | P3 |
| T19 | Observability | 前端运行观测页 | 展示运行时间线、失败原因、耗时统计 | `frontend/app/pipeline`, `frontend/components/` | 运行观测 UI | 运维无需查纯日志 | P3 |
| T20 | Multi-channel | 设计发布去向记录模型 | 记录目标平台、导出/发布状态、回执 | `app/models.py`, `app/api/schemas.py` | `DestinationRecord` | 每次分发有状态记录 | P4 |
| T21 | Multi-channel | 渠道结果追踪接口 | 对外返回每个平台的分发/发布状态 | `app/api/routes/`, `app/api/services/` | destination APIs | 可按草稿查看各渠道状态 | P4 |
| T22 | Multi-channel | 对接真实发布流程（可分阶段） | 先做回写，再做自动发布 | `app/publish/`, `scripts/` | 平台适配器 | 至少能记录人工发布结果 | P4 |
| T23 | Tooling | 补齐前端 `start` 脚本 | 完整区分 dev/build/start | `frontend/package.json`, `frontend/README.md` | start 命令 | 生产启动命令可用 | P5 |
| T24 | Tooling | 规范前端缓存与 dev 启动说明 | 避免 `.next` 脏缓存导致运行异常 | `frontend/README.md`, 可选脚本文件 | 文档/脚本 | 可稳定复现启动流程 | P5 |
| T25 | Deployment | 补齐统一启动文档/脚本 | 给出前后端一套标准启动方式 | `README.md`, `frontend/README.md`, 可选 `scripts/` | 启动说明 | 新人可按文档跑通 | P5 |

---

## 3. 里程碑拆分

| 里程碑 | 包含任务 | 结果 |
|---|---|---|
| M1：草稿可治理 | T01-T07 | 草稿有状态、可审核、导出可审计 |
| M2：后端可操作 | T08-T12 | API 不再只读，核心动作可远程触发 |
| M3：前端可运营 | T13-T16 | 审核、导出、查询可在 UI 完成 |
| M4：系统可运维 | T17-T19 | 运行历史和失败原因可视化 |
| M5：分发可闭环 | T20-T22 | 导出/发布有去向记录与结果追踪 |
| M6：工程可交付 | T23-T25 | 启动、部署、文档完整 |

---

## 4. 推荐实施顺序

1. **先做 M1**：把草稿变成有状态、有审核、有导出约束的对象。
2. **再做 M2**：补齐写接口，让前端能真正操作系统。
3. **接着做 M3**：把当前只读控制台升级成运营后台。
4. **然后做 M4**：补足运行观测，减少查日志成本。
5. **最后做 M5/M6**：完善多渠道追踪与工程化交付。

---

## 5. 风险与注意事项

| 风险 | 说明 | 应对 |
|---|---|---|
| 文件扫描与数据库双源不一致 | 当前 editorial draft 部分逻辑基于扫描 `outputs/editorial/` | 先定义 DB 为主，文件系统为附属输出 |
| 现有前端查询层有本地聚合逻辑 | 新增 detail/search API 后前端需逐步切换 | 先兼容，再逐页替换 |
| 通知/流水线脚本目前是 CLI 驱动 | 直接暴露 API 可能引入并发与幂等问题 | 先做受控同步接口，后续再任务化 |
| 真实渠道发布复杂度高 | 各平台自动发布差异大 | 先做去向记录和人工回写，再做自动化 |

---

## 6. 建议的首批实施包

### 包 A（建议先做）
- T01 草稿模型
- T02 状态机
- T03 内容流水线写 DB
- T05 审核接口
- T06 导出校验
- T07 导出审计

### 包 B
- T09 论文详情 API
- T10 服务端搜索/筛选/分页
- T11 通知重试 API

### 包 C
- T13 草稿列表页
- T14 草稿详情审核页
- T15 导出管理页

---

## 7. 验收口径（项目级）

当以下条件全部满足时，可以认为本轮核心缺口已被补齐：

- 草稿不再只是文件，而是数据库中的可治理实体。
- 未审核草稿不能被导出。
- 前端可完成审核、批准、驳回、导出操作。
- 后端提供单篇论文详情与服务端查询接口。
- 通知与流水线核心动作可通过 API 触发。
- 运行历史、失败原因、分发结果可查询。
- 前端具备稳定的 dev/build/start 运行路径。

---

Plan complete and saved to `docs/superpowers/plans/2026-04-28-paperclaw-development-task-table.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - 我按任务分批派子代理执行并逐批 review。  
**2. Inline Execution** - 我在当前会话里按这个任务表直接开始实现。
