import { LoadingPanel } from "@/components/loading-panel";

export default function DraftDetailLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="草稿详情"
        title="正在读取编辑草稿上下文"
        description="正在解析指定草稿、论文来源和导出历史。"
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="草稿内容"
        title="正在准备 Markdown 预览和审计轨迹"
        description="正在读取生成内容和活动时间线。"
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="导出历史"
        title="正在收集导出尝试"
        description="正在获取与该编辑草稿关联的导出记录。"
        cardCount={2}
      />
    </div>
  );
}
