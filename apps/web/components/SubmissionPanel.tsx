"use client";

import { useState } from "react";
import {
  assetUrl,
  deleteSubmissionSlot,
  putSubmissionLink,
  recheckSubmission,
  uploadSubmissionFile,
  type SubmissionOut,
} from "@/lib/api";

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

// A memo is one static document, so it is a direct upload rather than a
// pasted link — nothing about it benefits from staying live and editable the
// way a dashboard or a deck does.
const UPLOAD_SLOTS = new Set(["memo"]);

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
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [justSubmitted, setJustSubmitted] = useState(false);

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
    setJustSubmitted(false);
    try {
      await putSubmissionLink(slot, url);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that link.");
    } finally {
      setBusy(null);
    }
  }

  async function upload(slot: string, file: File) {
    setBusy(slot);
    setError(null);
    setJustSubmitted(false);
    try {
      await uploadSubmissionFile(slot, file);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload that file.");
    } finally {
      setBusy(null);
    }
  }

  async function remove(slot: string) {
    setBusy(slot);
    setError(null);
    setJustSubmitted(false);
    try {
      await deleteSubmissionSlot(slot);
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove that file.");
    } finally {
      setBusy(null);
    }
  }

  async function submit() {
    setBusy("submit");
    setSubmitError(null);
    setJustSubmitted(false);
    try {
      // Re-checking on submit rather than trusting the last-known status
      // catches a link that was revoked minutes ago — the one failure this
      // whole area exists to prevent, and worth one more look at the moment
      // the participant is declaring themselves done.
      const result = await recheckSubmission();
      if (result.status === "complete") {
        setJustSubmitted(true);
      } else {
        setSubmitError("Something needs fixing before this can be submitted — see above.");
      }
      onChange();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not submit right now.");
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
              : submission.slots.some((s) => s.drive_url || s.file_url)
                ? "In progress"
                : "Not started"}
        </span>
      </div>

      {submission.locked && (
        <div className="notice">
          The deadline has passed. What was here at the deadline is what gets judged — a
          frozen copy was taken, so later edits to your document do not change it.
        </div>
      )}

      {error && <div className="notice bad">{error}</div>}

      {submission.slots.map((slot) => {
        const isUpload = UPLOAD_SLOTS.has(slot.slot);
        const failed = slot.drive_url && slot.access_status !== "ok";
        return (
          <div className="card" key={slot.slot}>
            <label htmlFor={`slot-${slot.slot}`}>{SLOT_LABELS[slot.slot] ?? slot.slot}</label>
            <div className="small muted" style={{ marginBottom: "0.5rem" }}>
              {SLOT_HINTS[slot.slot] ?? ""}
            </div>

            {isUpload ? (
              <>
                <div className="row">
                  <input
                    id={`slot-${slot.slot}`}
                    type="file"
                    accept="application/pdf"
                    disabled={submission.locked || busy === slot.slot}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (file) upload(slot.slot, file);
                    }}
                    style={{ flex: "1 1 18rem" }}
                  />
                  {slot.file_url && !submission.locked && (
                    <button
                      className="secondary small"
                      onClick={() => remove(slot.slot)}
                      disabled={busy === slot.slot}
                    >
                      Remove
                    </button>
                  )}
                </div>
                {busy === slot.slot && (
                  <div className="small muted" style={{ marginTop: "0.4rem" }}>
                    Uploading…
                  </div>
                )}
                {slot.file_url && (
                  <div className="small" style={{ color: "var(--ok)", marginTop: "0.4rem" }}>
                    We have this —{" "}
                    <a href={assetUrl(slot.file_url)}>{slot.filename ?? "view PDF"}</a>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="row">
                  <input
                    id={`slot-${slot.slot}`}
                    type="url"
                    placeholder="Paste a link"
                    defaultValue={slot.drive_url ?? ""}
                    disabled={submission.locked}
                    onChange={(e) => setDrafts((d) => ({ ...d, [slot.slot]: e.target.value }))}
                    style={{ flex: "1 1 18rem" }}
                  />
                  {!submission.locked && (
                    <button onClick={() => save(slot.slot)} disabled={busy === slot.slot}>
                      {busy === slot.slot ? "Saving…" : "Save"}
                    </button>
                  )}
                </div>
                {slot.access_status === "ok" && slot.drive_url && (
                  <div className="small" style={{ color: "var(--ok)", marginTop: "0.4rem" }}>
                    {slot.filename ? `We can open this — ${slot.filename}` : "Saved."}
                  </div>
                )}
                {failed && (
                  <div className="small" style={{ color: "var(--danger)", marginTop: "0.4rem" }}>
                    {slot.access_status === "denied"
                      ? "We can't open this. Set sharing to “Anyone with the link can view”, then check again."
                      : "We can't find that file. Check the link is complete."}
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
      {!submission.locked && (
        <div className="panel" style={{ marginTop: "1rem" }}>
          {!complete && (
            <p className="small muted" style={{ marginTop: 0 }}>
              Fill every slot — a link, or a file you have uploaded — to
              submit.
            </p>
          )}
          {submitError && <div className="notice bad">{submitError}</div>}
          {justSubmitted && submission.submitted_at && (
            <div className="notice good">
              Submitted {formatSubmittedAt(submission.submitted_at)}. You can keep
              making changes and submit again any time before the deadline.
            </div>
          )}
          <button onClick={submit} disabled={!complete || busy !== null}>
            {busy === "submit" ? "Submitting…" : "Submit"}
          </button>
        </div>
      )}
    </>
  );
}

function formatSubmittedAt(value: string) {
  return new Date(value).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
