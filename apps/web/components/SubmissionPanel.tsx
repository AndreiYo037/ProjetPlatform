"use client";

import { useEffect, useState } from "react";
import {
  assetUrl,
  deleteSubmissionSlot,
  putSubmissionLink,
  submitSubmission,
  uploadSubmissionFile,
  type SubmissionOut,
} from "@/lib/api";
import { formatSlot } from "@/lib/dates";
import { autosaveLabel, useAutosave } from "@/lib/useAutosave";

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
  programmeId,
  onChange,
}: {
  submission: SubmissionOut | null;
  programmeId?: string;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
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

  async function upload(slot: string, file: File) {
    setBusy(slot);
    setError(null);
    setJustSubmitted(false);
    try {
      await uploadSubmissionFile(slot, file, programmeId);
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
      await deleteSubmissionSlot(slot, programmeId);
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
      const result = await submitSubmission(programmeId);
      if (result.submitted_at) {
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
  const handedIn = Boolean(submission.submitted_at);

  return (
    <>
      <div className="row" style={{ marginBottom: "0.75rem" }}>
        <span className={`tag ${handedIn || complete ? "open" : "closed"}`}>
          {submission.locked
            ? "Locked"
            : handedIn
              ? "Submitted"
              : complete
                ? "Ready to submit"
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
                <SlotLinkInput
                  slot={slot.slot}
                  initialUrl={slot.drive_url ?? ""}
                  locked={Boolean(submission.locked)}
                  programmeId={programmeId}
                  onSaved={onChange}
                  onError={setError}
                />
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
              Fill every slot — a link, or a file you have uploaded — then
              submit. That is what opens a pitch timeslot.
            </p>
          )}
          {complete && !handedIn && (
            <p className="small muted" style={{ marginTop: 0 }}>
              Submit to hand this in. Then you can pick a pitch timeslot.
            </p>
          )}
          {submitError && <div className="notice bad">{submitError}</div>}
          {justSubmitted && submission.submitted_at && (
            <div className="notice good">
              Submitted {formatSubmittedAt(submission.submitted_at)}. Pick a
              pitch timeslot under How you&apos;re judged. You can keep making
              changes and submit again any time before the deadline.
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
  return formatSlot(value) ?? value;
}

function SlotLinkInput({
  slot,
  initialUrl,
  locked,
  programmeId,
  onSaved,
  onError,
}: {
  slot: string;
  initialUrl: string;
  locked: boolean;
  programmeId?: string;
  onSaved: () => void;
  onError: (message: string | null) => void;
}) {
  const [url, setUrl] = useState(initialUrl);
  const [baseline, setBaseline] = useState(initialUrl);

  useEffect(() => {
    setUrl(initialUrl);
    setBaseline(initialUrl);
  }, [initialUrl]);

  const { status, error } = useAutosave(
    url.trim(),
    baseline.trim(),
    async (next) => {
      if (!next) return;
      onError(null);
      await putSubmissionLink(slot, next, programmeId);
      setBaseline(next);
      onSaved();
    },
    800,
  );

  useEffect(() => {
    if (error) onError(error);
  }, [error, onError]);

  return (
    <div>
      <input
        id={`slot-${slot}`}
        type="url"
        placeholder="Paste a link"
        value={url}
        disabled={locked}
        onChange={(e) => setUrl(e.target.value)}
        style={{ flex: "1 1 18rem", width: "100%" }}
      />
      {!locked && (
        <div className="small muted" style={{ marginTop: "0.35rem" }}>
          {autosaveLabel(status) ?? "Saves when you pause typing"}
        </div>
      )}
    </div>
  );
}
