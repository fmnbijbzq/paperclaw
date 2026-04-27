import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cx } from "@/lib/utils";

interface SectionCardProps extends ComponentPropsWithoutRef<"section"> {
  eyebrow?: string;
  title?: string;
  description?: string;
  actions?: ReactNode;
}

export function SectionCard({
  eyebrow,
  title,
  description,
  actions,
  children,
  className,
  ...props
}: SectionCardProps) {
  return (
    <section {...props} className={cx("panel-card rounded-[1.75rem] p-5 sm:p-6", className)}>
      {(eyebrow || title || description || actions) && (
        <header className="mb-5 flex flex-col gap-4 border-b border-[color:rgba(115,147,197,0.18)] pb-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
            {title ? <h2 className="section-title mt-2 text-2xl font-semibold text-white">{title}</h2> : null}
            {description ? <p className="mt-2 text-sm subtle-copy">{description}</p> : null}
          </div>
          {actions ? <div className="shrink-0">{actions}</div> : null}
        </header>
      )}
      {children}
    </section>
  );
}
