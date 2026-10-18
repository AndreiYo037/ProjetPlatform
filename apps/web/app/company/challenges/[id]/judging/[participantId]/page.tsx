"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import SkillPicker from "@/components/SkillPicker";
import {
  assetUrl,
  externalHref,
  getScoringCard,
  getTestimonial,
  signTestimonial,
  updateScoringCard,
  uploadTestimonialFile,
  writeTestimonial,
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
function TestimonialBox({
  programmeId,
  participantId,
  skillsSaving,
}: {
  programmeId: string;
  participantId: string;
  skillsSaving: boolean;
}) {
  const [existing, setExisting] = useState<TestimonialOut | null>(null);
  const [body, setBody] = useState("");
  const [baseline, setBaseline] = useState("");
  const [busy, setBusy] = useState(false);
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

  async function attach(file: File) {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const saved = await uploadTestimonialFile(programmeId, participantId, file);
      setExisting(saved);
      setFlash("Your PDF is attached. It replaces a generated letter.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not attach that PDF.");
    } finally {
      setBusy(false);
    }
  }

  async function sign(signature: { drawn: string | null; typed: boolean }) {
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      // Make sure the server holds the wording on screen before signing it.
      if (body.trim() !== baseline.trim()) {
        const current = await writeTestimonial(programmeId, participantId, {
          body: body.trim(),
          publish: false,
        });
        setBaseline(current.body);
      }
      const saved = await signTestimonial(programmeId, participantId, {
        ...(signature.drawn ? { signature: signature.drawn } : {}),
        typed: signature.typed,
        confirm: true,
      });
      setExisting(saved);
      setBaseline(saved.body);
      setFlash("Signed and published. The letter now carries your signature.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign that letter.");
    } finally {
      setBusy(false);
    }
  }

  const published = existing?.published_at != null;
  const signed = Boolean(existing?.signed);
  const hasPdf = Boolean(existing?.pdf_url);
  const locked = busy || skillsSaving;

  return (
    <>
      <h2>
        Testimonial <span className="tag">Optional</span>
      </h2>
      <p className="small muted">
        Only if you mean it. One you chose to write is worth more than one everyone
        was made to, and this is the part they will actually carry with them.
        {signed
          ? " Signed. Changing the wording clears the signature and you sign again."
          : published
            ? " You can still edit the wording."
            : " A draft stays private and saves as you type. Sign it when the wording is finished, or attach your own PDF if you reformatted it. It goes on their profile only when you Close and issue."}
      </p>
      <div className="field">
        <textarea
          id="testimonial"
          rows={12}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="I am pleased to recommend…"
        />
      </div>
      {hasPdf && existing?.pdf_url && (
        <p>
          <a href={assetUrl(existing.pdf_url)} target="_blank" rel="noreferrer">
            {existing.own_file ? "View your PDF" : "View PDF"}
          </a>
        </p>
      )}
      <div className="field">
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
      {(error || draftError) && (
        <div className="notice bad">{error ?? draftError}</div>
      )}
      {flash && <div className="notice good">{flash}</div>}
      <p className="small muted">
        {autosaveLabel(draftStatus)
          ? `Draft ${autosaveLabel(draftStatus)?.toLowerCase()}`
          : "Draft saves as you type"}
        {existing?.own_file
          ? " · your PDF attached"
          : signed
            ? " · signed"
            : published
              ? " · published, not signed"
              : ""}
        .
      </p>
      {existing?.signed && existing.signed_at && (
        <div className="notice good">
          Signed by {existing.signed_name} on {formatSlot(existing.signed_at)}
          {existing.signature_typed ? " with a typed name" : ""}.
        </div>
      )}
      {existing?.needs_signature && (
        <div className="notice warn">
          <strong>Published without a signature.</strong> This letter went out before signing
          existed. Sign it below to reissue it as a signed letter.
        </div>
      )}
      {!existing?.own_file && !signed && existing && body.trim() && (
        <SigningPanel
          name={existing.author_name ?? "the author"}
          reissue={Boolean(existing.needs_signature)}
          disabled={locked}
          busy={busy}
          onSign={sign}
        />
      )}
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

/**
 * Sign and publish. Draw a signature (finger or mouse), or sign with the typed
 * name. Pressing the button is the act of signing; nothing is sent until a
 * signature exists.
 */
function SigningPanel({
  name,
  reissue,
  disabled,
  busy,
  onSign,
}: {
  name: string;
  reissue: boolean;
  disabled: boolean;
  busy: boolean;
  onSign: (signature: { drawn: string | null; typed: boolean }) => Promise<void> | void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);
  const last = useRef<{ x: number; y: number } | null>(null);
  const [hasInk, setHasInk] = useState(false);
  const [typed, setTyped] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    ctx.lineWidth = 2.6;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#0b1a5c";
  }, [typed]);

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
    setHasInk(true);
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
    drawing.current = false;
    last.current = null;
  }

  function clear() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.restore();
    setHasInk(false);
  }

  const ready = typed || hasInk;

  function submit() {
    if (!ready) return;
    if (typed) {
      void onSign({ drawn: null, typed: true });
      return;
    }
    const data = canvasRef.current?.toDataURL("image/png") ?? null;
    void onSign({ drawn: data, typed: false });
  }

  return (
    <div className="rubric" style={{ border: "2px solid var(--accent)", marginTop: "1rem" }}>
      <strong>{reissue ? "Sign and reissue this letter" : "Sign and publish"}</strong>
      <p className="small muted" style={{ margin: "0.25rem 0 0.75rem" }}>
        Your signature goes on the letter with the date, and is tied to this exact wording.
        Change a word afterwards and you will need to sign again.
      </p>

      {typed ? (
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
          }}
        >
          {name}
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
          {!hasInk && (
            <p className="small muted" style={{ margin: "0.35rem 0 0" }}>
              Sign here with your finger or mouse.
            </p>
          )}
        </div>
      )}

      <div className="row" style={{ gap: "0.5rem", margin: "0.6rem 0", flexWrap: "wrap" }}>
        {!typed && (
          <button type="button" className="secondary small" onClick={clear} disabled={!hasInk}>
            Clear
          </button>
        )}
        <button
          type="button"
          className="secondary small"
          onClick={() => {
            setTyped((value) => !value);
            setHasInk(false);
          }}
        >
          {typed ? "Draw my signature instead" : "Sign with my typed name instead"}
        </button>
      </div>

      <div className="row" style={{ marginTop: "0.75rem" }}>
        <button disabled={disabled || !ready} onClick={submit}>
          {busy ? "Signing…" : reissue ? "Sign and reissue" : "Sign and publish"}
        </button>
      </div>
    </div>
  );
}
