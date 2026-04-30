import { LoadingPanel } from "@/components/loading-panel";

export default function NotificationsLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="通知健康"
        title="正在读取通知可靠性指标"
        description="正在汇总成功发送、需要重试的失败和最新发送时间。"
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="通知日志"
        title="正在收集近期通知尝试"
        description="正在合并论文元数据和通知结果。"
        cardCount={3}
      />
    </div>
  );
}
