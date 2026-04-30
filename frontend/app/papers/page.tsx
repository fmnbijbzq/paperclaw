import { Suspense } from "react";

import { EmptyState } from "@/components/empty-state";
import { PaperSearchForm } from "@/components/paper-search-form";
import { PaperList } from "@/components/paper-list";
import { SectionCard } from "@/components/section-card";
import { searchPapers } from "@/lib/queries";
import type { PaperSource } from "@/lib/types";

interface PapersPageProps {
  searchParams: Promise<{
    q?: string;
    source?: string;
    page?: string;
  }>;
}

const validSources: PaperSource[] = ["arxiv", "openreview", "cvf"];

export default async function PapersPage({ searchParams }: PapersPageProps) {
  const { q: rawQuery, source: rawSource, page: rawPage } = await searchParams;

  const query = rawQuery ?? "";
  const source: PaperSource | "all" = rawSource && validSources.includes(rawSource as PaperSource) ? (rawSource as PaperSource) : "all";
  const page = rawPage ? Math.max(1, Number.parseInt(rawPage, 10) || 1) : 1;

  const result = await searchPapers({
    q: query || undefined,
    source: source !== "all" ? source : undefined,
    page,
    pageSize: 20,
  });

  const { records, total, totalPages } = result;

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">论文库存</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">跨爬虫研究收录</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          搜索并浏览来自 arXiv、OpenReview 和 CVF 的论文。使用搜索框和来源筛选器查找特定论文。
        </p>

        <div className="mt-6">
          <Suspense>
            <PaperSearchForm initialQuery={query} initialSource={source} />
          </Suspense>
        </div>
      </section>

      <SectionCard
        eyebrow="论文记录"
        title={query ? `${total} 条关于 "${query}" 的结果` : `当前工作集中有 ${total} 篇论文`}
        description={
          query
            ? `正在显示第 ${page} / ${totalPages} 页。结果会匹配标题、作者、会议、分类和摘要内容。`
            : "行内容突出来源、摘要置信度、草稿数量和通知状态，适合高密度浏览。"
        }
      >
        {records.length > 0 ? (
          <>
            <PaperList records={records} />
            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-3">
                {page > 1 ? (
                  <a
                    href={`/papers?${new URLSearchParams({ ...(query && { q: query }), ...(source !== "all" && { source }), page: String(page - 1) }).toString()}`}
                    className="action-button action-button-secondary"
                  >
                    上一页
                  </a>
                ) : (
                  <span className="action-button action-button-secondary pointer-events-none opacity-40">上一页</span>
                )}
                <span className="text-sm subtle-copy">
                  第 {page} / {totalPages} 页
                </span>
                {page < totalPages ? (
                  <a
                    href={`/papers?${new URLSearchParams({ ...(query && { q: query }), ...(source !== "all" && { source }), page: String(page + 1) }).toString()}`}
                    className="action-button action-button-secondary"
                  >
                    下一页
                  </a>
                ) : (
                  <span className="action-button action-button-secondary pointer-events-none opacity-40">下一页</span>
                )}
              </div>
            )}
          </>
        ) : (
          <EmptyState
            compact
            title={query ? "没有匹配搜索条件的论文" : "暂无可用论文"}
            description={
              query
                ? `未找到关于 "${query}" 的结果。请尝试其他搜索词或调整来源筛选器。`
                : "仓库返回论文记录后，它们会连同洞察、投递和编辑上下文显示在这里。"
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
