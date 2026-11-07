"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

import { TOOLS } from "@/lib/constants";
import { getCatalogGroups } from "@/lib/tool-catalog";

export function ToolSwitcher() {
  const pathname = usePathname();
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const summaryRef = useRef<HTMLElement>(null);
  const groups = getCatalogGroups(TOOLS);

  useEffect(() => {
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !detailsRef.current?.contains(event.target) && detailsRef.current) {
        detailsRef.current.open = false;
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);

  useEffect(() => {
    if (detailsRef.current) detailsRef.current.open = false;
  }, [pathname]);

  return (
    <details
      className="tool-switcher"
      ref={detailsRef}
      onBlur={(event) => {
        if (event.relatedTarget instanceof Node && !event.currentTarget.contains(event.relatedTarget)) {
          event.currentTarget.open = false;
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && detailsRef.current?.open) {
          event.preventDefault();
          detailsRef.current.open = false;
          summaryRef.current?.focus();
        }
      }}
    >
      <summary ref={summaryRef}>All tools <span aria-hidden="true">⌄</span></summary>
      <nav className="tool-switcher-panel" aria-label="Switch tool">
        <Link className="tool-switcher-catalog" href="/">Browse all tools <span aria-hidden="true">↗</span></Link>
        {groups.map((group) => (
          <section key={group.id}>
            <h2>{group.label}</h2>
            <ul>
              {group.tools.map((tool) => (
                <li key={tool.id}><Link aria-current={pathname === tool.route ? "page" : undefined} href={tool.route}>{tool.title}</Link></li>
              ))}
            </ul>
          </section>
        ))}
      </nav>
    </details>
  );
}
