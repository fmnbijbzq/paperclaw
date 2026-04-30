import { LoadingPanel } from "@/components/loading-panel";

export default function PipelineLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="管道地图"
        title="正在读取阶段边界"
        description="正在准备抓取、标准化、存储、洞察、编辑和导出阶段。"
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="当前阶段"
        title="正在收集证据和实现路径"
        description="正在读取每个后端阶段对应的代码位置和运行证据。"
        cardCount={3}
      />
    </div>
  );
}
