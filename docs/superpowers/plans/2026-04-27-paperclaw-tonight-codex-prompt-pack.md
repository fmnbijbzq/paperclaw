# PaperClaw Tonight Codex Prompt Pack（多源抓取 + 创新点总结 + 多平台文案）

生成时间：2026-04-27 00:28:17 UTC
项目路径：`/root/workspace/paperclaw`
建议执行分支：`feature/content-factory-alpha`

---

## 使用说明（先看）

1. 进入项目目录并创建分支：

```bash
cd /root/workspace/paperclaw
git checkout -b feature/content-factory-alpha
```

2. 当前仓库有未提交改动（`git status` 显示多个 `M` 与未跟踪目录），为避免污染本次任务，请先做其一：
   - 方案A：提交当前改动后再跑本包
   - 方案B：`git stash -u` 后再跑本包

3. 本包分为 3 个可并行 Track（A/B/C）+ 1 个集成 Track（D）。

4. 每个 Track 都提供：
   - 任务目标
   - 可直接复制给 Codex 的 Prompt
   - 验收命令

5. 建议使用 PTY 执行 Codex（Hermes/终端同理）：

```bash
codex exec "<PROMPT>"
```

---

## 全局约束（给每个 Codex 子任务都附带）

请将以下约束粘贴到每个 Prompt 顶部：

```text
You are working in /root/workspace/paperclaw.
Constraints:
1) Keep changes minimal and production-safe; preserve existing behavior unless required.
2) Prefer TDD: add/adjust tests first, then implementation.
3) Do NOT use destructive git commands.
4) Use existing project patterns (SQLAlchemy + pydantic + pytest).
5) If DB schema changes are needed, keep backward compatibility for existing SQLite databases.
6) Run targeted tests before finishing and report exact commands/results.
7) Return a concise change summary with touched files.
```

---

## Track-A：来源层（CVF 实现 + 配置增强）

### 目标

- 将 `app/sources/cvf.py` 从 placeholder 改为可用抓取器
- 支持 CVPR / ICCV / ECCV 最近论文索引抓取（先元数据 + 链接）
- 扩展 `config/sources.yaml` 结构（enabled/lookback_days/priority/rate_limit）并兼容现有逻辑
- 增加或改造测试使其可验证

### 建议关注文件

- `app/sources/cvf.py`
- `app/sources/__init__.py`
- `run_once.py`
- `app/config.py`
- `config/sources.yaml`
- `tests/test_cvf_source.py`
- （必要时）`tests/test_run_once.py`

### 可直接给 Codex 的 Prompt（Track-A）

```text
You are working in /root/workspace/paperclaw.
Constraints:
1) Keep changes minimal and production-safe; preserve existing behavior unless required.
2) Prefer TDD: add/adjust tests first, then implementation.
3) Do NOT use destructive git commands.
4) Use existing project patterns (SQLAlchemy + pydantic + pytest).
5) If DB schema changes are needed, keep backward compatibility for existing SQLite databases.
6) Run targeted tests before finishing and report exact commands/results.
7) Return a concise change summary with touched files.

Task:
Implement a production-usable CVF source adapter to replace the current NotImplementedError placeholder.

Requirements:
- Implement app/sources/cvf.py fetch() to return list[PaperRecord].
- Support configurable conferences/tokens (CVPR/ICCV/ECCV) and recent papers list.
- Use robust parsing (HTML parsing is acceptable) with graceful fallback if fields are missing.
- Map fields into PaperRecord: source, source_paper_id, title, abstract(optional), authors(optional), paper_url, pdf_url(optional), venue(optional), categories(optional), raw_payload.
- Keep idempotency expectations: source must be "cvf" and source_paper_id stable/deterministic.
- Update run_once.py to load CVF source from config when enabled.
- Extend config/sources.yaml to include cvf section and allow future per-source keys: enabled/lookback_days/priority/rate_limit.
- Ensure existing arxiv/openreview behavior remains compatible.

Testing:
- Rewrite tests/test_cvf_source.py from placeholder test to parser behavior tests using mocked HTTP transport.
- Add/adjust tests for run_once source initialization if needed.
- Run: pytest tests/test_cvf_source.py -q
- Run any impacted tests and report results.

Deliverables:
- Code changes
- Test results
- Short rationale for source_paper_id strategy and parsing assumptions.
```

### 验收命令

```bash
cd /root/workspace/paperclaw
pytest tests/test_cvf_source.py -q
pytest tests/test_run_once.py -q
```

---

## Track-B：总结层（paper_insights + 结构化总结服务）

### 目标

- 新增 `paper_insights` 数据模型与存储接口
- 实现“从论文内容生成结构化 insight”的服务层（先规则/模板版本，后续可接 LLM）
- 接入主流程（不影响现有 pipeline 的稳定）

### 建议关注文件

- `app/models.py`
- `app/storage.py`
- `app/schemas.py`
- 新增：
  - `app/summarization/__init__.py`
  - `app/summarization/schemas.py`
  - `app/summarization/service.py`
  - `app/enrichment/extractor.py`（可选）
- `app/pipeline.py`（轻量接线）
- 测试：
  - `tests/test_storage.py`
  - 新增 `tests/test_summarization_service.py`

### 可直接给 Codex 的 Prompt（Track-B）

```text
You are working in /root/workspace/paperclaw.
Constraints:
1) Keep changes minimal and production-safe; preserve existing behavior unless required.
2) Prefer TDD: add/adjust tests first, then implementation.
3) Do NOT use destructive git commands.
4) Use existing project patterns (SQLAlchemy + pydantic + pytest).
5) If DB schema changes are needed, keep backward compatibility for existing SQLite databases.
6) Run targeted tests before finishing and report exact commands/results.
7) Return a concise change summary with touched files.

Task:
Add an insights layer that generates structured innovation summaries per paper.

Requirements:
1) Data model:
- Add PaperInsight ORM model/table (paper_insights) with fields:
  paper_id(FK papers),
  summary_short,
  summary_long,
  novelty_points(JSON array),
  limitations(JSON array),
  applications(JSON array),
  confidence_score(float optional),
  created_at, updated_at.
- Add storage methods for upsert/get insights by paper_id.
- Keep SQLite migration backward compatible in existing create_schema migration style.

2) Schemas/service:
- Add pydantic schema for insight payload.
- Implement summarization service that accepts a paper (title/abstract/full_text) and returns structured insight.
- For now, deterministic/rule-based summarization is acceptable (no external LLM dependency required), but design API so an LLM backend can be plugged in later.
- Ensure empty/full_text-missing cases still produce usable summaries using abstract/title fallback.

3) Pipeline integration:
- Integrate optional insight generation in pipeline without breaking existing tests.
- Keep current run behavior compatible even if insight generation fails (log and continue).

Testing:
- Add tests for summarization service output schema and fallback behavior.
- Add storage tests for paper_insights upsert/read.
- Run targeted tests and report command outputs.

Deliverables:
- Code + tests
- Notes on future LLM integration points.
```

### 验收命令

```bash
cd /root/workspace/paperclaw
pytest tests/test_storage.py -q
pytest tests/test_summarization_service.py -q
pytest tests/test_pipeline.py -q
```

---

## Track-C：文案层（三平台草稿生成 + 导出）

### 目标

- 基于 `paper + insight` 生成平台化草稿（B站/小红书/抖音）
- 提供可落盘导出（Markdown/JSON）
- 增加最小审核状态（draft/reviewed）能力（可先文件级）

### 建议关注文件

- 新增：
  - `app/editorial/__init__.py`
  - `app/editorial/composer.py`
  - `app/editorial/pipeline.py`
  - `app/editorial/templates/bilibili.md.j2`
  - `app/editorial/templates/xiaohongshu.md.j2`
  - `app/editorial/templates/douyin.md.j2`
  - `app/publish/exporter.py`
  - `scripts/run_content_pipeline.py`
  - `scripts/export_for_publish.py`
- 可选 DB 表（若你希望先入库）：`editorial_drafts`
- 测试：
  - `tests/test_editorial_composer.py`

### 可直接给 Codex 的 Prompt（Track-C）

```text
You are working in /root/workspace/paperclaw.
Constraints:
1) Keep changes minimal and production-safe; preserve existing behavior unless required.
2) Prefer TDD: add/adjust tests first, then implementation.
3) Do NOT use destructive git commands.
4) Use existing project patterns (SQLAlchemy + pydantic + pytest).
5) If DB schema changes are needed, keep backward compatibility for existing SQLite databases.
6) Run targeted tests before finishing and report exact commands/results.
7) Return a concise change summary with touched files.

Task:
Build an editorial drafting layer for bilibili/xiaohongshu/douyin from paper + insights.

Requirements:
- Create a composer module that takes canonical paper metadata + insight object and generates platform drafts.
- Add 3 platform templates (bilibili, xiaohongshu, douyin) with distinct style:
  - bilibili: longer educational script format
  - xiaohongshu: concise bullet style with hashtag suggestions
  - douyin: 30-60s spoken script + simple shot breakdown
- Include title/hook/body/tags in output structure.
- Add export utility that writes drafts to outputs/editorial/<date>/ as markdown files.
- Keep implementation deterministic/testable (no online API required).
- Optional: if adding DB persistence for drafts, keep migration backward compatible.

Testing:
- Add tests/test_editorial_composer.py to verify non-empty drafts for 3 platforms and key fields.
- Run targeted tests and report commands/results.

Deliverables:
- Code + templates + tests
- Example generated files path.
```

### 验收命令

```bash
cd /root/workspace/paperclaw
pytest tests/test_editorial_composer.py -q
python scripts/run_content_pipeline.py --limit 3
python scripts/export_for_publish.py --date $(date +%F)
```

---

## Track-D：集成与回归（最后执行）

### 目标

- 汇总 A/B/C 成果并完成最小端到端演示
- 确保不破坏现有抓取与通知流程

### 可直接给 Codex 的 Prompt（Track-D）

```text
You are working in /root/workspace/paperclaw.
Constraints:
1) Keep changes minimal and production-safe; preserve existing behavior unless required.
2) Prefer TDD: add/adjust tests first, then implementation.
3) Do NOT use destructive git commands.
4) Use existing project patterns (SQLAlchemy + pydantic + pytest).
5) If DB schema changes are needed, keep backward compatibility for existing SQLite databases.
6) Run targeted tests before finishing and report exact commands/results.
7) Return a concise change summary with touched files.

Task:
Integrate latest source + insights + editorial tracks and run end-to-end regression.

Requirements:
- Ensure run_once.py still works and summary output remains meaningful.
- Ensure new capabilities can run in a separate command/script without forcing existing daily run to fail.
- Add/update README usage section for new workflow:
  fetch -> insight -> editorial -> export.
- Run key tests and provide a final checklist.

Test checklist (minimum):
- pytest tests/test_arxiv_source.py -q
- pytest tests/test_openreview_source.py -q
- pytest tests/test_cvf_source.py -q
- pytest tests/test_pipeline.py -q
- pytest tests/test_storage.py -q
- pytest tests/test_notification_pipeline.py -q
- pytest tests/test_editorial_composer.py -q
- pytest tests/test_summarization_service.py -q

Deliverables:
- Final integration summary
- Any follow-up technical debt list.
```

---

## 推荐执行顺序

1. Track-A（来源）
2. Track-B（总结）
3. Track-C（文案）
4. Track-D（集成）

并行时建议 A/B/C 各自分支，最后用 D 分支集成。

---

## 快速复制版（单条总控 Prompt）

如果你只想给 Codex 一条总任务，用下面这条：

```text
In /root/workspace/paperclaw, implement an alpha content-factory upgrade in four phases:
(A) CVF source implementation + config extension,
(B) paper_insights schema/storage/service,
(C) platform editorial drafts for bilibili/xiaohongshu/douyin with export,
(D) integration and regression.
Use TDD style with targeted tests for each phase, keep backward compatibility with existing SQLite schema migration style, and avoid breaking current run_once notification workflow.
Return after each phase with changed files, commands run, and results.
```

---

## 你今晚执行时的注意点

- 你当前仓库存在未提交改动，建议先 `stash` 或先提交，避免 Codex 改到无关文件。
- 先完成可审稿导出，不要急着做自动发布 API（风控和平台限制复杂）。
- 优先保证：抓取稳定性 > insight 结构化正确性 > 文案数量。

---

如果你需要，我下一步可以再给你一份“**Hermes 一键并行启动 A/B/C 的命令模板**”，你直接复制执行即可。