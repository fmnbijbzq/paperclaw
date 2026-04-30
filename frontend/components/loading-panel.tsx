import { LoaderCircle } from "lucide-react";

import { cx } from "@/lib/utils";

interface LoadingPanelProps {
  eyebrow: string;
  title: string;
  description: string;
  cardCount?: number;
  className?: string;
}

const skeletonWidths = ["w-full", "w-11/12", "w-8/12"];

export function LoadingPanel({
  eyebrow,
  title,
  description,
  cardCount = 2,
  className,
}: LoadingPanelProps) {
  return (
    <section aria-busy="true" aria-live="polite" className={cx("panel-card rounded-[1.75rem] p-5 sm:p-6", className)}>
      <div className="flex flex-col gap-4 border-b border-[color:rgba(115,147,197,0.18)] pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="eyebrow">{eyebrow}</p>
          <h2 className="section-title mt-2 text-2xl font-semibold text-white">{title}</h2>
          <p className="mt-2 text-sm subtle-copy">{description}</p>
        </div>
        <div className="inline-flex items-center gap-2 self-start rounded-full border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.12)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
          加载中
        </div>
      </div>

      <div
        className={cx(
          "mt-5 grid gap-4",
          cardCount >= 3 ? "xl:grid-cols-3" : "",
          cardCount === 4 ? "md:grid-cols-2 xl:grid-cols-4" : "",
          cardCount === 2 ? "xl:grid-cols-2" : "",
        )}
      >
        {Array.from({ length: cardCount }, (_, index) => (
          <article
            key={`${title}-${index}`}
            className="rounded-[1.5rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.52)] p-4"
          >
            <div className="loading-shimmer h-3 w-24 rounded-full bg-[rgba(96,165,250,0.12)]" />
            <div className="mt-4 space-y-3">
              {skeletonWidths.map((widthClass) => (
                <div
                  key={`${title}-${index}-${widthClass}`}
                  className={cx("loading-shimmer h-3 rounded-full bg-[rgba(148,163,184,0.14)]", widthClass)}
                />
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
