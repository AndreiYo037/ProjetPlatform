"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import SkillPicker from "@/components/SkillPicker";
import {
  assetUrl,
  draftTestimonial,
  externalHref,
  getScoringCard,
  getTestimonial,
  updateScoringCard,
  writeTestimonial,
  type ScoringCard,
  type TestimonialOut,
} from "@/lib/api";
import { autosaveLabel, useAutosave } from "@/lib/useAutosave";
import { formatSlot } from "@/lib/dates";
import { useActor } from "@/lib/useActor";

const REFERRAL = [
  { value: "yes", label: "Yes, I would refer them" },
  { value: "maybe", label: "Maybe" },
  { value: "no", label: "No" },
];

/**
 * One person's scoring card, with their submission kept on it.
 *
 * The work and the rubric sit on the same page because a judge is doing both
 * at once, live: nobody wants two tabs open while someone is presenting.
 *
 * Every control saves the moment it is used. There is no Save button, because
 * the failure mode is a judge who scores four pitches and closes the laptop.
 */
export default function ScoringCardPage({
  params,
}: {
  params: Promise<{ id: string; participantId: string }>;
}) {
  const { id, participantId } = use(params);
  const gate = useActor("company_user");
  const [card, setCard] = useState<ScoringCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    try {
      setCard(await getScoringCard(id, participantId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this card.");
    }
  }, [id, participantId, gate.status]);

  useEffect(() => {
    load();
  }, [load]);

  async function save(body: Parameters<typeof updateScoringCard>[2]) {
    setSaving(true);
    setError(null);
    try {
      setCard(await updateScoringCard(id, participantId, body));
      setSavedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that.");
    } finally {
      setSaving(false);
    }
  }

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error && !card) return <main><div className="notice bad">{error}</div></main>;
  if (!card) return <main><p className="muted">Loading…</p></main>;

  const tagged = new Set(card.skill_ids);

  return (
    <main>
      <Link
        href={`/company/challenges/${id}?section=judging`}
        className="small muted"
        style={{ textDecoration: "none" }}
      >
        &larr; Back to the cohort
      </Link>

      <div className="row" style={{ justifyContent: "space-between", marginTop: "0.5rem" }}>
        <h1 style={{ margin: 0 }}>{card.name}</h1>
        <span className={`tag ${card.complete ? "open" : ""}`}>
          {card.total !== null ? `${card.total}/20` : "in progress"}
        </span>
      </div>
      {card.submission.pitch_at && (
        <p className="small muted" style={{ marginTop: "0.4rem" }}>
          {formatSlot(card.submission.pitch_at)} SGT
        </p>
      )}
      {card.submission.meet_link && (
        <p className="small" style={{ marginTop: "0.25rem" }}>
          Same room for every pitch.{" "}
          <a href={card.submission.meet_link} target="_blank" rel="noreferrer">
            {card.submission.meet_link}
          </a>
        </p>
      )}

      <h2>What they handed in</h2>
      {card.submission.links.length === 0 ? (
        <p className="muted small">Nothing submitted.</p>
      ) : (
        <div className="panel">
          {card.submission.links.map((link) => (
            <div className="row" key={link.slot} style={{ justifyContent: "space-between" }}>
              <div style={{ minWidth: 0, paddingRight: "0.75rem" }}>
                <strong style={{ textTransform: "capitalize" }}>{link.slot}</strong>
                <div
                  className="small muted"
                  style={{ overflowWrap: "anywhere" }}
                >
                  {link.filename ?? link.url ?? "Nothing submitted"}
                </div>
              </div>
              <div className="row" style={{ gap: "0.5rem", alignItems: "center", flexShrink: 0 }}>
                {link.access_status !== "ok" && (
                  <span className="tag">{link.access_status}</span>
                )}
                {link.snapshot_url && (
                  <a href={assetUrl(link.snapshot_url)} target="_blank" rel="noreferrer">
                    Submission
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
          <p className="small muted" style={{ marginBottom: 0 }}>
            The submission is the copy taken at the deadline. A link can have
            changed since, so judge the submission when there is one.
          </p>
        </div>
      )}

      <h2>Score</h2>
      <p className="small muted">
        Saves as you go{savedAt && ` · last saved ${savedAt}`}. The total appears once
        all four are rated.
      </p>
      {error && <div className="notice bad">{error}</div>}

      {card.criteria.map((criterion) => (
        <div className="rubric" key={criterion.criterion_id}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>
              {criterion.slot}. {criterion.name}
            </strong>
            {criterion.is_universal && <span className="tag">universal</span>}
          </div>
          <div className="anchors">
            <div>
              <b>5</b> <span>{criterion.anchor_5}</span>
            </div>
            <div>
              <b>3</b> <span>{criterion.anchor_3}</span>
            </div>
            <div>
              <b>1</b> <span>{criterion.anchor_1}</span>
            </div>
          </div>
          <div className="row" style={{ gap: "0.4rem", marginTop: "0.5rem" }}>
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                className={criterion.value === value ? "" : "secondary"}
                disabled={saving}
                onClick={() =>
                  save({ ratings: { [criterion.criterion_id]: value } })
                }
              >
                {value}
              </button>
            ))}
          </div>
        </div>
      ))}

      <h2>What you saw</h2>
      <p className="small muted">
        Tag what they actually demonstrated. This lands on their profile when
        you close and issue — not when you tag — so a tag is still a claim you
        are making about them.
      </p>
      <SkillPicker
        options={card.skill_options}
        selectedIds={card.skill_ids}
        disabled={saving}
        onToggle={(id) =>
          save({
            skill_ids: tagged.has(id)
              ? card.skill_ids.filter((existing) => existing !== id)
              : [...card.skill_ids, id],
          })
        }
      />

      <TestimonialBox
        programmeId={id}
        participantId={participantId}
        skillsTagged={card.skill_ids.length > 0}
        skillsSaving={saving}
      />

      <h2>Would you refer them</h2>
      <p className="small muted">
        Never shown to the participant. It is the answer that makes this worth
        running.
      </p>
      <div className="row" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
        {REFERRAL.map((option) => (
          <button
            key={option.value}
            className={card.would_refer === option.value ? "" : "secondary"}
            disabled={saving}
            onClick={() => save({ would_refer: option.value })}
          >
            {option.label}
          </button>
        ))}
      </div>
    </main>
  );
}

/**
 * Optional, and kept away from the score on purpose.
 *
 * A testimonial is a public claim the company puts its name to; a score is a
 * private working note. They get written in the same sitting and must never
 * travel together, so this saves separately and carries no reference to the
 * rubric above it.
 *
 * Publishing is one-way. By the time someone has it on a CV, retracting it is
 * not ours to do - but the wording stays editable. Publishing turns the text
 * into a PDF they can download.
 */
function TestimonialBox({
  programmeId,
  participantId,
  skillsTagged,
  skillsSaving,
}: {
  programmeId: string;
  participantId: string;
  skillsTagged: boolean;
  skillsSaving: boolean;
}) {
  const [existing, setExisting] = useState<TestimonialOut | null>(null);
  const [body, setBody] = useState("");
  const [baseline, setBaseline] = useState("");
  const [busy, setBusy] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  useEffect(() => {
    getTestimonial(programmeId, participantId)
      .then((found) => {
        setExisting(found);
        const next = found?.body ?? "";
        setBody(next);
        setBaseline(next);
      })
      .catch(() => setExisting(null));
  }, [programmeId, participantId]);

  const { status: draftStatus, error: draftError } = useAutosave(
    body,
    baseline,
    async (next) => {
      if (!next.trim() && !baseline.trim()) return;
      const saved = await writeTestimonial(programmeId, participantId, {
        body: next.trim(),
        publish: false,
      });
      setExisting(saved);
      setBaseline(saved.body);
    },
    900,
  );

  async function draft() {
    setDrafting(true);
    setError(null);
    setFlash(null);
    try {
      const drafted = await draftTestimonial(programmeId, participantId);
      setBody(drafted.body);
      setFlash(
        "Drafted from the skills you tagged and this challenge's brief. It saves as you edit — publish when you mean it.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not draft that.");
    } finally {
      setDrafting(false);
    }
  }

  async function publish() {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const saved = await writeTestimonial(programmeId, participantId, {
        body: body.trim(),
        publish: true,
      });
      setExisting(saved);
      setBaseline(saved.body);
      setFlash("Published.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not publish that.");
    } finally {
      setBusy(false);
    }
  }

  const published = existing?.published_at != null;
  const hasPdf = Boolean(existing?.pdf_url);
  const locked = busy || drafting || skillsSaving;

  return (
    <>
      <h2>Testimonial (optional)</h2>
      <p className="small muted">
        Only if you mean it. One you chose to write is worth more than one everyone
        was made to, and this is the part they will actually carry with them.
        {published
          ? " Ready for Close and issue. You can still edit the wording."
          : " A draft stays private and saves as you type. Mark it ready when the wording is finished — it goes on their profile only when you Close and issue."}
        {" "}
        Drafting uses the skills you tagged above and this challenge's brief. It will
        not invent anything you did not tag.
      </p>
      <div className="field">
        <textarea
          id="testimonial"
          rows={12}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="I am pleased to recommend…"
        />
        <button
          className="secondary"
          disabled={locked || !skillsTagged}
          onClick={draft}
          style={{ marginTop: "0.5rem" }}
        >
          {drafting ? "Drafting…" : "Draft from skills"}
        </button>
      </div>
      {hasPdf && existing?.pdf_url && (
        <p>
          <a href={assetUrl(existing.pdf_url)} target="_blank" rel="noreferrer">
            View PDF
          </a>
        </p>
      )}
      {(error || draftError) && (
        <div className="notice bad">{error ?? draftError}</div>
      )}
      {flash && <div className="notice good">{flash}</div>}
      <p className="small muted">
        {autosaveLabel(draftStatus)
          ? `Draft ${autosaveLabel(draftStatus)?.toLowerCase()}`
          : "Draft saves as you type"}
        {published ? " · ready for Close and issue" : ""}.
      </p>
      {!published && (
        <div className="row" style={{ gap: "0.75rem", flexWrap: "wrap" }}>
          <button disabled={locked || !body.trim()} onClick={publish}>
            Ready for Close and issue
          </button>
        </div>
      )}
    </>
  );
}

