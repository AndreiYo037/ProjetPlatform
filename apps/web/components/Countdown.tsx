"use client";

import { useEffect, useState } from "react";

/**
 * FR-501 — the deadline, in the participant's own timezone.
 *
 * Rendered client-side on purpose: a server-rendered countdown is wrong the
 * moment it reaches the browser, and this is the single most time-critical
 * thing on the page.
 */
export default function Countdown({
  deadline,
  timezone,
}: {
  deadline: string | null;
  timezone: string;
}) {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, []);

  if (!deadline) return null;

  const target = new Date(deadline);
  const local = target.toLocaleString(undefined, {
    timeZone: timezone,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  // Until the clock has mounted, show the date without a relative figure
  // rather than a figure that flashes and corrects itself.
  let remaining: string | null = null;
  let urgent = false;
  if (now !== null) {
    const ms = target.getTime() - now;
    if (ms <= 0) {
      remaining = "Deadline passed";
      urgent = true;
    } else {
      const hours = Math.floor(ms / 3_600_000);
      const days = Math.floor(hours / 24);
      remaining =
        days >= 2
          ? `${days} days left`
          : hours >= 1
            ? `${hours} hour${hours === 1 ? "" : "s"} left`
            : `${Math.max(1, Math.floor(ms / 60_000))} minutes left`;
      urgent = hours < 24;
    }
  }

  return (
    <div className="panel" style={{ marginBottom: "1.25rem" }}>
      <div className="small muted">Submission due</div>
      <div style={{ fontSize: "1.15rem", fontWeight: 600 }}>{local}</div>
      {remaining && (
        <div className="small" style={{ color: urgent ? "var(--warn)" : "var(--muted)" }}>
          {remaining} · {timezone.replace("_", " ")}
        </div>
      )}
    </div>
  );
}
