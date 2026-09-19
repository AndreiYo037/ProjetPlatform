"use client";

import { useEffect, useRef, useState } from "react";

export type AutosaveStatus = "idle" | "pending" | "saving" | "saved" | "error";

/**
 * Debounced write of a controlled value. Skips the initial load and any value
 * that still matches the last known server baseline.
 *
 * Intentional submits (apply, publish, sign-in) stay as buttons. This is for
 * fields where forgetting Save loses work — briefs, scores, profile text.
 */
export function useAutosave<T>(
  value: T,
  baseline: T,
  save: (value: T) => Promise<void>,
  delayMs = 700,
): { status: AutosaveStatus; error: string | null } {
  const [status, setStatus] = useState<AutosaveStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const saveRef = useRef(save);
  saveRef.current = save;
  const skipFirst = useRef(true);
  const serialisedBaseline = JSON.stringify(baseline);

  useEffect(() => {
    if (skipFirst.current) {
      skipFirst.current = false;
      return;
    }
    if (JSON.stringify(value) === serialisedBaseline) {
      return;
    }

    setStatus("pending");
    setError(null);
    const handle = window.setTimeout(() => {
      setStatus("saving");
      void (async () => {
        try {
          await saveRef.current(value);
          setStatus("saved");
        } catch (err) {
          setStatus("error");
          setError(err instanceof Error ? err.message : "Could not save.");
        }
      })();
    }, delayMs);

    return () => window.clearTimeout(handle);
  }, [value, serialisedBaseline, delayMs]);

  return { status, error };
}

export function autosaveLabel(status: AutosaveStatus): string | null {
  switch (status) {
    case "pending":
      return "Saving…";
    case "saving":
      return "Saving…";
    case "saved":
      return "Saved";
    case "error":
      return null;
    default:
      return null;
  }
}
