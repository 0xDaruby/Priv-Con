"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { BackendMonitorIcon } from "@/components/icons/PrivConIcons";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import type { BackendHealthState } from "@/lib/types";
import { TOOLS } from "@/lib/constants";
import { ToolSwitcher } from "@/components/shell/ToolSwitcher";
import { AnimatedThemeToggle } from "@/components/ui/animated-theme-toggle";

const STATUS_LABELS: Readonly<Record<BackendHealthState, string>> = {
  checking: "Checking",
  running: "Running",
  unavailable: "Not running",
};

export function AppHeader() {
  const pathname = usePathname();
  const currentTool = TOOLS.find((tool) => tool.route === pathname);
  const { state: backendState } = useBackendHealth();
  const statusLabel = STATUS_LABELS[backendState];

  return (
    <header className="global-header">
      <nav className="brand-navigation" aria-label="Primary navigation">
        <Link className="brand-link" href="/" aria-label="PrivCon home">
          <Image
            alt="PrivCon"
            className="brand-lockup"
            height={49}
            priority
            src="/brand/privcon-lockup.png"
            width={222}
          />
        </Link>
        <span className="header-rule" aria-hidden="true" />
        {currentTool ? <span className="header-current-tool">{currentTool.title}</span> : <span className="header-current-tool">Document tools</span>}
        <ToolSwitcher />
      </nav>

      <div className="header-utilities">
      <AnimatedThemeToggle />
      <div
        aria-label={`Local backend is ${statusLabel.toLowerCase()}`}
        className="backend-status"
        data-state={backendState}
        role="status"
      >
        <BackendMonitorIcon />
        <span className="backend-label">Local backend</span>
        <span className="status-pill">{statusLabel}</span>
      </div>
      </div>
    </header>
  );
}
