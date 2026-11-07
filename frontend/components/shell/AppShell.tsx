import type { ReactNode } from "react";

import { AppHeader } from "@/components/shell/AppHeader";
import { ProgressRail } from "@/components/shell/ProgressRail";
import { WorkspaceNavigationGuard } from "@/components/shell/WorkspaceNavigationGuard";
import type { WorkspaceNavigationState } from "@/lib/navigation-policy";
import type { ProgressStep } from "@/lib/types";

interface AppShellProps {
  readonly children: ReactNode;
  readonly currentStep?: ProgressStep;
  readonly variant?: "catalog" | "workspace";
  readonly navigationState?: WorkspaceNavigationState;
}

export function AppShell({ children, currentStep = 1, variant = "workspace", navigationState = "idle" }: AppShellProps) {
  return (
    <WorkspaceNavigationGuard state={navigationState}>
    <div className={`app-frame app-frame--${variant}`}>
      <AppHeader />
      {variant === "workspace" ? <ProgressRail currentStep={currentStep} /> : null}
      <main className="app-shell" id="main-content">
        <section className="task-canvas">{children}</section>
      </main>
      <a
        aria-label="Built by 0xdaruby — opens portfolio in a new tab"
        className="creator-credit"
        href="https://oxdaruby.tech"
        referrerPolicy="no-referrer"
        rel="noopener noreferrer"
        target="_blank"
      >
        Built by 0xdaruby
      </a>
    </div>
    </WorkspaceNavigationGuard>
  );
}
