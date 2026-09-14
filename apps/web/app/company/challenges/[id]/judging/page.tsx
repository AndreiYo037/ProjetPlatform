"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import {
  getProgramme,
  listSubmissionCards,
  type ProgrammeDetail,
  type SubmissionCard,
} from "@/lib/api";
import { useActor } from "@/lib/useActor";

/**
 * Judging day: the cohort as a stack of submission cards, in pitch order.
 *
 * Each card is what one person handed in, and opening it is opening their
 * scoring card. Everything is individual, so there is nothing to disambiguate
 * between the work and the verdict on it.
 */
export default function JudgingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const gate = useActor("company_user");
  const [programme, setProgramme] = useState<ProgrammeDetail | null>(null);
  const [cards, setCards] = useState<SubmissionCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    try {
      const [p, list] = await Promise.all([
        getProgramme(id).catch(() => null),
        listSubmissionCards(id),
      ]);
      setProgramme(p);
      setCards(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the cohort.");
    }
  }, [id, gate.status]);

  useEffect(() => {
    load();
  }, [load]);

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!cards) return <main><p className="muted">Loading…</p></main>;

  const scored = cards.filter((card) => card.your_total !== null).length;

  return (
    <main>
      <Link href={`/company/challenges/${id}`} className="small muted" style={{ textDecoration: "none" }}>
        &larr; Back to the challenge
      </Link>
      <h1 style={{ marginTop: "0.5rem" }}>Judging</h1>
      <p className="lede">
        {programme?.title}
        {programme?.pitch_at && ` · pitches ${new Date(programme.pitch_at).toLocaleString()}`}
      </p>

      {cards.length === 0 ? (
        <p className="muted small">
          Nobody to judge yet. Cards appear once participants have seats.
        </p>
      ) : (
        <>
          <p className="small muted">
            {scored} of {cards.length} scored. Open a card to watch the pitch against
            the rubric; it saves as you go.
          </p>
          {cards.map((card) => (
            <Link
              key={card.participant_id}
              href={`/company/challenges/${id}/judging/${card.participant_id}`}
              className="card"
              style={{ display: "block", textDecoration: "none" }}
            >
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <strong>
                    {card.run_order !== null && `${card.run_order}. `}
                    {card.name}
                  </strong>
                  <div className="small muted">
                    {card.organisation ?? "—"} · {card.links.length} file
                    {card.links.length === 1 ? "" : "s"}
                  </div>
                </div>
                <div className="row" style={{ gap: "0.5rem", alignItems: "center" }}>
                  {!card.complete && <span className="tag">incomplete</span>}
                  {card.locked && <span className="tag">locked</span>}
                  <span className={`tag ${card.your_total !== null ? "open" : ""}`}>
                    {card.your_total !== null ? `${card.your_total}/20` : "not scored"}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </>
      )}
    </main>
  );
}
