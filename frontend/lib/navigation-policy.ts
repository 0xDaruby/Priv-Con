export type WorkspaceNavigationState = "idle" | "draft" | "processing";

/** Only same-tab navigation that would abandon this workspace needs a decision. */
export function needsNavigationDecision(
  state: WorkspaceNavigationState,
  currentUrl: string,
  destinationUrl: string,
  opensAnotherTab = false,
): boolean {
  if (state === "idle" || opensAnotherTab) return false;
  const current = new URL(currentUrl);
  const destination = new URL(destinationUrl, current);
  if (destination.origin !== current.origin) return false;
  return destination.pathname !== current.pathname || destination.search !== current.search;
}
