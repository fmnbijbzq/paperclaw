"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BellRing, BookOpenText, ChartColumnStacked, LayoutDashboard, MoveUpRight } from "lucide-react";

import { cx } from "@/lib/utils";

const navigationItems = [
  {
    href: "/",
    label: "Overview",
    description: "System state",
    icon: LayoutDashboard,
  },
  {
    href: "/papers",
    label: "Papers",
    description: "Research intake",
    icon: BookOpenText,
  },
  {
    href: "/pipeline",
    label: "Pipeline",
    description: "Editorial flow",
    icon: ChartColumnStacked,
  },
  {
    href: "/notifications",
    label: "Notifications",
    description: "Feishu delivery",
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
          <h1 className="section-title mt-2 text-2xl font-semibold text-white">Research Console</h1>
          <p className="mt-2 max-w-xs text-sm subtle-copy">
            Standalone companion UI for paper discovery, insight review, editorial drafting, and notification health.
          </p>
        </div>
        <span className="rounded-full border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.62)] p-2 text-[color:var(--accent-blue)]">
          <MoveUpRight className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>

      <nav aria-label="Primary" className="overflow-x-auto">
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
        <p className="eyebrow">Design Direction</p>
        <p className="mt-3 text-sm font-semibold text-white">Dark operations dashboard</p>
        <p className="mt-2 text-sm subtle-copy">
          Cool blue data surfaces, amber action emphasis, visible focus treatment, and high-density information panels.
        </p>
      </div>
    </div>
  );
}
