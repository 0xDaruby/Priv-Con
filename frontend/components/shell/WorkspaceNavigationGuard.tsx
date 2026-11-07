"use client";

import { useEffect, useId, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { needsNavigationDecision, type WorkspaceNavigationState } from "@/lib/navigation-policy";

interface WorkspaceNavigationGuardProps {
  readonly children: ReactNode;
  readonly state: WorkspaceNavigationState;
}

export function WorkspaceNavigationGuard({ children, state }: WorkspaceNavigationGuardProps) {
  const router = useRouter();
  const [destination, setDestination] = useState<string>();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const keepWorkingRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (state === "idle") return;
    const warnOnUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnOnUnload);
    return () => window.removeEventListener("beforeunload", warnOnUnload);
  }, [state]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (destination) {
      if (!dialog.open) dialog.showModal();
      keepWorkingRef.current?.focus();
    } else if (dialog.open) {
      dialog.close();
      returnFocusRef.current?.focus();
      returnFocusRef.current = null;
    }
  }, [destination]);

  const checkNavigation = (event: MouseEvent<HTMLDivElement>) => {
    if (event.defaultPrevented || event.button !== 0 || !(event.target instanceof Element)) return;
    const anchor = event.target.closest<HTMLAnchorElement>("a[href]");
    if (!anchor || anchor.hasAttribute("download")) return;
    const opensAnotherTab = event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || anchor.target === "_blank";
    if (!needsNavigationDecision(state, window.location.href, anchor.href, opensAnotherTab)) return;
    event.preventDefault();
    const url = new URL(anchor.href);
    // A disclosure link may disappear as focus moves into the dialog.
    returnFocusRef.current = anchor.closest("details")?.querySelector("summary") ?? anchor;
    setDestination(`${url.pathname}${url.search}${url.hash}`);
  };

  const leave = () => {
    if (!destination || state === "processing") return;
    const href = destination;
    returnFocusRef.current = null;
    setDestination(undefined);
    router.push(href);
  };

  return (
    <div className="workspace-navigation-boundary" onClickCapture={checkNavigation}>
      {children}
      <dialog
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="leave-workspace-dialog"
        onCancel={(event) => { event.preventDefault(); setDestination(undefined); }}
        ref={dialogRef}
      >
        <h2 id={titleId}>{state === "processing" ? "A conversion is running" : "Leave this tool?"}</h2>
        <p id={descriptionId}>
          {state === "processing"
            ? "Finish or cancel this conversion before switching tools. Return to your conversion to use its Cancel control."
            : "Your selected files and options will be cleared. The original files on your computer will not be changed."}
        </p>
        <div className="leave-workspace-actions">
          <button className="secondary-action" onClick={() => setDestination(undefined)} ref={keepWorkingRef} type="button">Keep working</button>
          {state !== "processing" ? <button className="primary-action" onClick={leave} type="button">Leave and clear selection</button> : null}
        </div>
      </dialog>
    </div>
  );
}
