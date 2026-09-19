"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import ChallengeCards from "@/components/ChallengeCards";
import { SkillTags, SkillsBlock, toTaggedSkills } from "@/components/SkillTags";
import {
  assetUrl,
  getPortfolio,
  listChallenges,
  type Portfolio,
  type PublicListingSummary,
} from "@/lib/api";
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

  const empty =
    attested.length === 0 &&
    portfolio.credentials.length === 0 &&
    portfolio.testimonials.length === 0;

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

      {empty && (
        <div className="notice">
          Skills and credentials fill in after you pitch.
        </div>
      )}

      <SkillsBlock attested={attested} />

      {portfolio.credentials.length > 0 && (
        <>
          <h2>Credentials</h2>
          {portfolio.credentials.map((credential) => (
            <div className="panel" key={`${credential.company}-${credential.programme}`}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                <strong>{credential.company}</strong>
                <span className="small muted">{credential.programme}</span>
              </div>
              {credential.attesters.length > 0 && (
                <p className="small muted" style={{ margin: "0.2rem 0 0.5rem" }}>
                  Endorsed by {credential.attesters.join(", ")}
                </p>
              )}
              <SkillTags skills={credential.skills.map((name) => ({ name }))} />
            </div>
          ))}
        </>
      )}

      {portfolio.testimonials.length > 0 && (
        <>
          <h2>What they said</h2>
          {portfolio.testimonials.map((testimonial, index) => (
            <div className="card" key={index}>
              <div className="small muted">
                {testimonial.author_name}
                {testimonial.author_title && `, ${testimonial.author_title}`} ·{" "}
                {testimonial.company} · {testimonial.programme}
              </div>
              {testimonial.pdf_url && (
                <p style={{ marginBottom: 0 }}>
                  <a href={assetUrl(testimonial.pdf_url)} target="_blank" rel="noreferrer">
                    Download PDF
                  </a>
                </p>
              )}
            </div>
          ))}
        </>
      )}

      <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ marginBottom: 0 }}>Open challenges</h2>
        <Link className="small" href="/challenges">
          Browse all
        </Link>
      </div>
      {openChallenges === null ? (
        <p className="muted">Loading challenges…</p>
      ) : openChallenges.length === 0 ? (
        <p className="muted">No open challenges right now — check back soon.</p>
      ) : (
        <ChallengeCards items={openChallenges} />
      )}
    </main>
  );
}
