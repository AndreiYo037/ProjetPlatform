"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { acceptOffer, declineOffer } from "@/lib/api";

function OfferActions() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<
    { kind: "idle" } | { kind: "accepted"; title: string } | { kind: "declined" }
  >({ kind: "idle" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!token) return <div className="notice bad">That link is missing its token.</div>;

  async function act(which: "accept" | "decline") {
    setBusy(true);
    setError(null);
    try {
      if (which === "accept") {
        const result = await acceptOffer(token!);
        setState({ kind: "accepted", title: result.programme_title });
      } else {
        await declineOffer(token!);
        setState({ kind: "declined" });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "That link is no longer valid.");
    } finally {
      setBusy(false);
    }
  }

  if (state.kind === "accepted") {
    return (
      <div className="notice good">
        <strong>You&rsquo;re confirmed for {state.title}.</strong>
        <p className="small" style={{ margin: "0.5rem 0 0" }}>
          Calendar invites for kickoff, the deadline and your judging session are on their
          way.
        </p>
      </div>
    );
  }

  if (state.kind === "declined") {
    return (
      <div className="notice">
        Thanks for letting us know. Your place has gone to the next person on the list.
      </div>
    );
  }

  return (
    <>
      <p>
        Accepting confirms your place and sends your calendar invites. The offer expires 48
        hours after it was sent.
      </p>
      {error && <div className="notice bad">{error}</div>}
      <div className="row">
        <button onClick={() => act("accept")} disabled={busy}>
          {busy ? "Working…" : "Accept my place"}
        </button>
        <button className="secondary" onClick={() => act("decline")} disabled={busy}>
          Decline
        </button>
      </div>
    </>
  );
}

export default function AcceptPage() {
  return (
    <main className="narrow">
      <h1>Your place</h1>
      <Suspense fallback={null}>
        <OfferActions />
      </Suspense>
    </main>
  );
}
