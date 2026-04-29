# PaperClaw 多源顶刊顶会抓取与内容分发实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 PaperClaw 基础上，扩展为“多来源顶刊顶会论文发现 + 正文获取 + 创新点总结 + 多平台内容产出（B站/小红书/抖音）”的一体化流水线，并确保可在 Codex 晚间迭代执行。

**Architecture:** 采用分层流水线：`Source Connectors -> Canonical Paper Store -> Enrichment/Summarization -> Editorial Generator -> Publisher Connectors`。抓取与内容生成解耦，统一落库并通过任务状态机驱动，支持失败重试、幂等执行与增量更新。短期以“先产出可审阅文案，再半自动发布”为主，后续再扩展自动发布。

**Tech Stack:** Python 3.12, SQLAlchemy, httpx, pydantic, pypdf, lxml/BeautifulSoup, readability/trafilatura, Jinja2, Markdown/HTML, pytest, APScheduler/cron, optional Redis queue

---

## 0. 现状评估（基于当前仓库）

当前 `/root/workspace/paperclaw` 已具备：

- 已实现来源：
  - `arXiv`（`app/sources/arxiv.py`）
  - `OpenReview`（`app/sources/openreview.py`）
- 已预留但未实现：
  - `CVF`（`app/sources/cvf.py` 仅 `NotImplementedError`）
- 已有能力：
  - 论文基础字段入库（`papers` / `paper_versions`）
  - PDF 文本提取（`BaseSource._fetch_full_text`）
  - 去重/幂等更新（按 `source + source_paper_id`，并有 `dedup_key`）
  - 通知链路（飞书）
- 缺口（对应你的目标）：
  - 顶刊顶会来源覆盖不足（IEEE/ACM/Springer/Nature/Science/CVF等）
  - 没有“论文创新点结构化总结”字段与任务
  - 没有“面向平台的内容改写”与多平台输出模板
  - 没有发布编排（审稿->出稿->分发）状态机
  - 缺少反爬/限流/版权策略层

> 结论：现有项目是“抓取与通知 MVP”，离“内容生产+分发系统”差一层内容工厂和发布编排层。

---

## 1. 目标边界与原则

### 1.1 目标（本轮方案）

1. 覆盖主流高价值论文来源（优先 API/官方渠道）
2. 稳定获取元数据与可用正文（含降级策略）
3. 自动生成：
   - 技术摘要
   - 创新点（3~5条）
   - 适用场景/局限
   - 一句话结论
4. 生成平台化内容草稿：
   - B站：长文脚本/视频口播提纲
   - 小红书：图文风格短帖
   - 抖音：短视频分镜+口播
5. 输出可审核的发布包（先半自动发布，避免直接违规自动发）

### 1.2 原则

- **数据优先级**：官方 API > 官方 RSS/Feed > 网页抓取
- **合规优先**：遵守 robots.txt / ToS / 版权边界（摘要可引用，正文不对外再分发）
- **幂等与可回放**：所有任务可重跑，不重复产出垃圾内容
- **人工兜底**：生成内容先审后发，先保证质量与账号安全

---

## 2. 总体架构（升级后）

```text
[Source Scheduler]
   -> [Connector Layer: arXiv/OpenReview/CVF/IEEE/ACM/...]
   -> [Normalize + Dedup]
   -> [Paper Store]
   -> [Content Extractor]
   -> [LLM Summarizer]
   -> [Editorial Composer]
   -> [Review Queue]
   -> [Publisher Adapters: Bilibili/XHS/Douyin]
   -> [Metrics & Logs]
```

### 2.1 核心子系统

1. **Connector Layer**：不同来源统一协议（fetch list / fetch detail）
2. **Paper Store**：论文主表、版本表、处理状态表
3. **Enrichment**：正文提取、章节切分、引用信息提炼
4. **Summarizer**：标准化提示词生成结构化 JSON 结论
5. **Composer**：按平台模板输出最终文案包
6. **Publisher**：先支持导出待发布稿；后接 API/自动化工具
7. **Observability**：成功率、耗时、失败原因、重复率、内容评分

---

## 3. 数据来源分级实施

## Tier-1（今晚优先）

- arXiv（已上线，增强类别/分页）
- OpenReview（已上线，增强 venue mapping）
- CVF OpenAccess（补齐实现）

## Tier-2（下一阶段）

- Semantic Scholar API（高性价比聚合元数据）
- Crossref（DOI 元信息增强）
- ACL Anthology（NLP顶会）

## Tier-3（谨慎推进）

- IEEE Xplore / ACM DL / Springer / Nature 等（通常有访问或授权限制）

> 对 Tier-3，优先“索引元数据 + 官方链接”，不要非法镜像全文。

---

## 4. 数据模型升级（建议）

在现有 `papers / paper_versions / crawl_runs / notifications` 基础上新增：

### 4.1 新增表

- `paper_assets`
  - `paper_id`, `asset_type`(pdf/html/supp/code), `url`, `local_path`, `fetch_status`, `checksum`
- `paper_insights`
  - `paper_id`, `summary_short`, `summary_long`, `novelty_points(json)`, `limitations(json)`, `applications(json)`, `confidence_score`
- `editorial_drafts`
  - `paper_id`, `platform`(bilibili/xhs/douyin), `title`, `hook`, `body`, `tags(json)`, `status`(draft/reviewed/published)
- `publish_records`
  - `draft_id`, `platform`, `publish_status`, `publish_url`, `error_message`, `published_at`

### 4.2 现有表补充字段

- `papers`：
  - `doi`, `citation_count`, `primary_domain`, `language`, `content_quality_score`

---

## 5. 今晚执行路线（Codex 可直接落地）

> 目标：一晚内从“抓取MVP”升级到“可生成平台稿件的内容流水线 alpha”。

### 阶段 A（1~1.5h）：补齐来源与配置骨架

- 实现 `CVFSource.fetch()`（至少支持 ICCV/CVPR/ECCV 最近论文索引）
- 扩展 `config/sources.yaml` 为多源结构：
  - 每源 `enabled`, `lookback_days`, `rate_limit`, `priority`
- 增加 source 级测试：`tests/test_cvf_source.py` 从 placeholder 改为真实解析测试

**交付物**
- 可运行的 CVF connector
- 配置模板升级
- 单测通过

**验收**
- `pytest tests/test_cvf_source.py -q` 通过
- `run_once.py` 能在 summary 中看到 `cvf` 成功抓取统计

---

### 阶段 B（1.5~2h）：增加内容提炼层（Enrichment + Summarize）

新增模块建议：

- `app/enrichment/extractor.py`
  - 统一正文获取策略：`full_text > abstract > landing page excerpt`
- `app/enrichment/chunker.py`
  - 文本分段（按 token/段落）
- `app/summarization/schemas.py`
  - `PaperInsight` pydantic schema
- `app/summarization/service.py`
  - 生成结构化输出：摘要、创新点、局限、适用场景

**交付物**
- `paper_insights` 入库链路
- 至少 3 条样例论文完成 insight 生成

**验收**
- 新增测试：
  - `tests/test_extractor.py`
  - `tests/test_summarization_service.py`
- 运行后 DB 中存在 `paper_insights` 记录

---

### 阶段 C（1.5~2h）：平台文案生成（B站/小红书/抖音）

新增模块建议：

- `app/editorial/templates/`
  - `bilibili.md.j2`
  - `xiaohongshu.md.j2`
  - `douyin.md.j2`
- `app/editorial/composer.py`
  - 将 `paper + insight` 组合为平台文案
- `app/editorial/pipeline.py`
  - 批量生成 `editorial_drafts`

模板最低要求：

- B站：
  - 标题、开场Hook、3段核心创新点、结尾讨论问题
- 小红书：
  - 强情绪标题、3~5条要点、标签建议
- 抖音：
  - 30~60秒口播脚本、分镜（3~5镜头）

**交付物**
- 一键生成三平台草稿
- 草稿入库或导出到 `outputs/editorial/YYYY-MM-DD/`

**验收**
- 同一论文可生成 3 平台各 1 篇草稿
- 每篇含标题、正文、标签建议

---

### 阶段 D（0.5~1h）：人工审核与发布准备

- 增加简易审核命令：
  - `python review_queue.py list`
  - `python review_queue.py approve <draft_id>`
- 增加导出命令：
  - `python export_for_publish.py --platform xiaohongshu --status reviewed`

**交付物**
- 审核状态流转（draft -> reviewed）
- 可投放素材包（Markdown/CSV）

**验收**
- 可以筛选已审核内容并导出

---

## 6. 代码结构建议（对应当前仓库）

在现有结构上新增：

- `app/enrichment/`
  - `__init__.py`
  - `extractor.py`
  - `chunker.py`
- `app/summarization/`
  - `__init__.py`
  - `schemas.py`
  - `service.py`
- `app/editorial/`
  - `__init__.py`
  - `composer.py`
  - `pipeline.py`
  - `templates/*.j2`
- `app/publish/`
  - `__init__.py`
  - `exporter.py`
  - `adapters/`（先空实现）
- `scripts/`
  - `run_content_pipeline.py`
  - `review_queue.py`
  - `export_for_publish.py`

测试新增：

- `tests/test_extractor.py`
- `tests/test_summarization_service.py`
- `tests/test_editorial_composer.py`
- `tests/test_review_queue.py`

---

## 7. Codex 执行分工建议（今晚）

可并行开 3 个 Codex 任务（worktree 或临时分支）：

1. **Track-A 来源层**
   - CVF 实现 + source config 扩展 + 相关测试
2. **Track-B 总结层**
   - insight schema + summarization service + DB迁移
3. **Track-C 文案层**
   - 平台模板 + composer + draft 存储/导出

最后主分支做集成与回归测试。

推荐合并顺序：A -> B -> C（C 依赖 B 的 insight 数据）。

---

## 8. 风险与规避

1. **版权/平台风控风险**
   - 不直接搬运全文，不伪造原创；输出“研究解读”而非“论文转载”
2. **反爬封禁风险**
   - 限速、重试、User-Agent、缓存；优先官方 API
3. **LLM 幻觉风险**
   - 输出结构化 JSON + 引文片段 + 置信度；低分内容进人工复核
4. **内容同质化风险**
   - 模板参数化 + 受众画像（工程向/科普向）双模板

---

## 9. 验收标准（本方案完成态）

满足以下即视为第一阶段完成：

- 至少 3 个来源稳定抓取（arXiv/OpenReview/CVF）
- 每篇新论文可自动生成 `paper_insights`
- 每篇可生成 3 平台草稿（B站/小红书/抖音）
- 有审核状态与导出能力
- 关键链路单测覆盖并可在 CI 本地跑通

---

## 10. 今晚建议的最小可交付（MVP+）

如果时间紧，优先做这 4 件：

1. CVF 来源实现并入主 pipeline
2. `paper_insights` 表 + 自动总结服务
3. 小红书 + 抖音 两套模板先跑通（B站次优先）
4. 导出 reviewed 草稿为 Markdown 包

这样你今晚就能拿到“可直接二次编辑后发布”的内容资产。
