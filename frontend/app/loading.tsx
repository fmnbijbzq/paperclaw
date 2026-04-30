import { LoadingPanel } from "@/components/loading-panel";

export default function AppLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="研究抓取可视性"
        title="正在启动 Paperclaw 控制台"
        description="正在读取仪表盘指标、来源健康状态和编辑库存。"
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="运行指标"
        title="正在准备概览卡片"
        description="正在汇总洞察覆盖、待重试通知和草稿库存。"
        cardCount={4}
      />
      <LoadingPanel
        eyebrow="近期发现"
        title="正在整理最新论文记录"
        description="正在关联论文元数据、洞察、通知和编辑草稿。"
        cardCount={3}
      />
    </div>
  );
}
