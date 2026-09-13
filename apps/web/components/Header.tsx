"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession, logout, type Actor } from "@/lib/api";

export default function Header() {
  const [actor, setActor] = useState<Actor | null>(null);
  const [checked, setChecked] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // The probe is unauthenticated, so a signed-out visitor does not get a 401
    // in the console on every page load.
    getSession()
      .then(setActor)
      .catch(() => setActor(null))
      .finally(() => setChecked(true));
  }, []);

  async function signOut() {
    await logout().catch(() => undefined);
    setActor(null);
    router.push("/signin");
    router.refresh();
  }

  return (
    <header className="bar">
      <Link href="/" className="brand">
        Projet
      </Link>
      <div className="row">
        {!checked ? null : actor ? (
          <>
            <span className="small muted">
              {actor.name} · {actor.actor_type.replace("_", " ")}
            </span>
            {actor.actor_type === "platform" && (
              <Link className="btn secondary small" href="/admin">
                Admin
              </Link>
            )}
            {actor.company_id && (
              <Link className="btn secondary small" href="/company">
                Company
              </Link>
            )}
            <button className="secondary" onClick={signOut}>
              Sign out
            </button>
          </>
        ) : (
          <Link className="btn secondary" href="/signin">
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
