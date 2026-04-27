import type { ReactNode } from "react";

import { SidebarNav } from "@/components/sidebar-nav";
import { Topbar } from "@/components/topbar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen lg:flex">
      <aside className="border-b border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.85)] lg:sticky lg:top-0 lg:h-screen lg:w-72 lg:border-b-0 lg:border-r">
        <SidebarNav />
      </aside>
      <div className="min-w-0 flex-1">
        <Topbar />
        <main id="main-content" className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
