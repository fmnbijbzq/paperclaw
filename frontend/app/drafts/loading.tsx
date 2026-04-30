import { LoadingPanel } from "@/components/loading-panel";

export default function DraftsLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="编辑工作流"
        title="正在读取草稿管理控制台"
        description="正在获取编辑草稿、状态统计和平台分布。"
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="草稿列表"
        title="正在准备草稿行"
        description="正在按更新时间排序并应用状态与平台筛选。"
        cardCount={3}
      />
    </div>
  );
}
