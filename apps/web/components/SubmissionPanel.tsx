"use client";

import { useState } from "react";
import { putSubmissionLink, recheckSubmission, type SubmissionOut } from "@/lib/api";

const SLOT_LABELS: Record<string, string> = {
  artifact: "Your artifact",
  memo: "Your memo",
  extra: "Anything extra",
};

const SLOT_HINTS: Record<string, string> = {
  artifact: "The main thing you built.",
  memo: "Half a page: the problem, your approach, your recommendation, what you'd do next.",
  extra: "Optional.",
};

export default function SubmissionPanel({
  submission,
  onChange,
}: {
  submission: SubmissionOut | null;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  if (!submission) {
    return (
      <p className="muted small">
        Your submission slots are still being set up. Nothing is needed from you yet.
      </p>
    );
  }

  async function save(slot: string) {
    const url = drafts[slot];
    if (!url) return;
    setBusy(slot);
    setError(null);
    try {
      await putSubmissionLink(slot, url);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that link.");
    } finally {
      setBusy(null);
    }
  }

  const complete = submission.status === "complete";

  return (
    <>
      <div className="row" style={{ marginBottom: "0.75rem" }}>
        <span className={`tag ${complete ? "open" : "closed"}`}>
          {submission.locked
            ? "Locked"
            : complete
              ? "Complete"
              : submission.slots.some((s) => s.drive_url)
                ? "In progress"
                : "Not started"}
        </span>
        {!submission.locked && (
          <button
            className="secondary small"
            onClick={async () => {
              setBusy("recheck");
              await recheckSubmission().catch(() => undefined);
              setBusy(null);
              onChange();
            }}
            disabled={busy !== null}
          >
            {busy === "recheck" ? "Checking…" : "Check my links again"}
          </button>
        )}
      </div>

      {submission.locked && (
        <div className="notice">
          The deadline has passed. What was here at the deadline is what gets judged — a
          frozen copy was taken, so later edits to your document do not change it.
        </div>
      )}

      {error && <div className="notice bad">{error}</div>}

      {submission.slots.map((slot) => {
        const failed = slot.drive_url && slot.access_status !== "ok";
        return (
          <div className="card" key={slot.slot}>
            <label htmlFor={`slot-${slot.slot}`}>{SLOT_LABELS[slot.slot] ?? slot.slot}</label>
            <div className="small muted" style={{ marginBottom: "0.5rem" }}>
              {SLOT_HINTS[slot.slot] ?? ""}
            </div>
            <div className="row">
              <input
                id={`slot-${slot.slot}`}
                type="url"
                placeholder="Paste your Google Drive link"
                defaultValue={slot.drive_url ?? ""}
                disabled={submission.locked}
                onChange={(e) => setDrafts((d) => ({ ...d, [slot.slot]: e.target.value }))}
                style={{ flex: "1 1 18rem" }}
              />
              {!submission.locked && (
                <button onClick={() => save(slot.slot)} disabled={busy === slot.slot}>
                  {busy === slot.slot ? "Checking…" : "Save"}
                </button>
              )}
            </div>
            {slot.access_status === "ok" && slot.filename && (
              <div className="small" style={{ color: "var(--ok)", marginTop: "0.4rem" }}>
                We can open this — {slot.filename}
              </div>
            )}
            {failed && (
              <div className="small" style={{ color: "var(--danger)", marginTop: "0.4rem" }}>
                {slot.access_status === "denied"
                  ? "We can't open this. Set sharing to “Anyone with the link can view”, then check again."
                  : "We can't find that file. Check the link is complete."}
              </div>
            )}
          </div>
        );
      })}
      {!complete && !submission.locked && (
        <p className="small muted">
          Your submission counts as complete once every link is one we can open.
        </p>
      )}
    </>
  );
}
