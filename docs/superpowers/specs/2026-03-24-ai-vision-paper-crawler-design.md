# AI 视觉论文抓取与通知脚本设计

## 1. 背景与目标

本项目目标是实现一个运行在 Linux 服务器上的 Python 脚本，用于定时抓取人工智能视觉方向的学术论文，并完成结构化入库与飞书通知。

当前确认的需求边界如下：

- 抓取范围以多源为主，优先覆盖 `arXiv` 与 `OpenReview`
- 运行环境为 Linux 服务器常驻场景
- 第一优先级是发现新论文后通知
- 同时要求论文数据结构化存储到数据库
- 后续预留接入飞书多维表格的能力
- 第一版先尽量全量抓取入库，只推送本次新发现论文
- 数据库先用 `SQLite`，但需要保留平滑迁移到 `PostgreSQL` 的可能
- 调度频率先按每天一次设计
- 实现语言使用 `Python`

## 2. 设计原则

- 单机优先：第一版不引入服务编排、消息队列或复杂部署组件
- 模块分层：抓取、标准化、存储、通知、入口执行分离
- 幂等执行：重复运行不应重复入库或重复发送通知
- 来源解耦：每个抓取源使用独立 adapter，便于单独维护
- 存储优先：入库成功与否不受通知结果影响
- 易扩展：后续可接入 CVF、飞书多维表格、PostgreSQL、补发机制

## 3. 方案选择

共评估过三种方案：

### 方案 A：极简单脚本

单个 `main.py` 串行完成抓取、去重、入库、通知。

优点：

- 上手最快
- 文件最少

缺点：

- 代码会迅速膨胀
- 后续扩展来源和通知渠道时代价高
- 排障困难

### 方案 B：模块化采集脚本

使用 Python 单机项目，但按 `source adapters / normalize / storage / notifier / entrypoint` 划分模块，调度交给 Linux 系统。

优点：

- 复杂度适中
- 易于扩展
- 部署简单
- 非常适合当前“每天一次抓取”的需求

缺点：

- 比极简单脚本多一点工程结构成本

### 方案 C：小型服务化架构

将抓取、入库、通知、同步等拆分为多个 worker 或服务，通过队列驱动。

优点：

- 长期扩展性最好

缺点：

- 当前场景明显过度设计
- 维护成本高

### 结论

采用方案 B：模块化采集脚本。

原因是当前目标是稳定完成“抓取 -> 入库 -> 飞书通知”，不需要服务化，但也不能将所有逻辑塞进单文件脚本。

## 4. 总体架构

### 4.1 模块划分

- `run_once.py`
  - 单次任务入口
  - 供手动执行与 `cron` 调用
- `sources/*.py`
  - 负责各来源抓取
  - 不直接发通知，不直接操作数据库
- `normalizer.py`
  - 将来源侧原始数据转为统一内部结构
- `storage.py`
  - 建表、查询、去重、插入、更新、通知记录
- `pipeline.py`
  - 编排整条业务流程
- `notifiers/feishu_bot.py`
  - 负责飞书机器人发送
- `config.py`
  - 负责环境变量与来源配置读取
- `logging.py`
  - 统一日志初始化

### 4.2 核心数据流

一次执行任务的数据流如下：

`抓取原始论文 -> 标准化 -> 生成唯一键 -> 查库去重 -> 新论文入库 -> 汇总新增 -> 飞书通知`

### 4.3 运行方式

Python 代码仅负责“执行一次任务”，不内嵌长驻调度器。

定时执行交由 Linux 系统完成，第一版优先使用 `cron`。

## 5. 数据模型设计

第一版使用 `SQLite`，但表结构与访问层应避免依赖 SQLite 专有能力，保证后续迁移到 `PostgreSQL` 时改动最小。

### 5.1 papers

用于存储标准化后的论文主记录。

建议字段：

- `id`
- `source`
- `source_paper_id`
- `title`
- `abstract`
- `authors_json`
- `paper_url`
- `pdf_url`
- `venue`
- `categories_json`
- `published_at`
- `updated_at_source`
- `first_seen_at`
- `last_seen_at`
- `dedup_key`
- `raw_payload_json`
- `created_at`
- `updated_at`

用途：

- `(source, source_paper_id)` 用于来源内唯一
- `dedup_key` 用于跨来源近似识别
- `first_seen_at` 与 `last_seen_at` 用于追踪抓取历史

### 5.2 paper_versions

用于保存论文信息变化历史。

建议字段：

- `id`
- `paper_id`
- `version_label`
- `title`
- `abstract`
- `pdf_url`
- `raw_payload_json`
- `seen_at`

用途：

- 保存 arXiv 版本变化
- 保存 OpenReview 元信息变化
- 后续可用于“论文更新通知”

### 5.3 crawl_runs

用于记录每次抓取任务的执行情况。

建议字段：

- `id`
- `started_at`
- `finished_at`
- `status`
- `source`
- `fetched_count`
- `new_count`
- `updated_count`
- `error_count`
- `error_message`

用途：

- 追踪任务是否执行成功
- 统计抓取效果
- 便于排障与失败补跑

### 5.4 notifications

用于记录通知发送历史。

建议字段：

- `id`
- `paper_id`
- `channel`
- `sent_at`
- `payload_snapshot_json`
- `status`
- `error_message`

用途：

- 防止重复通知
- 支持通知失败后重试
- 让入库与通知状态解耦

## 6. 去重策略

由于目标是“尽量全量入库，只推送新增”，所以需要稳健的幂等与去重设计。

### 6.1 同来源强唯一

基于 `(source, source_paper_id)` 建唯一约束。

适用场景：

- 同一个来源被重复抓取
- 同一天任务被手动重跑

处理策略：

- 如果已存在且无变化，仅更新 `last_seen_at`
- 如果已存在且字段变化，更新主记录并写入 `paper_versions`

### 6.2 跨来源软去重

通过 `dedup_key` 做跨来源的疑似重复识别。

建议生成方法：

- 标题转小写
- 去除标点
- 压缩空白
- 去除部分噪声字符
- 可选拼接第一作者或年份
- 最终计算 hash

处理原则：

- 第一版不做强制跨源合并
- 保留各来源原始记录
- 逻辑上标记为“疑似同论文”
- 通知时只对首次发现的主记录发送一次

这样能避免：

- 因合并规则不稳定造成误杀
- 因不同来源重复出现造成飞书刷屏

## 7. 统一数据结构

内部建议定义统一的 `PaperRecord` 数据结构。

建议字段：

- `source`
- `source_paper_id`
- `title`
- `abstract`
- `authors`
- `paper_url`
- `pdf_url`
- `venue`
- `categories`
- `published_at`
- `updated_at_source`
- `first_seen_at`
- `last_seen_at`
- `dedup_key`
- `raw_payload`

这样所有来源只需要输出统一结构，后续无论是入库、通知还是同步飞书多维表格，都可以复用同一套上层逻辑。

## 8. 来源抓取设计

### 8.1 arXiv

第一版推荐优先抓取：

- `cs.CV`
- 可配置预留 `cs.AI`
- 可配置预留 `cs.LG`

建议实现：

- 使用官方 API 或可稳定解析的 Atom feed
- 每次抓最近 `1-3` 天的更新窗口

建议重点字段：

- arXiv id
- title
- summary
- authors
- published
- updated
- pdf url

说明：

- `cs.AI` 与 `cs.LG` 噪声会较大
- 第一版默认只开启 `cs.CV`
- 其他分类作为配置项预留

### 8.2 OpenReview

第一版不抓全站，只抓 venue 白名单。

推荐起步 venue：

- `CVPR`
- `ICCV`
- `ECCV`

建议实现：

- 调用 OpenReview API
- 基于 venue 或 note 时间窗口抓取最近 `3` 天数据

建议重点字段：

- note id
- title
- abstract
- authors
- forum / paper link
- pdf
- venue
- cdate / mdate

说明：

- OpenReview 的会议配置并不统一
- 第一版不要追求万能解析
- 每个 venue 应允许单独配置

### 8.3 CVF

第一版作为预留来源，不强制纳入 MVP 实现。

未来用途：

- 补充 `CVPR / ICCV / ECCV / WACV` 公开论文页面

实现建议：

- 每个会议单独 adapter
- 解析论文列表页中的标题、作者、论文页、PDF 链接

风险：

- 页面结构会变化
- 不同届次 URL 结构不一定一致

因此更适合在 MVP 稳定后再补。

## 9. 执行流程设计

一次定时任务建议执行如下步骤：

1. 创建 `crawl_run`
2. 逐个来源抓取数据
3. 标准化为 `PaperRecord`
4. 执行去重判定
5. 写入新论文或更新已有论文
6. 汇总“本次新增且未通知”的论文
7. 发送飞书通知
8. 写入通知结果
9. 更新 `crawl_run` 执行结果

### 9.1 错误隔离

每个来源必须独立错误处理。

原则：

- `arXiv` 失败不影响 `OpenReview`
- 某个来源失败时任务仍应继续
- 最终在摘要日志与飞书摘要中体现失败来源

### 9.2 幂等性要求

脚本必须支持安全重跑：

- 同一天手工重复执行，不重复入库
- 已推送论文不重复通知
- 飞书失败不影响论文入库
- 某个来源失败后，下一次执行仍可补抓

### 9.3 默认抓取窗口

推荐默认值：

- `arXiv`：最近 2 天
- `OpenReview`：最近 3 天
- `CVF`：最近 7 天或最新论文页全量拉取后由数据库去重

这样即使偶发漏跑，也能通过回看窗口降低漏抓概率。

## 10. 飞书通知设计

### 10.1 通知目标

第一版通知以飞书机器人 webhook 为主。

主流程要求：

- 论文先成功入库
- 再对本次新增论文发送通知
- 通知失败不回滚数据库事务

### 10.2 消息层次

建议每次执行发送两类信息：

#### 摘要消息

包含：

- 执行时间
- 抓取来源
- 抓取总数
- 新增论文数
- 失败来源数

作用：

- 让使用者确认任务正常运行
- 即使当天没有新增，也能知道调度正常

#### 新增论文明细

每篇建议展示：

- 标题
- 来源
- venue 或分类
- 发布时间
- 论文页链接
- PDF 链接

设计原则：

- 第一版不展示长摘要
- 单次通知限制最多展示 `10-20` 篇
- 超出部分提示“其余 X 篇已入库”

### 10.3 失败处理

当飞书发送失败时：

- 数据库事务不回滚
- 在 `notifications` 中记录 `failed`
- 保留失败原因
- 后续可增加补发命令

## 11. 定时任务设计

### 11.1 选型

运行环境为 Linux 服务器，第一版优先使用 `cron`。

理由：

- 简单
- 稳定
- 部署与排障成本低

`systemd timer` 作为后续可选升级项，不作为 MVP 默认方案。

### 11.2 调度方式

调度不写入 Python 常驻进程，Python 代码只保留单次执行入口。

示例：

```cron
0 8 * * * cd /root/workspace/paperclaw && /usr/bin/python3 run_once.py >> logs/cron.log 2>&1
```

### 11.3 日志要求

建议保留两层日志：

- 应用日志：记录抓取、去重、入库、通知细节
- 调度日志：确认任务是否被系统正常拉起

## 12. 项目目录结构

建议目录结构如下：

```text
paperclaw/
  run_once.py
  pyproject.toml
  .env.example
  config/
    sources.yaml
  app/
    __init__.py
    config.py
    models.py
    schemas.py
    normalizer.py
    storage.py
    logging.py
    pipeline.py
    scheduler/
      __init__.py
    sources/
      __init__.py
      base.py
      arxiv.py
      openreview.py
      cvf.py
    notifiers/
      __init__.py
      feishu_bot.py
    utils/
      __init__.py
      hashers.py
      time.py
  data/
    papers.db
  logs/
```

## 13. 配置设计

### 13.1 环境变量

建议放入 `.env`：

- `APP_ENV`
- `DATABASE_URL`
- `FEISHU_BOT_WEBHOOK`
- `LOG_LEVEL`
- `TIMEZONE`
- `MAX_NOTIFY_ITEMS`

### 13.2 来源配置

建议放入 `config/sources.yaml`：

```yaml
arxiv:
  enabled: true
  categories:
    - cs.CV
  lookback_days: 2

openreview:
  enabled: true
  venues:
    - CVPR
    - ICCV
    - ECCV
  lookback_days: 3

cvf:
  enabled: false
  conferences:
    - CVPR
    - ICCV
    - ECCV
    - WACV
  lookback_days: 7
```

## 14. MVP 范围

为尽快交付一个可运行版本，第一版建议只做如下范围：

### 14.1 来源范围

纳入 MVP：

- `arXiv`
- `OpenReview`

暂不纳入 MVP：

- `CVF`

原因：

- `arXiv + OpenReview` 已足以覆盖大量视觉 AI 新论文
- `CVF` 页面抓取更容易受网页结构影响
- 先把核心链路跑通更合理

### 14.2 核心能力

- 自动建表
- 幂等入库
- 任务执行记录
- 飞书机器人通知
- 配置化来源开关
- 每天一次系统调度

### 14.3 明确不做

第一版不做以下内容：

- 复杂关键词筛选
- 深度摘要生成
- 全站历史回填
- 多通知渠道并发发送
- 飞书多维表格同步
- PostgreSQL 生产迁移

## 15. 第二阶段扩展方向

当 MVP 跑稳后，推荐扩展顺序如下：

1. 增加 `CVF` 抓取
2. 增加飞书多维表格同步
3. 增加通知失败补发命令
4. 增加更稳健的跨来源合并逻辑
5. 迁移到 `PostgreSQL`
6. 增加论文标签、关键词分类、优先级评分

## 16. 测试与验证建议

第一版实现后，至少需要验证以下场景：

- 首次运行时可以成功建表
- 同一天重复运行不会重复插入相同论文
- 论文重复抓到时只更新 `last_seen_at`
- 论文元数据变化时会写入 `paper_versions`
- 飞书发送失败时不会影响论文入库
- 某一来源抓取异常不会阻断其他来源执行
- `cron` 触发执行后日志可追踪

## 17. 最终建议

当前推荐的第一版落地基线如下：

- Python
- 模块化单机项目
- 单次执行入口 `run_once.py`
- Linux `cron` 每天一次
- `arXiv + OpenReview`
- `SQLite`
- 飞书机器人通知
- `papers / paper_versions / crawl_runs / notifications` 四张表

该设计在复杂度、可维护性和未来扩展之间达成了较稳妥的平衡，适合作为本项目的第一版实现基础。
