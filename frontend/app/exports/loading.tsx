import { LoadingPanel } from "@/components/loading-panel";

export default function ExportsLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="导出流程"
        title="正在读取导出可靠性指标"
        description="正在汇总导出总数、成功次数和失败次数。"
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="导出日志"
        title="正在准备导出历史"
        description="正在关联导出记录和草稿元数据。"
        cardCount={3}
      />
    </div>
  );
}
