"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import SkillPicker from "@/components/SkillPicker";
import {
  assetUrl,
  externalHref,
  getScoringCard,
  getLetterContext,
  getTestimonial,
  signTestimonial,
  updateScoringCard,
  uploadTestimonialFile,
  writeTestimonial,
  type LetterContext,
  type ScoringCard,
  type TestimonialOut,
} from "@/lib/api";
import { autosaveLabel, useAutosave } from "@/lib/useAutosave";
import { formatSlot } from "@/lib/dates";
import { SHOW_SUBMISSION_MEMO } from "@/lib/features";
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
          {card.total !== null ? `${card.total}/${card.max_total}` : "in progress"}
        </span>
      </div>
      {card.submission.pitch_at && (
        <p className="small muted" style={{ marginTop: "0.4rem" }}>
          {formatSlot(card.submission.pitch_at)}
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
      {(() => {
        const links = card.submission.links.filter(
          (link) => SHOW_SUBMISSION_MEMO || link.slot !== "memo",
        );
        if (links.length === 0) {
          return <p className="muted small">Nothing submitted.</p>;
        }
        return (
        <div className="panel">
          {links.map((link) => (
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
        );
      })()}

      <h2>
        Score <span className="tag open">Required</span>
      </h2>
      <p className="small muted">
        Rate every rubric box below. Or use the override at the top to give your own
        overall score instead. Everything after the score is optional and can be left
        blank. Saves as you go{savedAt && ` · last saved ${savedAt}`}. The rubric total
        appears once every box is rated.
      </p>
      {error && <div className="notice bad">{error}</div>}

      <OwnScoreInput
        key={participantId}
        saved={card.manual_total ?? null}
        max={card.manual_max}
        onSave={(value) =>
          value === null ? save({ clear_manual_total: true }) : save({ manual_total: value })
        }
      />

      <h3 style={{ margin: "1.25rem 0 0.25rem" }}>Rubric</h3>
      {card.manual_total !== null && (
        <div className="notice warn">
          <strong>Overridden.</strong> Your own score of {card.manual_total}/{card.manual_max} is
          what counts for this candidate. These rubric ratings are kept but not used. Clear the
          override above to use them.
        </div>
      )}
      <div style={card.manual_total !== null ? { opacity: 0.45 } : undefined}>
      {card.criteria.map((criterion) => (
        <div className="rubric" key={criterion.criterion_id}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>
              {criterion.slot}. {criterion.name}
              {criterion.role_name ? ` · ${criterion.role_name}` : ""}
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
      </div>

      <h2>
        What you saw <span className="tag">Optional</span>
      </h2>
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
        skillsSaving={saving}
      />

      <h2>
        Would you refer them <span className="tag">Optional</span>
      </h2>
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
type LetterDraft = {
  recipients: string[];
  body: string;
  name: string;
  title: string;
  company: string;
  details: string;
};

const EMPTY_LETTER: LetterDraft = {
  recipients: [],
  body: "",
  name: "",
  title: "",
  company: "",
  details: "",
};

function letterFrom(context: LetterContext, found: TestimonialOut | null): LetterDraft {
  if (found) {
    return {
      recipients: found.recipients.length ? found.recipients : [context.participant_name],
      body: found.body,
      name: found.signoff_name,
      title: found.signoff_title,
      company: found.signoff_company,
      details: found.company_details,
    };
  }
  return {
    recipients: [context.participant_name],
    body: "",
    name: context.author_name,
    title: context.author_title,
    company: context.company_name,
    details: "",
  };
}

function letterPayload(draft: LetterDraft) {
  return {
    body: draft.body.trim(),
    publish: false,
    recipients: draft.recipients.map((name) => name.trim()).filter(Boolean),
    signoff_name: draft.name,
    signoff_title: draft.title,
    signoff_company: draft.company,
    company_details: draft.details,
  };
}

const LETTER_CAPTION: React.CSSProperties = {
  fontSize: "0.72rem",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "var(--muted)",
  margin: "0 0 0.3rem",
};

/**
 * The testimonial, laid out as the letter it becomes. Every part of the letter
 * is a box in the order it prints: the names it is about, the wording, the
 * signature, who it is from, and the company's own details. Nothing is hidden
 * behind a "generate" step; what is on screen is what is typeset and signed.
 *
 * Optional, and kept away from the score on purpose. A testimonial is a public
 * claim the company puts its name to; a score is a private working note. It
 * goes on their profile only when the company closes and issues.
 */
function TestimonialBox({
  programmeId,
  participantId,
  skillsSaving,
}: {
  programmeId: string;
  participantId: string;
  skillsSaving: boolean;
}) {
  const [context, setContext] = useState<LetterContext | null>(null);
  const [existing, setExisting] = useState<TestimonialOut | null>(null);
  const [draft, setDraft] = useState<LetterDraft | null>(null);
  const [baseline, setBaseline] = useState<LetterDraft | null>(null);
  const [signature, setSignature] = useState<SignatureValue>({ typed: false, drawn: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getLetterContext(programmeId, participantId),
      getTestimonial(programmeId, participantId).catch(() => null),
    ])
      .then(([loaded, found]) => {
        const next = letterFrom(loaded, found);
        setContext(loaded);
        setExisting(found);
        setDraft(next);
        setBaseline(next);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not open the testimonial."),
      );
  }, [programmeId, participantId]);

  const { status: draftStatus, error: draftError } = useAutosave(
    draft ?? EMPTY_LETTER,
    baseline ?? EMPTY_LETTER,
    async (next) => {
      // The letter is not saved until there is wording to keep.
      if (!next.body.trim() && !existing) return;
      const saved = await writeTestimonial(programmeId, participantId, letterPayload(next));
      setExisting(saved);
      setBaseline(next);
    },
    900,
  );

  function change(patch: Partial<LetterDraft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
  }

  function setRecipient(index: number, value: string) {
    if (!draft) return;
    change({ recipients: draft.recipients.map((name, i) => (i === index ? value : name)) });
  }

  async function attach(file: File) {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const saved = await uploadTestimonialFile(programmeId, participantId, file);
      setExisting(saved);
      setFlash("Your PDF is attached. It replaces the typeset letter.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not attach that PDF.");
    } finally {
      setBusy(false);
    }
  }

  async function sign() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      // The server signs what it holds, so make sure it holds what is on screen.
      if (JSON.stringify(draft) !== JSON.stringify(baseline)) {
        await writeTestimonial(programmeId, participantId, letterPayload(draft));
        setBaseline(draft);
      }
      const saved = await signTestimonial(programmeId, participantId, {
        ...(signature.drawn ? { signature: signature.drawn } : {}),
        typed: signature.typed,
        confirm: true,
      });
      setExisting(saved);
      setSignature({ typed: false, drawn: null });
      setFlash("Signed. The letter carries your signature and goes on their profile when you close and issue.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign that letter.");
    } finally {
      setBusy(false);
    }
  }

  if (!draft || !context) {
    return (
      <>
        <h2>
          Testimonial <span className="tag">Optional</span>
        </h2>
        {error ? <div className="notice bad">{error}</div> : <p className="muted small">Loading…</p>}
      </>
    );
  }

  const signed = Boolean(existing?.signed);
  const locked = busy || skillsSaving;
  const today = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Singapore",
  });
  const canSign = !locked && draft.body.trim().length > 0 && (signature.typed || signature.drawn !== null);

  return (
    <>
      <h2>
        Testimonial <span className="tag">Optional</span>
      </h2>
      <p className="small muted">
        Only if you mean it. This is the letter they will carry with them, laid out as it
        prints. Fill in each part, then sign. It goes on their profile only when you close
        and issue.
      </p>

      {existing?.own_file ? (
        <div className="notice">
          You attached your own PDF, so it is used as it is and is not signed here.{" "}
          {existing.pdf_url && (
            <a href={assetUrl(existing.pdf_url)} target="_blank" rel="noreferrer">
              View your PDF
            </a>
          )}
        </div>
      ) : (
        <div className="card" style={{ maxWidth: "48rem" }}>
          <div
            className="row"
            style={{ justifyContent: "space-between", alignItems: "center", gap: "1rem" }}
          >
            {context.company_logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={assetUrl(context.company_logo_url)}
                alt={context.company_name}
                style={{ maxHeight: "3.2rem", maxWidth: "10rem", objectFit: "contain" }}
              />
            ) : (
              <span />
            )}
            <strong>{context.company_name}</strong>
          </div>
          <hr style={{ margin: "0.75rem 0 1rem" }} />

          <p className="small muted" style={{ margin: 0 }}>
            {today} · To whom it may concern
          </p>

          <p style={LETTER_CAPTION}>Re: the people this is about</p>
          {draft.recipients.map((name, index) => (
            <div key={index} className="row" style={{ gap: "0.5rem", marginBottom: "0.4rem" }}>
              <input
                type="text"
                aria-label={`Name ${index + 1}`}
                value={name}
                placeholder="Full name"
                onChange={(e) => setRecipient(index, e.target.value)}
                style={{ flex: "1 1 14rem" }}
              />
              {draft.recipients.length > 1 && (
                <button
                  type="button"
                  className="secondary small"
                  onClick={() =>
                    change({ recipients: draft.recipients.filter((_, i) => i !== index) })
                  }
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <div style={{ marginBottom: "0.4rem" }}>
            <button
              type="button"
              className="secondary small"
              onClick={() => change({ recipients: [...draft.recipients, ""] })}
            >
              + Add another name
            </button>
          </div>
          <p className="small" style={{ margin: "0 0 1rem" }}>
            <strong>{context.programme_title}</strong>
          </p>

          <p style={LETTER_CAPTION}>Your testimonial</p>
          <textarea
            id="testimonial"
            rows={12}
            value={draft.body}
            onChange={(e) => change({ body: e.target.value })}
            placeholder="I am pleased to recommend…"
            style={{ width: "100%" }}
          />

          <p style={{ margin: "1rem 0 0.4rem" }}>Sincerely,</p>

          {signed ? (
            <div className="notice good">
              Signed by {existing?.signed_name}
              {existing?.signed_at ? ` on ${formatSlot(existing.signed_at)}` : ""}
              {existing?.signature_typed ? " with a typed name" : ""}.{" "}
              {existing?.pdf_url && (
                <a href={assetUrl(existing.pdf_url)} target="_blank" rel="noreferrer">
                  View the letter
                </a>
              )}
              <div className="small muted">
                Change any part of the letter and the signature is cleared, so you sign again.
              </div>
            </div>
          ) : (
            <>
              {existing?.needs_signature && (
                <div className="notice warn">
                  <strong>Published without a signature.</strong> This letter went out before
                  signing existed. Sign it to reissue it as a signed letter.
                </div>
              )}
              <p style={LETTER_CAPTION}>Your signature</p>
              <SignaturePad
                typedName={draft.name}
                value={signature}
                onChange={setSignature}
              />
            </>
          )}

          <p style={{ ...LETTER_CAPTION, marginTop: "1rem" }}>From</p>
          <div className="field">
            <label htmlFor="letter-name">Name</label>
            <input
              id="letter-name"
              type="text"
              value={draft.name}
              onChange={(e) => change({ name: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="letter-title">Title</label>
            <input
              id="letter-title"
              type="text"
              value={draft.title}
              placeholder="e.g. Head of Data"
              onChange={(e) => change({ title: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="letter-company">Company</label>
            <input
              id="letter-company"
              type="text"
              value={draft.company}
              onChange={(e) => change({ company: e.target.value })}
            />
          </div>

          <div className="field">
            <label htmlFor="letter-details">Company details</label>
            <textarea
              id="letter-details"
              rows={4}
              value={draft.details}
              placeholder={"Address, website, email.\nPrinted under your name."}
              onChange={(e) => change({ details: e.target.value })}
              style={{ width: "100%" }}
            />
          </div>

          <hr style={{ margin: "0.75rem 0" }} />
          <p className="small muted" style={{ margin: 0 }}>
            Issued through Projet
          </p>
        </div>
      )}

      {(error || draftError) && <div className="notice bad">{error ?? draftError}</div>}
      {flash && <div className="notice good">{flash}</div>}
      <p className="small muted">
        {autosaveLabel(draftStatus)
          ? `Draft ${autosaveLabel(draftStatus)?.toLowerCase()}`
          : "Draft saves as you type"}
        {existing?.own_file
          ? " · your PDF attached"
          : signed
            ? " · signed"
            : existing?.published_at
              ? " · published, not signed"
              : ""}
        .
      </p>

      {!existing?.own_file && !signed && (
        <div className="row" style={{ gap: "0.75rem", flexWrap: "wrap" }}>
          <button disabled={!canSign} onClick={sign}>
            {busy
              ? "Signing…"
              : existing?.needs_signature
                ? "Sign and reissue"
                : "Sign and publish"}
          </button>
        </div>
      )}

      <details style={{ marginTop: "1rem" }}>
        <summary className="small muted">Use your own PDF instead</summary>
        <div className="field" style={{ marginTop: "0.5rem" }}>
          <label htmlFor="testimonial-file">Attach your own PDF</label>
          <input
            id="testimonial-file"
            type="file"
            accept="application/pdf,.pdf"
            disabled={locked}
            onChange={(event) => {
              const picked = event.target.files?.[0];
              event.target.value = "";
              if (picked) void attach(picked);
            }}
          />
          <p className="small muted">
            Use this if you reformatted the letter. Attaching replaces the typeset letter, and
            your own file is not signed here.
          </p>
        </div>
      </details>
    </>
  );
}

/**
 * A judge's own overall score, used instead of the rubric. It sits above the
 * rubric so it is in view without scrolling past every criterion. Saves when
 * the judge pauses; clearing the box goes back to the rubric total.
 */
function OwnScoreInput({
  saved,
  max,
  onSave,
}: {
  saved: number | null;
  max: number;
  onSave: (value: number | null) => Promise<void> | void;
}) {
  const initial = saved === null ? "" : String(saved);
  const [text, setText] = useState(initial);
  const [baseline, setBaseline] = useState(initial);
  const trimmed = text.trim();
  const value = Number(trimmed);
  const valid = trimmed === "" || (Number.isInteger(value) && value >= 0 && value <= max);

  useAutosave(
    valid ? trimmed : baseline,
    baseline,
    async (next) => {
      await onSave(next === "" ? null : Number(next));
      setBaseline(next);
    },
    800,
  );

  return (
    <div
      className="rubric"
      style={{
        border: "2px solid var(--accent)",
        background: saved !== null ? "var(--accent-soft)" : undefined,
      }}
    >
      <label htmlFor="own-score">
        <strong>Override the rubric with your own score</strong>{" "}
        <span className="tag projet">Override</span>
      </label>
      <p className="small muted" style={{ margin: "0.25rem 0 0.5rem" }}>
        Optional. Type an overall score out of {max} and it replaces the rubric total for
        this candidate. The rubric ratings below are then ignored. Clear the box to go back
        to the rubric.
      </p>
      <div className="row" style={{ gap: "0.5rem", alignItems: "center" }}>
        <input
          id="own-score"
          type="number"
          inputMode="numeric"
          min={0}
          max={max}
          step={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ maxWidth: "8rem" }}
        />
        <span className="small muted">out of {max}</span>
      </div>
      {!valid && (
        <p className="small" style={{ color: "var(--danger)", marginBottom: 0 }}>
          Enter a whole number from 0 to {max}.
        </p>
      )}
    </div>
  );
}

type SignatureValue = { typed: boolean; drawn: string | null };

/**
 * Draw a signature with a finger or mouse, or sign with the typed name. The
 * drawing is handed up as a PNG each time the pen lifts; the Sign button lives
 * with the rest of the letter, so a name is never signed before it is filled in.
 */
function SignaturePad({
  typedName,
  value,
  onChange,
}: {
  typedName: string;
  value: SignatureValue;
  onChange: (next: SignatureValue) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);
  const last = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(canvas.clientWidth * ratio);
    canvas.height = Math.round(canvas.clientHeight * ratio);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    ctx.lineWidth = 2.6;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#0b1a5c";
  }, [value.typed]);

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function start(event: React.PointerEvent<HTMLCanvasElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    drawing.current = true;
    const p = point(event);
    last.current = p;
    const ctx = event.currentTarget.getContext("2d");
    if (ctx) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 0.8, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  function move(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current || !last.current) return;
    const ctx = event.currentTarget.getContext("2d");
    if (!ctx) return;
    const p = point(event);
    ctx.beginPath();
    ctx.moveTo(last.current.x, last.current.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    last.current = p;
  }

  function end() {
    if (!drawing.current) return;
    drawing.current = false;
    last.current = null;
    const data = canvasRef.current?.toDataURL("image/png") ?? null;
    onChange({ typed: false, drawn: data });
  }

  function clear() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.restore();
    onChange({ typed: false, drawn: null });
  }

  return (
    <div>
      {value.typed ? (
        <div
          style={{
            border: "1px dashed var(--line)",
            borderRadius: 8,
            padding: "1rem",
            background: "#fff",
            color: "#0b1a5c",
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontStyle: "italic",
            fontSize: "1.8rem",
            maxWidth: "34rem",
          }}
        >
          {typedName || "Your name"}
        </div>
      ) : (
        <div>
          <canvas
            ref={canvasRef}
            aria-label="Draw your signature here"
            onPointerDown={start}
            onPointerMove={move}
            onPointerUp={end}
            onPointerCancel={end}
            style={{
              width: "100%",
              maxWidth: "34rem",
              height: "9rem",
              display: "block",
              border: "1px dashed var(--line)",
              borderRadius: 8,
              background: "#fff",
              touchAction: "none",
              cursor: "crosshair",
            }}
          />
          {value.drawn === null && (
            <p className="small muted" style={{ margin: "0.35rem 0 0" }}>
              Sign here with your finger or mouse.
            </p>
          )}
        </div>
      )}
      <div className="row" style={{ gap: "0.5rem", margin: "0.6rem 0", flexWrap: "wrap" }}>
        {!value.typed && (
          <button
            type="button"
            className="secondary small"
            onClick={clear}
            disabled={value.drawn === null}
          >
            Clear
          </button>
        )}
        <button
          type="button"
          className="secondary small"
          onClick={() => onChange({ typed: !value.typed, drawn: null })}
        >
          {value.typed ? "Draw my signature instead" : "Sign with my typed name instead"}
        </button>
      </div>
    </div>
  );
}

