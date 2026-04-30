import { LoadingPanel } from "@/components/loading-panel";

export default function PaperDetailLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="论文详情"
        title="正在读取论文上下文和洞察状态"
        description="正在解析指定论文、通知历史和编辑草稿。"
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="洞察摘要"
        title="正在准备分析面板"
        description="正在加载短摘要、长摘要、创新点、局限和应用方向。"
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="下游活动"
        title="正在收集通知和编辑历史"
        description="正在合并近期通知尝试和平台草稿。"
        cardCount={2}
      />
    </div>
  );
}
