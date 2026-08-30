import type { ReactNode } from "react";

import { AppHeader } from "@/components/shell/AppHeader";
import { ProgressRail } from "@/components/shell/ProgressRail";
import { ToolSidebar } from "@/components/shell/ToolSidebar";
import type { ProgressStep } from "@/lib/types";

interface AppShellProps {
  readonly children: ReactNode;
  readonly currentStep?: ProgressStep;
}

export function AppShell({ children, currentStep = 1 }: AppShellProps) {
  return (
    <div className="app-frame">
      <AppHeader />
      <ProgressRail currentStep={currentStep} />
      <main className="app-shell" id="main-content">
        <ToolSidebar />
        <section className="task-canvas">{children}</section>
      </main>
    </div>
  );
}
