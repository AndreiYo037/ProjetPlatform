"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import ParticipantProfile from "@/components/ParticipantProfile";
import { getDashboard, type Dashboard } from "@/lib/api";
import { useActor } from "@/lib/useActor";

/**
 * The participant's home, which is not a programme.
 *
 * Their details and what they keep belong to the person and outlast any one
 * cohort; the programme is a thing they are currently doing and has its own
 * page. Keeping them apart means a participant between programmes still has
 * somewhere that is theirs.
 */
export default function ParticipantHomePage() {
  const gate = useActor("participant");
  const ready = gate.status === "ready";
  const [programme, setProgramme] = useState<Dashboard["programme"] | null>(null);
  const [checked, setChecked] = useState(false);

  const load = useCallback(async () => {
    if (!ready) return;
    try {
      setProgramme((await getDashboard()).programme);
    } catch {
      setProgramme(null);
    } finally {
      setChecked(true);
    }
  }, [ready]);

  useEffect(() => {
    load();
  }, [load]);

  if (!ready) return <ActorGateNotice gate={gate} />;

  return (
    <main className="narrow">
      <h1>Your home</h1>

      <h2>Your programme</h2>
      {!checked ? (
        <p className="muted small">Loading…</p>
      ) : programme ? (
        <div className="panel">
          <strong>{programme.title}</strong>
          <p className="small muted" style={{ margin: "0.3rem 0 0.8rem" }}>
            {programme.company} · {programme.role}
          </p>
          <Link className="btn" href="/dashboard">
            Open programme
          </Link>
        </div>
      ) : (
        <div className="panel">
          <strong>You are not on a programme yet.</strong>
          <p className="small muted" style={{ margin: "0.3rem 0 0.8rem" }}>
            Browse what companies are running right now and apply to one.
          </p>
          <Link className="btn" href="/challenges">
            See open challenges
          </Link>
        </div>
      )}

      <h2>What you keep</h2>
      <p className="small muted">
        Skills the judges tagged, credentials, and anything they chose to write about
        you. It fills in after you pitch.
      </p>
      <Link className="btn secondary" href="/portfolio">
        Open your portfolio
      </Link>

      <div style={{ marginTop: "2rem" }}>
        <ParticipantProfile />
      </div>
    </main>
  );
}
