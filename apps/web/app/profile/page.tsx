"use client";

import Link from "next/link";
import ActorGateNotice from "@/components/ActorGateNotice";
import ParticipantProfile from "@/components/ParticipantProfile";
import { useActor } from "@/lib/useActor";

/**
 * The details you maintain about yourself — name, emails, CV, school or role.
 *
 * Separate from Home (the portfolio) so editing account fields is never mixed
 * with evidence a judge put there.
 */
export default function UpdateProfilePage() {
  const gate = useActor("participant");
  if (gate.status !== "ready") return <ActorGateNotice gate={gate} />;

  return (
    <main className="narrow">
      <Link href="/home" className="small muted" style={{ textDecoration: "none" }}>
        &larr; Home
      </Link>
      <h1 style={{ marginTop: "0.5rem" }}>Update profile</h1>
      <ParticipantProfile />
    </main>
  );
}
