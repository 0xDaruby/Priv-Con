"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { requestBackendHealthCheck } from "@/hooks/useBackendHealth";
import { PrivConApiError, submitConversion } from "@/lib/api";
import type {
  ConversionExtraFields,
  ConversionFailure,
  ConversionPhase,
  DownloadableConversionResult,
  ToolConfig,
} from "@/lib/types";

const CLIENT_REQUEST_TIMEOUT_MS = 70_000;

export function useConversion(config: ToolConfig) {
  const [phase, setPhase] = useState<ConversionPhase>("idle");
  const [error, setError] = useState<ConversionFailure>();
  const [result, setResult] = useState<DownloadableConversionResult>();
  const abortControllerRef = useRef<AbortController | undefined>(undefined);
  const resultUrlRef = useRef<string | undefined>(undefined);

  const revokeResultUrl = useCallback(() => {
    if (resultUrlRef.current) {
      URL.revokeObjectURL(resultUrlRef.current);
      resultUrlRef.current = undefined;
    }
  }, []);

  const convert = useCallback(
    async (files: readonly File[], extraFields: ConversionExtraFields = {}) => {
      revokeResultUrl();
      setResult(undefined);
      setError(undefined);
      setPhase("processing");

      const controller = new AbortController();
      abortControllerRef.current = controller;
      let timedOut = false;
      const timeoutId = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, CLIENT_REQUEST_TIMEOUT_MS);

      try {
        const conversion = await submitConversion(
          config,
          files,
          extraFields,
          controller.signal,
        );
        const url = URL.createObjectURL(conversion.blob);
        resultUrlRef.current = url;
        setResult({ ...conversion, url });
        setPhase("success");
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          if (timedOut) {
            setError({
              code: "conversion_timeout",
              message:
                "This conversion took too long and was stopped. Try a smaller or simpler file.",
            });
            setPhase("error");
            requestBackendHealthCheck();
          } else {
            setPhase("ready");
          }
          return;
        }

        const failure = caught instanceof PrivConApiError
          ? { code: caught.code, message: caught.message }
          : {
              code: "internal_error",
              message: "An unexpected error occurred. Please try again.",
            };
        setError(failure);
        setPhase("error");
        requestBackendHealthCheck();
      } finally {
        window.clearTimeout(timeoutId);
        abortControllerRef.current = undefined;
      }
    },
    [config, revokeResultUrl],
  );

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const retry = useCallback(() => {
    setError(undefined);
    setPhase("ready");
  }, []);

  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    revokeResultUrl();
    setResult(undefined);
    setError(undefined);
    setPhase("idle");
  }, [revokeResultUrl]);

  useEffect(() => () => {
    abortControllerRef.current?.abort();
    revokeResultUrl();
  }, [revokeResultUrl]);

  return { cancel, convert, error, phase, reset, result, retry } as const;
}
