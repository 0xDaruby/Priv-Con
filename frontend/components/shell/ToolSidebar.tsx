"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ToolFileIcon } from "@/components/icons/PrivConIcons";
import { TOOLS } from "@/lib/constants";

export function ToolSidebar() {
  const pathname = usePathname();

  return (
    <aside className="tool-sidebar" aria-label="Conversion tools">
      <ul className="tool-list">
        {TOOLS.map((tool) => {
          const isActive = pathname === tool.route;

          return (
            <li key={tool.id}>
              <Link
                aria-current={isActive ? "page" : undefined}
                className="tool-link"
                href={tool.route}
              >
                <span className="tool-icon" aria-hidden="true">
                  <ToolFileIcon name={tool.icon} />
                </span>
                <span className="tool-label">{tool.title}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
