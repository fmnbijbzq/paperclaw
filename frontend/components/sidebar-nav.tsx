"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowDownToLine, BellRing, BookOpenText, ChartColumnStacked, FilePenLine, LayoutDashboard, MoveUpRight } from "lucide-react";

import { cx } from "@/lib/utils";

const navigationItems = [
  {
    href: "/",
    label: "概览",
    description: "系统状态",
    icon: LayoutDashboard,
  },
  {
    href: "/papers",
    label: "论文",
    description: "研究收录",
    icon: BookOpenText,
  },
  {
    href: "/pipeline",
    label: "流水线",
    description: "编辑流程",
    icon: ChartColumnStacked,
  },
  {
    href: "/drafts",
    label: "草稿",
    description: "草稿管理",
    icon: FilePenLine,
  },
  {
    href: "/exports",
    label: "导出",
    description: "导出历史",
    icon: ArrowDownToLine,
  },
  {
    href: "/notifications",
    label: "通知",
    description: "飞书投递",
    icon: BellRing,
  },
] as const;

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col gap-6 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Paperclaw</p>
          <h1 className="section-title mt-2 text-2xl font-semibold text-white">研究控制台</h1>
          <p className="mt-2 max-w-xs text-sm subtle-copy">
            用于论文发现、洞察审核、编辑草稿和通知健康监控的独立协同界面。
          </p>
        </div>
        <span className="rounded-full border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.62)] p-2 text-[color:var(--accent-blue)]">
          <MoveUpRight className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>

      <nav aria-label="主导航" className="overflow-x-auto">
        <ul className="flex gap-3 lg:flex-col">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/" ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <li key={item.href} className="min-w-[12rem] lg:min-w-0">
                <Link
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={cx(
                    "panel-card panel-card-interactive flex h-full items-start gap-3 rounded-3xl px-4 py-3",
                    isActive
                      ? "border-[color:var(--border-strong)] bg-[rgba(17,31,54,0.96)]"
                      : "bg-[rgba(10,17,30,0.75)]",
                  )}
                >
                  <span
                    className={cx(
                      "mt-0.5 rounded-2xl border p-2",
                      isActive
                        ? "border-[rgba(245,158,11,0.28)] bg-[color:var(--surface-amber)] text-[color:var(--accent-amber)]"
                        : "border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.65)] text-[color:var(--accent-blue)]",
                    )}
                  >
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-white">{item.label}</span>
                    <span className="mt-1 block text-xs subtle-copy">{item.description}</span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="panel-card mt-auto rounded-3xl p-4">
        <p className="eyebrow">设计方向</p>
        <p className="mt-3 text-sm font-semibold text-white">深色运营仪表盘</p>
        <p className="mt-2 text-sm subtle-copy">
          冷蓝色数据界面、琥珀色操作强调、清晰焦点状态和高密度信息面板。
        </p>
      </div>
    </div>
  );
}
