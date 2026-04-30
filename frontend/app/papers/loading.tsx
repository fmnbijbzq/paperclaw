import { LoadingPanel } from "@/components/loading-panel";

export default function PapersLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="论文库存"
        title="正在读取当前论文集"
        description="正在获取论文记录和洞察摘要。"
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="论文记录"
        title="正在准备浏览表格"
        description="正在合并通知状态和编辑产物数量。"
        cardCount={3}
      />
    </div>
  );
}
