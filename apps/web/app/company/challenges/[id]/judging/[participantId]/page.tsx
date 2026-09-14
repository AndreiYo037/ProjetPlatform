"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  assetUrl,
  getScoringCard,
  updateScoringCard,
  type ScoringCard,
} from "@/lib/api";
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
        href={`/company/challenges/${id}/judging`}
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

      <h2>What they handed in</h2>
      {card.submission.links.length === 0 ? (
        <p className="muted small">Nothing submitted.</p>
      ) : (
        <div className="panel">
          {card.submission.links.map((link) => (
            <div className="row" key={link.slot} style={{ justifyContent: "space-between" }}>
              <div>
                <strong style={{ textTransform: "capitalize" }}>{link.slot}</strong>
                <div className="small muted">{link.filename ?? "No file"}</div>
              </div>
              <div className="row" style={{ gap: "0.5rem", alignItems: "center" }}>
                {link.access_status !== "ok" && (
                  <span className="tag">{link.access_status}</span>
                )}
                {link.snapshot_url && (
                  <a href={assetUrl(link.snapshot_url)} target="_blank" rel="noreferrer">
                    Snapshot
                  </a>
                )}
                {link.url && (
                  <a href={link.url} target="_blank" rel="noreferrer" className="small muted">
                    Live
                  </a>
                )}
              </div>
            </div>
          ))}
          <p className="small muted" style={{ marginBottom: 0 }}>
            The snapshot is the copy taken at the deadline. The live document can
            have changed since, so judge the snapshot.
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
        Tag what they actually demonstrated. This is what shows on their profile,
        so a tag is a claim you are making about them.
      </p>
      <div className="row" style={{ flexWrap: "wrap", gap: "0.4rem" }}>
        {card.skill_options.map((skill) => (
          <button
            key={skill.id}
            className={tagged.has(skill.id) ? "" : "secondary"}
            disabled={saving}
            onClick={() =>
              save({
                skill_ids: tagged.has(skill.id)
                  ? card.skill_ids.filter((existing) => existing !== skill.id)
                  : [...card.skill_ids, skill.id],
              })
            }
          >
            {skill.name}
          </button>
        ))}
      </div>

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
