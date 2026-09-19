"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import ChallengeCards from "@/components/ChallengeCards";
import { SkillTags, toTaggedSkills } from "@/components/SkillTags";
import {
  assetUrl,
  getPortfolio,
  listChallenges,
  type Portfolio,
  type PublicListingSummary,
} from "@/lib/api";
import { formatDay, formatDayRange } from "@/lib/dates";
import { useActor } from "@/lib/useActor";

/**
 * Home is the portfolio first (skills, credentials, testimonials), then open
 * challenges to apply to at the bottom.
 *
 * Details you maintain (name, school) sit behind Update profile. The
 * programme(s) you are on sit behind My programmes.
 *
 * No scores, ever. FR-1004 keeps them out of the schema.
 */
export default function ParticipantHomePage() {
  const gate = useActor("participant");
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [openChallenges, setOpenChallenges] = useState<PublicListingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (gate.status !== "ready") return;
    try {
      const [nextPortfolio, challenges] = await Promise.all([
        getPortfolio(),
        listChallenges({ limit: 100 }).catch(() => [] as PublicListingSummary[]),
      ]);
      setPortfolio(nextPortfolio);
      setOpenChallenges(challenges);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your profile.");
    }
  }, [gate.status]);

  useEffect(() => {
    load();
  }, [load]);

  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;
  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!portfolio) return <main><p className="muted">Loading…</p></main>;

  const attested = toTaggedSkills(portfolio.skills);

  return (
    <main>
      <h1 style={{ marginTop: 0 }}>{portfolio.name}</h1>
      <p className="lede">
        {portfolio.programmes_completed === 0
          ? "Nothing here yet."
          : `${portfolio.programmes_completed} programme${
              portfolio.programmes_completed === 1 ? "" : "s"
            } completed.`}
      </p>

      <h2>Skills</h2>
      {attested.length === 0 ? (
        <p className="muted small">
          Skills appear here when a company closes the challenge.
        </p>
      ) : (
        <SkillTags skills={attested} />
      )}

      <h2>Credentials</h2>
      {portfolio.credentials.length === 0 ? (
        <p className="muted small">
          A credential appears here when a company closes the challenge.
        </p>
      ) : (
        portfolio.credentials.map((credential) => (
          <div className="panel" key={`${credential.company}-${credential.programme}`}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
              <strong>{credential.company}</strong>
              <span className="small muted">{credential.programme}</span>
            </div>
            {formatDayRange(credential.start_at, credential.ended_at) && (
              <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
                {formatDayRange(credential.start_at, credential.ended_at)}
              </p>
            )}
            {credential.attesters.length > 0 && (
              <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
                Endorsed by {credential.attesters.join(", ")}
              </p>
            )}
            <SkillTags skills={credential.skills.map((name) => ({ name }))} />
          </div>
        ))
      )}

      <h2>What they said</h2>
      {portfolio.testimonials.length === 0 ? (
        <p className="muted small">
          A company testimonial appears here when they close the challenge.
        </p>
      ) : (
        portfolio.testimonials.map((testimonial, index) => (
          <div className="card" key={index}>
            <div className="small muted">
              {testimonial.author_name}
              {testimonial.author_title && `, ${testimonial.author_title}`} ·{" "}
              {testimonial.company} · {testimonial.programme}
              {formatDay(testimonial.published_at) && ` · ${formatDay(testimonial.published_at)}`}
            </div>
            {testimonial.pdf_url && (
              <p style={{ marginBottom: 0 }}>
                <a href={assetUrl(testimonial.pdf_url)} target="_blank" rel="noreferrer">
                  View PDF
                </a>
              </p>
            )}
          </div>
        ))
      )}

      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ marginBottom: 0 }}>Active challenges</h2>
        <Link className="small" href="/challenges">
          Browse all
        </Link>
      </div>
      {openChallenges === null ? (
        <p className="muted small">Loading challenges…</p>
      ) : openChallenges.length === 0 ? (
        <p className="muted small">No active challenges right now — check back soon.</p>
      ) : (
        <ChallengeCards items={openChallenges} />
      )}
    </main>
  );
}
