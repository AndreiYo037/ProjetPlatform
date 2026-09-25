"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { closeProgramme, listSubmissionCards, type SubmissionCard } from "@/lib/api";
import { formatSlot, formatSlotTime } from "@/lib/dates";

function byTimeslot(cards: SubmissionCard[]): SubmissionCard[] {
  return [...cards].sort((a, b) => {
    if (a.pitch_at && b.pitch_at) return a.pitch_at.localeCompare(b.pitch_at);
    if (a.pitch_at) return -1;
    if (b.pitch_at) return 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
}

/**
 * The cohort as a stack of submission cards, in pitch order.
 *
 * Lives on the challenge page under Judging. Opening a name still goes to that
 * person's scoring card — that page needs the room.
 */
export default function JudgingPanel({
  programmeId,
  issued = false,
  meetLink = null,
  onIssued,
}: {
  programmeId: string;
  issued?: boolean;
  meetLink?: string | null;
  onIssued?: () => void;
}) {
  const [cards, setCards] = useState<SubmissionCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);
  const [confirmStep, setConfirmStep] = useState<0 | 1 | 2>(0);
  const [closed, setClosed] = useState<string | null>(null);
  const [issuedNow, setIssuedNow] = useState(false);

  const alreadyIssued = issued || issuedNow;

  const load = useCallback(async () => {
    try {
      setCards(await listSubmissionCards(programmeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the cohort.");
    }
  }, [programmeId]);

  useEffect(() => {
    load();
  }, [load]);

  const shown = useMemo(() => (cards ? byTimeslot(cards) : []), [cards]);

  async function close() {
    if (alreadyIssued) return;
    if (confirmStep === 0) {
      setConfirmStep(1);
      setError(null);
      return;
    }
    if (confirmStep === 1) {
      setConfirmStep(2);
      return;
    }
    setClosing(true);
    setError(null);
    try {
      const result = await closeProgramme(programmeId);
      setClosed(
        `${result.credentials_issued} credential${
          result.credentials_issued === 1 ? "" : "s"
        } issued, ${result.skills_promoted} skill${
          result.skills_promoted === 1 ? "" : "s"
        } on profiles.` +
          (result.unscored > 0
            ? ` ${result.unscored} not scored, so nothing was issued for them.`
            : ""),
      );
      setIssuedNow(true);
      setConfirmStep(0);
      onIssued?.();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not close the programme.");
    } finally {
      setClosing(false);
    }
  }

  if (error && !cards) return <div className="notice bad">{error}</div>;
  if (!cards) return <p className="muted">Loading…</p>;

  const scored = cards.filter((card) => card.your_total !== null).length;
  const unscored = cards.length - scored;
  const room = meetLink ?? cards.find((card) => card.meet_link)?.meet_link ?? null;

  if (cards.length === 0) {
    return (
      <p className="muted small">
        Nobody to judge yet. Cards appear once participants have seats.
      </p>
    );
  }

  return (
    <>
      <p className="small muted">
        {scored} of {cards.length} scored. Score a candidate to watch the
        pitch against the rubric; it saves as you go.
      </p>
      {room && (
        <p className="small" style={{ margin: "0 0 1rem" }}>
          One room for the whole cohort.{" "}
          <a href={room} target="_blank" rel="noreferrer">
            {room}
          </a>
        </p>
      )}
      {error && <div className="notice bad">{error}</div>}
      {closed && <div className="notice good">{closed}</div>}
      {shown.map((card) => (
        <div className="card" key={card.participant_id}>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <strong>
                {card.pitch_at
                  ? `${formatSlotTime(card.pitch_at)} · `
                  : card.run_order !== null
                    ? `${card.run_order}. `
                    : ""}
                {card.name}
              </strong>
              <div className="small muted">
                {card.pitch_at ? `${formatSlot(card.pitch_at)} · ` : ""}
                {card.organisation ?? "—"} · {card.links.length} file
                {card.links.length === 1 ? "" : "s"}
              </div>
            </div>
            <div className="row" style={{ gap: "0.5rem", alignItems: "center" }}>
              {!card.complete && <span className="tag">incomplete</span>}
              {card.locked && <span className="tag">locked</span>}
              <span className={`tag ${card.your_total !== null ? "open" : ""}`}>
                {card.your_total !== null
                  ? `${card.your_total}/${card.max_total}`
                  : "not scored"}
              </span>
            </div>
          </div>
          <div className="row" style={{ justifyContent: "flex-end", marginTop: "0.75rem" }}>
            <Link
              className="btn"
              href={`/company/challenges/${programmeId}/judging/${card.participant_id}`}
            >
              Score candidate
            </Link>
          </div>
        </div>
      ))}
      <div className="panel" style={{ marginTop: "1.5rem" }}>
        <strong>Close and issue</strong>
        {alreadyIssued ? (
          <p className="small muted" style={{ marginBottom: 0 }}>
            Issued. Candidate profiles were updated. This cannot run again.
          </p>
        ) : (
          <>
            <p className="small muted">
              Candidate profiles update only here, and only once. Skills you
              tagged become attested skills, and everyone you scored gets a
              credential someone else can verify. Nothing is issued for turning
              up.
            </p>
            {confirmStep === 1 && (
              <p className="small">
                This writes skills and credentials onto profiles for everyone
                you scored
                {unscored > 0
                  ? `, and ${unscored} unscored ${unscored === 1 ? "pitch gets" : "pitches get"} nothing`
                  : ""}
                . You cannot do this again.
              </p>
            )}
            {confirmStep === 2 && (
              <p className="small">
                Last check. This cannot be undone. Issue now?
              </p>
            )}
            <div className="row" style={{ gap: "0.75rem" }}>
              {confirmStep > 0 && (
                <button
                  className="secondary"
                  disabled={closing}
                  onClick={() => setConfirmStep(0)}
                >
                  Cancel
                </button>
              )}
              <button disabled={closing || scored === 0} onClick={close}>
                {closing
                  ? "Closing…"
                  : confirmStep === 0
                    ? "Close and issue"
                    : confirmStep === 1
                      ? "Continue"
                      : "Yes, close and issue"}
              </button>
            </div>
            {scored === 0 && confirmStep === 0 && (
              <p className="small muted" style={{ marginBottom: 0 }}>
                Score at least one pitch first.
              </p>
            )}
          </>
        )}
      </div>
    </>
  );
}
