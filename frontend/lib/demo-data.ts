import type {
  EditorialDraftItem,
  ExportRecordItem,
  NotificationItem,
  PaperInsightItem,
  PaperItem,
  PipelineStageItem,
  SourceHealthItem,
} from "./types.ts";

export const papers: PaperItem[] = [
  {
    paperId: 101,
    sourcePaperId: "arxiv-2404.01812",
    title: "Sparse Field Priors for Open-Vocabulary 3D Scene Understanding",
    abstract:
      "A multimodal 3D understanding pipeline that uses sparse field priors to recover scene structure from a small set of open-vocabulary prompts.",
    authors: ["Ava Patel", "Jonas Richter", "Luca Morel"],
    source: "arxiv",
    venue: "arXiv",
    categories: ["3d-vision", "open-vocabulary", "multimodal"],
    paperUrl: "https://arxiv.org/abs/2404.01812",
    pdfUrl: "https://arxiv.org/pdf/2404.01812.pdf",
    publishedAt: "2026-04-25T10:30:00Z",
    updatedAtSource: "2026-04-26T02:15:00Z",
  },
  {
    paperId: 102,
    sourcePaperId: "or-iclr26-graph-executor",
    title: "Graph Executors for Long-Horizon Agentic Research Tasks",
    abstract:
      "Introduces a planner-executor training recipe that stabilizes long-horizon research agents across multi-stage retrieval and reasoning tasks.",
    authors: ["Keira Holt", "Samir Gupta", "Nikhil Rao"],
    source: "openreview",
    venue: "ICLR 2026 Submission",
    categories: ["agents", "reasoning", "workflow-systems"],
    paperUrl: "https://openreview.net/forum?id=graph-executor",
    pdfUrl: "https://openreview.net/pdf?id=graph-executor",
    publishedAt: "2026-04-24T13:05:00Z",
    updatedAtSource: "2026-04-24T13:05:00Z",
  },
  {
    paperId: 103,
    sourcePaperId: "cvf-cvpr26-replay-compression",
    title: "Replay Compression for Real-Time Egocentric Perception",
    abstract:
      "Compresses egocentric perception buffers without losing retrieval quality, enabling faster downstream summarization and event selection.",
    authors: ["Elena Voss", "Marco Bellini", "Priya Iyer"],
    source: "cvf",
    venue: "CVPR 2026",
    categories: ["egocentric", "video", "compression"],
    paperUrl: "https://openaccess.thecvf.com/content/CVPR2026/html/replay-compression.html",
    pdfUrl: "https://openaccess.thecvf.com/content/CVPR2026/papers/replay-compression.pdf",
    publishedAt: "2026-04-22T08:20:00Z",
    updatedAtSource: "2026-04-22T08:20:00Z",
  },
  {
    paperId: 104,
    sourcePaperId: "arxiv-2404.09280",
    title: "Cross-Source Alignment for Paper Insight Normalization",
    abstract:
      "Studies how paper metadata and model-generated insights can be normalized across arXiv, OpenReview, and CVF without manual correction loops.",
    authors: ["Mina Seong", "Victor Alvarez"],
    source: "arxiv",
    venue: "arXiv",
    categories: ["normalization", "metadata", "evaluation"],
    paperUrl: "https://arxiv.org/abs/2404.09280",
    pdfUrl: "https://arxiv.org/pdf/2404.09280.pdf",
    publishedAt: "2026-04-20T17:40:00Z",
    updatedAtSource: "2026-04-21T05:00:00Z",
  },
  {
    paperId: 105,
    sourcePaperId: "or-icml26-gaussian-video",
    title: "Gaussian Slots for Controllable Video World Models",
    abstract:
      "Represents video dynamics as slot-conditioned Gaussian fields, making downstream generation and planning more editable.",
    authors: ["Mei Chen", "Rafael Costa", "Lena Berg"],
    source: "openreview",
    venue: "ICML 2026 Submission",
    categories: ["video", "world-models", "gaussian-representations"],
    paperUrl: "https://openreview.net/forum?id=gaussian-video",
    pdfUrl: "https://openreview.net/pdf?id=gaussian-video",
    publishedAt: "2026-04-19T09:10:00Z",
    updatedAtSource: "2026-04-19T09:10:00Z",
  },
  {
    paperId: 106,
    sourcePaperId: "cvf-cvpr26-robot-vision-index",
    title: "Robot Vision Indexes for Fast Failure Analysis",
    abstract:
      "Builds retrieval-friendly robot vision indexes so operations teams can investigate drift, failure cases, and annotation gaps in minutes.",
    authors: ["Hanna Weber", "Tobias Koch", "Rina Sato"],
    source: "cvf",
    venue: "CVPR 2026",
    categories: ["robotics", "retrieval", "operations"],
    paperUrl: "https://openaccess.thecvf.com/content/CVPR2026/html/robot-vision-index.html",
    pdfUrl: "https://openaccess.thecvf.com/content/CVPR2026/papers/robot-vision-index.pdf",
    publishedAt: "2026-04-26T06:45:00Z",
    updatedAtSource: "2026-04-26T06:45:00Z",
  },
];

export const insights: PaperInsightItem[] = [
  {
    insightId: 501,
    paperId: 101,
    summaryShort: "Sparse field priors let the system reconstruct semantically labeled scenes from far fewer prompts than prior open-vocabulary pipelines.",
    summaryLong:
      "The paper combines sparse 3D field estimation with language-guided scene labeling so the system can recover useful geometry before dense prompting. In practice, that reduces prompt cost, stabilizes object grounding, and improves downstream scene search for research teams tracking multiple experiments.",
    noveltyPoints: [
      "Moves open-vocabulary 3D labeling earlier in the reconstruction stack instead of after dense feature extraction.",
      "Separates geometry recovery from label attachment, which makes incremental scene updates cheaper.",
      "Shows better prompt efficiency on large indoor scans.",
    ],
    limitations: [
      "Indoor-heavy evaluation leaves outdoor robustness unclear.",
      "Sparse priors degrade when camera trajectories are highly redundant.",
    ],
    applications: [
      "3D experiment review consoles",
      "Robotics mapping audits",
      "Dataset triage for multimodal labs",
    ],
    confidenceScore: 0.92,
    updatedAt: "2026-04-26T03:00:00Z",
  },
  {
    insightId: 502,
    paperId: 102,
    summaryShort: "A graph executor policy keeps multi-step research agents on plan even when retrieval or summarization steps fail mid-run.",
    summaryLong:
      "The authors model the research workflow as a typed execution graph with recovery edges, allowing the agent to re-enter a task at the right node rather than restarting the entire run. For operations teams, the important takeaway is observability: retries, skipped edges, and completion state become explicit pipeline events.",
    noveltyPoints: [
      "Represents planner state as typed graph nodes instead of a flat chain of tool calls.",
      "Adds recovery edges that preserve successful partial work.",
      "Surfaces execution traces that are easy to inspect in dashboards.",
    ],
    limitations: [
      "Benchmarks center on synthetic agent tasks instead of real publication pipelines.",
      "Requires strong task typing to get the best recovery behavior.",
    ],
    applications: [
      "Agentic content pipelines",
      "Research workflow recovery",
      "Execution trace visualization",
    ],
    confidenceScore: 0.88,
    updatedAt: "2026-04-25T11:40:00Z",
  },
  {
    insightId: 503,
    paperId: 103,
    summaryShort: "Replay compression preserves semantically useful events in first-person video while cutting storage and retrieval costs.",
    summaryLong:
      "Rather than storing uniform replay windows, the method compresses segments according to semantic salience and retrieval value. This makes it relevant to any product that needs fast post-hoc analysis of large event streams without keeping every frame at equal fidelity.",
    noveltyPoints: [
      "Optimizes replay buffers directly for retrieval quality.",
      "Uses event salience to vary compression strength.",
      "Retains more failure evidence than naive keyframe schemes.",
    ],
    limitations: [
      "Compression gains depend on a well-tuned salience model.",
      "The method does not address privacy filtering.",
    ],
    applications: [
      "Egocentric video indexing",
      "Operations incident review",
      "Storage-aware ML pipelines",
    ],
    confidenceScore: 0.85,
    updatedAt: "2026-04-22T12:10:00Z",
  },
  {
    insightId: 504,
    paperId: 106,
    summaryShort: "Robot vision indexes make failure triage fast by grouping errors around retrieval anchors and operational drift signatures.",
    summaryLong:
      "The proposed indexing scheme emphasizes the operational use case over benchmark retrieval score alone. Teams can jump from a drift alert to visually similar failure clusters, then inspect which sensors, labels, or deployment contexts produced the pattern.",
    noveltyPoints: [
      "Treats failure analysis as the primary retrieval target.",
      "Includes drift tags that persist across deployment revisions.",
      "Improves operator time-to-diagnosis in the authors' study.",
    ],
    limitations: [
      "Requires curated retrieval anchors before the index becomes effective.",
      "The paper does not benchmark multilingual label workflows.",
    ],
    applications: [
      "Autonomy operations consoles",
      "Model regression review",
      "Deployment drift audits",
    ],
    confidenceScore: 0.9,
    updatedAt: "2026-04-26T08:05:00Z",
  },
];

export const notifications: NotificationItem[] = [
  {
    notificationId: 801,
    destination: "feishu",
    paperId: 101,
    success: true,
    errorMessage: null,
    sentAt: "2026-04-26T06:10:00Z",
  },
  {
    notificationId: 802,
    destination: "feishu",
    paperId: 102,
    success: false,
    errorMessage: "Webhook timeout after 5s during morning send window.",
    sentAt: "2026-04-25T08:05:00Z",
  },
  {
    notificationId: 803,
    destination: "feishu",
    paperId: 103,
    success: true,
    errorMessage: null,
    sentAt: "2026-04-23T07:35:00Z",
  },
  {
    notificationId: 804,
    destination: "feishu",
    paperId: 106,
    success: false,
    errorMessage: "Bot secret signature mismatch on first retry attempt.",
    sentAt: "2026-04-26T09:20:00Z",
  },
];

export const editorialDrafts: EditorialDraftItem[] = [
  {
    draftId: "101-bilibili",
    paperId: 101,
    platform: "bilibili",
    title: "稀疏场先验如何让 3D 开放词汇理解更稳",
    hook: "更少提示词，依然能把三维场景讲清楚。",
    status: "exported",
    assignee: "Lina Zhou",
    updatedAt: "2026-04-26T06:40:00Z",
    outputPath: "outputs/editorial/2026-04-26/bilibili-sparse-field-priors.md",
  },
  {
    draftId: "101-xiaohongshu",
    paperId: 101,
    platform: "xiaohongshu",
    title: "三维理解也能做成高信息密度速读卡",
    hook: "研究结论和应用场景可以在一张卡里讲透。",
    status: "approved",
    assignee: "Mia Sun",
    updatedAt: "2026-04-26T06:55:00Z",
    outputPath: "outputs/editorial/2026-04-26/xiaohongshu-sparse-field-priors.md",
  },
  {
    draftId: "101-douyin",
    paperId: 101,
    platform: "douyin",
    title: "三维开放词汇理解的新套路",
    hook: "从提示词成本开始优化，结果不只是更省。",
    status: "in_review",
    assignee: "Qiang Wu",
    updatedAt: "2026-04-26T07:10:00Z",
    outputPath: "outputs/editorial/2026-04-26/douyin-sparse-field-priors.md",
  },
  {
    draftId: "102-bilibili",
    paperId: 102,
    platform: "bilibili",
    title: "长链路研究 Agent 为什么总掉线",
    hook: "这篇文章把恢复路径变成了图结构。",
    status: "generated",
    assignee: null,
    updatedAt: "2026-04-25T12:00:00Z",
    outputPath: "outputs/editorial/2026-04-25/bilibili-graph-executors.md",
  },
  {
    draftId: "103-xiaohongshu",
    paperId: 103,
    platform: "xiaohongshu",
    title: "第一视角视频压缩，重点不是省空间而是保留故障线索",
    hook: "对运营排障来说，可检索性比平均画质更重要。",
    status: "rejected",
    assignee: "Jo Yu",
    updatedAt: "2026-04-23T08:10:00Z",
    outputPath: "outputs/editorial/2026-04-23/xiaohongshu-replay-compression.md",
  },
  {
    draftId: "106-douyin",
    paperId: 106,
    platform: "douyin",
    title: "机器人视觉故障排查终于有索引了",
    hook: "不是再看一遍日志，而是直接跳到相似故障簇。",
    status: "approved",
    assignee: "Kai Li",
    updatedAt: "2026-04-26T09:45:00Z",
    outputPath: "outputs/editorial/2026-04-26/douyin-robot-vision-index.md",
  },
];

export const editorialDraftContent: Record<string, string> = {
  "101-bilibili": `# 稀疏场先验如何让 3D 开放词汇理解更稳

## 一句话结论
更少的提示词，不代表信息更少；这篇工作把三维场景重建和语义标注拆开做，结果是成本更低、结构更稳。

## 值得讲给读者的三个点
- 先恢复几何，再挂接语义标签，三维场景不会因为提示词不够密而崩掉。
- 提示词预算下降后，开放词汇 3D 理解更适合做成持续更新的运营栏目。
- 对机器人和 3D 数据集排障团队来说，后续检索会更快。

## 视频结构建议
1. 用“提示词越来越贵，三维理解为什么还要继续做”开场。
2. 中段讲清“稀疏先验”到底减少了什么工作量。
3. 结尾落到真实场景：机器人地图巡检、三维数据集复盘、跨团队知识同步。
`,
  "101-xiaohongshu": `# 三维理解也能做成高信息密度速读卡

## 结论
这篇文章适合做“研究速读卡”，重点不是算法公式，而是它如何降低三维开放词汇理解的提示成本。

- 研究对象：开放词汇 3D 场景理解
- 关键改动：稀疏场先验先行
- 业务意义：更省提示词、更稳结构恢复、更适合做持续型内容栏目

> 适合搭配一张“传统流程 vs 稀疏先验流程”的对比图。
`,
  "101-douyin": `# 三维开放词汇理解的新套路

更少提示词，为什么结果反而更稳？

- 先讲场景结构，不急着一开始就把每个对象都命名。
- 稀疏先验让系统先把“骨架”搭好，再做语义贴标签。
- 这让运营和研究团队都更容易复盘为什么模型会误判。

结尾要把“节省提示词成本”和“提高复盘效率”这两个收益再强调一次。
`,
  "102-bilibili": `# 长链路研究 Agent 为什么总掉线

## 开场问题
研究型 Agent 不是不会思考，而是很难在多阶段任务里保持状态一致。

## 这篇论文给出的答案
- 把任务拆成图，而不是一条线
- 每个节点单独恢复，不必全量重跑
- 失败路径也变成可观察的系统事件

## 可运营化角度
这类工作最适合做成“系统设计拆解”内容，而不是泛泛谈 Agent 会不会更聪明。
`,
  "103-xiaohongshu": `# 第一视角视频压缩，重点不是省空间而是保留故障线索

## 为什么值得关注
很多视频压缩方法只看平均质量，但运营排障更关心关键故障画面有没有被保留下来。

- 这篇工作把“可检索的故障线索”放在压缩目标里
- 适合讲存储成本和排障效率的权衡
- 但当前文案不要过度延伸到隐私结论
`,
  "106-douyin": `# 机器人视觉故障排查终于有索引了

开头直接问：出问题的时候，你是翻日志，还是先找到相似故障？

## 三个看点
- 论文把故障分析当成检索目标，而不是顺手能力
- 相似故障簇可以直接拉出排查路径
- 对机器人运营团队来说，这比单纯提分更有价值

## 短视频节奏
1. 先给痛点
2. 再讲“故障索引”这个新抓手
3. 最后落到运维和回归测试场景
`,
};

export const editorialDraftReviewNotes: Record<string, string | null> = {
  "101-bilibili": "Export pack signed off for Bilibili scheduling.",
  "101-xiaohongshu": "Approved after tightening the CTA and reducing repetition in the middle section.",
  "101-douyin": "Need a sharper first three seconds before this can move to approval.",
  "102-bilibili": null,
  "103-xiaohongshu": "Claims overstate privacy implications. Rework the positioning before another review pass.",
  "106-douyin": "Approved after shortening the opening beat and clarifying the operator use case.",
};

export const exportRecords: ExportRecordItem[] = [
  {
    exportId: 901,
    draftId: "106-douyin",
    exportedBy: "ops-bot",
    success: false,
    sourcePath: "outputs/editorial/2026-04-26/douyin-robot-vision-index.md",
    destinationPath: null,
    errorMessage: "First export attempt happened before approval was recorded in the workflow state.",
    createdAt: "2026-04-26T10:05:00Z",
  },
  {
    exportId: 900,
    draftId: "101-bilibili",
    exportedBy: "lina.zhou",
    success: true,
    sourcePath: "outputs/editorial/2026-04-26/bilibili-sparse-field-priors.md",
    destinationPath: "outputs/exported/2026-04-26/bilibili-sparse-field-priors.md",
    errorMessage: null,
    createdAt: "2026-04-26T08:20:00Z",
  },
  {
    exportId: 899,
    draftId: "103-xiaohongshu",
    exportedBy: "ops-bot",
    success: false,
    sourcePath: "outputs/editorial/2026-04-23/xiaohongshu-replay-compression.md",
    destinationPath: null,
    errorMessage: "Draft must return to in-review before it can be exported again.",
    createdAt: "2026-04-23T08:30:00Z",
  },
];

export const sourceHealth: SourceHealthItem[] = [
  {
    source: "arxiv",
    enabled: true,
    status: "healthy",
    lastRunAt: "2026-04-26T06:00:00Z",
    fetchedCount: 42,
    newCount: 11,
    notes: "Daily ingest is stable and insight generation kept pace with discovery volume.",
  },
  {
    source: "openreview",
    enabled: true,
    status: "attention",
    lastRunAt: "2026-04-25T08:00:00Z",
    fetchedCount: 18,
    newCount: 4,
    notes: "Submission metadata is present, but one notification retry batch is still pending review.",
  },
  {
    source: "cvf",
    enabled: true,
    status: "degraded",
    lastRunAt: "2026-04-26T09:00:00Z",
    fetchedCount: 27,
    newCount: 7,
    notes: "Discovery is current, though one export-ready draft still lacks a successful notification send.",
  },
];

export const pipelineStages: PipelineStageItem[] = [
  {
    stageId: "fetch",
    name: "Fetch",
    status: "live",
    summary: "Source crawlers pull from arXiv, OpenReview, and CVF using source-specific adapters.",
    implementedIn: ["app/sources/arxiv.py", "app/sources/openreview.py", "app/sources/cvf.py"],
    evidence: "Crawl adapters already exist and run through the Python ingestion pipeline.",
  },
  {
    stageId: "normalize",
    name: "Normalize",
    status: "live",
    summary: "Raw payloads are normalized into a shared paper model before storage and downstream enrichment.",
    implementedIn: ["app/normalizer.py", "app/models.py"],
    evidence: "Normalized metadata is persisted to the shared SQLAlchemy models.",
  },
  {
    stageId: "store",
    name: "Store",
    status: "live",
    summary: "Papers, versions, insights, and notifications are stored in SQLite-backed SQLAlchemy tables.",
    implementedIn: ["app/storage.py", "app/models.py"],
    evidence: "Persistent entities back the existing CLI workflows.",
  },
  {
    stageId: "insight",
    name: "Insight",
    status: "live",
    summary: "Summaries, novelty points, limitations, and applications are generated and attached to papers.",
    implementedIn: ["app/summarization/service.py", "app/models.py"],
    evidence: "PaperInsight already captures the frontend detail-page content shape.",
  },
  {
    stageId: "editorial",
    name: "Editorial",
    status: "live",
    summary: "Platform-specific markdown drafts are composed for Bilibili, Xiaohongshu, and Douyin.",
    implementedIn: ["app/editorial/pipeline.py", "app/editorial/composer.py"],
    evidence: "Draft generation writes per-platform markdown files to the outputs directory.",
  },
  {
    stageId: "export",
    name: "Export",
    status: "partial",
    summary: "Reviewed markdown can be exported, but approval workflow and richer destination tracking are future extension points.",
    implementedIn: ["app/publish/exporter.py", "scripts/export_for_publish.py"],
    evidence: "Current export copies reviewed markdown without frontend-level approvals or audit UI.",
  },
];
