"use client";

import { useCallback, useEffect, useState } from "react";

import { checkHealth } from "@/lib/api";
import type { BackendHealthState } from "@/lib/types";

export const BACKEND_HEALTH_EVENT = "privcon:check-backend-health";

export function requestBackendHealthCheck() {
  window.dispatchEvent(new Event(BACKEND_HEALTH_EVENT));
}

export function useBackendHealth() {
  const [state, setState] = useState<BackendHealthState>("checking");

  const refresh = useCallback(async () => {
    setState("checking");
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 3_000);
    const running = await checkHealth(controller.signal);
    window.clearTimeout(timeoutId);
    setState(running ? "running" : "unavailable");
  }, []);

  useEffect(() => {
    let disposed = false;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 3_000);

    void checkHealth(controller.signal).then((running) => {
      window.clearTimeout(timeoutId);
      if (!disposed) {
        setState(running ? "running" : "unavailable");
      }
    });

    window.addEventListener(BACKEND_HEALTH_EVENT, refresh);
    return () => {
      disposed = true;
      controller.abort();
      window.clearTimeout(timeoutId);
      window.removeEventListener(BACKEND_HEALTH_EVENT, refresh);
    };
  }, [refresh]);

  return { refresh, state } as const;
}
