"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  assetUrl,
  closeProgramme,
  externalHref,
  listSubmissionCards,
  type SubmissionCard,
} from "@/lib/api";
import { formatSlot, formatSlotTime } from "@/lib/dates";
import { SHOW_SUBMISSION_MEMO } from "@/lib/features";

type View = "score" | "referral";

const REFERRAL_ORDER = ["yes", "maybe", "no", "unset"] as const;

function referralLabel(value: string | null | undefined) {
  if (value === "yes") return "Would refer";
  if (value === "maybe") return "Maybe";
  if (value === "no") return "Would not refer";
  return "Referral not set";
}

function referralKey(card: SubmissionCard): (typeof REFERRAL_ORDER)[number] {
  if (card.would_refer === "yes" || card.would_refer === "maybe" || card.would_refer === "no") {
    return card.would_refer;
  }
  return "unset";
}

function byScore(cards: SubmissionCard[]): SubmissionCard[] {
  return [...cards].sort((a, b) => {
    if (a.your_total !== null && b.your_total !== null) {
      if (b.your_total !== a.your_total) return b.your_total - a.your_total;
    } else if (a.your_total !== null) return -1;
    else if (b.your_total !== null) return 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
}

function byReferral(cards: SubmissionCard[]): { key: string; label: string; cards: SubmissionCard[] }[] {
  const groups = new Map<string, SubmissionCard[]>();
  for (const key of REFERRAL_ORDER) groups.set(key, []);
  for (const card of cards) {
    groups.get(referralKey(card))!.push(card);
  }
  return REFERRAL_ORDER.map((key) => ({
    key,
    label: referralLabel(key === "unset" ? null : key),
    cards: byScore(groups.get(key) ?? []),
  })).filter((group) => group.cards.length > 0);
}

/**
 * Cohort submissions and scores for the company — during the run and after
 * close-out. Ranked by score, or grouped by referral answer.
 */
export default function JudgingPanel({
  programmeId,
  issued = false,
  meetLink = null,
  showMeet = true,
  onIssued,
}: {
  programmeId: string;
  issued?: boolean;
  meetLink?: string | null;
  showMeet?: boolean;
  onIssued?: () => void;
}) {
  const [cards, setCards] = useState<SubmissionCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);
  const [confirmStep, setConfirmStep] = useState<0 | 1 | 2>(0);
  const [closed, setClosed] = useState<string | null>(null);
  const [issuedNow, setIssuedNow] = useState(false);
  const [view, setView] = useState<View>("score");

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

  const ranked = useMemo(() => (cards ? byScore(cards) : []), [cards]);
  const referralGroups = useMemo(() => (cards ? byReferral(cards) : []), [cards]);

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
  const room = showMeet
    ? (meetLink ?? cards.find((card) => card.meet_link)?.meet_link ?? null)
    : null;

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
        {alreadyIssued
          ? "Issued. Submissions, scores, and referral answers stay here."
          : `${scored} of ${cards.length} scored. Score a candidate; it saves as you go.`}
      </p>
      {room && !alreadyIssued && (
        <p className="small" style={{ margin: "0 0 1rem" }}>
          One room for the whole cohort.{" "}
          <a href={room} target="_blank" rel="noreferrer">
            {room}
          </a>
        </p>
      )}

      <nav className="tabs" style={{ marginBottom: "1rem" }}>
        <button
          type="button"
          className="tab"
          aria-current={view === "score" ? "page" : undefined}
          onClick={() => setView("score")}
        >
          By score
        </button>
        <button
          type="button"
          className="tab"
          aria-current={view === "referral" ? "page" : undefined}
          onClick={() => setView("referral")}
        >
          By referral
        </button>
      </nav>

      {error && <div className="notice bad">{error}</div>}
      {closed && <div className="notice good">{closed}</div>}

      {view === "score"
        ? ranked.map((card, index) => (
            <ParticipantJudgingCard
              key={card.participant_id}
              programmeId={programmeId}
              card={card}
              rank={card.your_total !== null ? index + 1 : null}
              issued={alreadyIssued}
            />
          ))
        : referralGroups.map((group) => (
            <section key={group.key} style={{ marginBottom: "1.5rem" }}>
              <h2 style={{ marginBottom: "0.75rem" }}>
                {group.label}{" "}
                <span className="small muted">({group.cards.length})</span>
              </h2>
              {group.cards.map((card) => (
                <ParticipantJudgingCard
                  key={card.participant_id}
                  programmeId={programmeId}
                  card={card}
                  issued={alreadyIssued}
                />
              ))}
            </section>
          ))}

      <div className="panel" style={{ marginTop: "1.5rem" }}>
        <strong>Close and issue</strong>
        {alreadyIssued ? (
          <p className="small muted" style={{ marginBottom: 0 }}>
            Issued. Candidate profiles were updated. This cannot run again —
            the lists above stay available.
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

function ParticipantJudgingCard({
  programmeId,
  card,
  rank = null,
  issued,
}: {
  programmeId: string;
  card: SubmissionCard;
  rank?: number | null;
  issued: boolean;
}) {
  const [showContact, setShowContact] = useState(false);
  const links = card.links.filter(
    (link) => SHOW_SUBMISSION_MEMO || link.slot !== "memo",
  );
  const summary = [
    card.organisation,
    `${links.length} file${links.length === 1 ? "" : "s"}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <strong>
            {rank !== null ? `${rank}. ` : ""}
            {card.pitch_at ? `${formatSlotTime(card.pitch_at)} · ` : ""}
            {card.name}
          </strong>
          <div className="small muted" style={{ overflowWrap: "anywhere" }}>
            {summary || "—"}
            {card.pitch_at ? ` · ${formatSlot(card.pitch_at)}` : ""}
          </div>
        </div>
        <div className="row" style={{ gap: "0.5rem", alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
          <span className="tag">{referralLabel(card.would_refer)}</span>
          {!card.complete && <span className="tag">incomplete</span>}
          {card.locked && <span className="tag">locked</span>}
          <span className={`tag ${card.your_total !== null ? "open" : ""}`}>
            {card.your_total !== null
              ? `${card.your_total}/${card.max_total}`
              : "not scored"}
          </span>
        </div>
      </div>

      {showContact && (
        <div className="panel" style={{ marginTop: "0.85rem" }}>
          <dl className="facts" style={{ margin: 0 }}>
            {card.contact_email && (
              <>
                <dt>Contact</dt>
                <dd style={{ overflowWrap: "anywhere" }}>{card.contact_email}</dd>
              </>
            )}
            {card.google_email && (
              <>
                <dt>Google</dt>
                <dd style={{ overflowWrap: "anywhere" }}>{card.google_email}</dd>
              </>
            )}
            {card.phone && (
              <>
                <dt>Phone</dt>
                <dd>{card.phone}</dd>
              </>
            )}
            {card.organisation && (
              <>
                <dt>Organisation</dt>
                <dd>{card.organisation}</dd>
              </>
            )}
            {(card.year_course || card.job_title) && (
              <>
                <dt>{card.year_course ? "Year / course" : "Job title"}</dt>
                <dd>{card.year_course || card.job_title}</dd>
              </>
            )}
            {card.linkedin_url && externalHref(card.linkedin_url) && (
              <>
                <dt>LinkedIn</dt>
                <dd>
                  <a href={externalHref(card.linkedin_url)} target="_blank" rel="noreferrer">
                    {card.linkedin_url}
                  </a>
                </dd>
              </>
            )}
          </dl>
          {!card.contact_email &&
            !card.google_email &&
            !card.phone &&
            !card.linkedin_url &&
            !card.organisation &&
            !card.year_course &&
            !card.job_title && (
              <p className="small muted" style={{ margin: 0 }}>
                No contact details on file.
              </p>
            )}
        </div>
      )}

      <div style={{ marginTop: "0.85rem" }}>
        <div className="small muted" style={{ marginBottom: "0.35rem" }}>
          Submissions
        </div>
        {links.length === 0 ? (
          <p className="small muted" style={{ margin: 0 }}>
            Nothing submitted.
          </p>
        ) : (
          <div className="panel" style={{ margin: 0 }}>
            {links.map((link) => (
              <div
                className="row"
                key={link.slot}
                style={{ justifyContent: "space-between", gap: "0.75rem" }}
              >
                <div style={{ minWidth: 0 }}>
                  <strong style={{ textTransform: "capitalize" }}>{link.slot}</strong>
                  <div className="small muted" style={{ overflowWrap: "anywhere" }}>
                    {link.filename ?? link.url ?? "Nothing submitted"}
                  </div>
                </div>
                <div className="row" style={{ gap: "0.5rem", flexShrink: 0, alignItems: "center" }}>
                  {link.access_status !== "ok" && (
                    <span className="tag">{link.access_status}</span>
                  )}
                  {link.snapshot_url && (
                    <a href={assetUrl(link.snapshot_url)} target="_blank" rel="noreferrer">
                      File
                    </a>
                  )}
                  {link.url && (
                    <a href={externalHref(link.url)} target="_blank" rel="noreferrer">
                      Link
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div
        className="row"
        style={{ justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}
      >
        <button
          type="button"
          className="secondary"
          onClick={() => setShowContact((open) => !open)}
        >
          {showContact ? "Hide contact details" : "View contact details"}
        </button>
        <Link
          className="btn"
          href={`/company/challenges/${programmeId}/judging/${card.participant_id}`}
        >
          {issued ? "View scorecard" : "Score candidate"}
        </Link>
      </div>
    </div>
  );
}
