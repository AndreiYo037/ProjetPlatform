"use client";

import Link from "next/link";
import type { ActorGate } from "@/lib/useActor";

/**
 * What a guarded screen renders while the session is still unknown, and when
 * the session turns out to belong to the wrong audience.
 *
 * Returns null once the gate is open, so a page can render it above its own
 * content without branching twice. Signing out is the header's job — offering
 * it a second time here would just be two buttons for one action.
 */
export default function ActorGateNotice({ gate }: { gate: ActorGate }) {
  if (gate.status === "ready") return null;

  if (gate.status === "wrong-account") {
    return (
      <main>
        <div className="notice bad">
          <p>{gate.message}</p>
        </div>
        <p className="small">
          <Link href={gate.home}>Go to your own home</Link>
        </p>
      </main>
    );
  }

  // Loading and signed-out look the same on purpose: the redirect is already
  // in flight, and naming it would flash a message nobody has time to read.
  return (
    <main>
      <p className="muted">Loading…</p>
    </main>
  );
}
