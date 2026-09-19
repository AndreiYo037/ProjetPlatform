"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession, logout, type Actor } from "@/lib/api";

export default function Header() {
  const [actor, setActor] = useState<Actor | null>(null);
  const [checked, setChecked] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Header lives in the root layout and never remounts on client-side
    // navigation, so a bare [] dependency would check the session once at
    // first paint and then never again - sign in from any page and the header
    // keeps showing "Sign in" until a hard reload. Re-checking on every
    // pathname change catches the redirect that follows a sign-in.
    //
    // The probe is unauthenticated, so a signed-out visitor does not get a 401
    // in the console on every page load.
    getSession()
      .then(setActor)
      .catch(() => setActor(null))
      .finally(() => setChecked(true));
  }, [pathname]);

  function signInPathFor(path: string): string {
    if (path.startsWith("/admin")) return "/admin/login";
    if (path.startsWith("/company")) return "/company/signin";
    return "/signin";
  }

  async function signOut() {
    // Return to the sign-in page for the portal you were just in, not always
    // the participant one — signing out of admin should offer admin sign in.
    const destination = actor
      ? actor.actor_type === "platform"
        ? "/admin/login"
        : actor.company_id
          ? "/company/signin"
          : "/signin"
      : signInPathFor(pathname);
    await logout().catch(() => undefined);
    setActor(null);
    router.push(destination);
    router.refresh();
  }

  return (
    <header className="bar">
      {actor ? (
        <span className="brand">Projet</span>
      ) : (
        <Link href="/" className="brand">
          Projet
        </Link>
      )}
      <nav className="bar-links">
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
              <>
                <Link className="btn secondary small" href="/company">
                  Programmes
                </Link>
                <Link className="btn secondary small" href="/company/profile">
                  Profile
                </Link>
              </>
            )}
            {actor.actor_type === "participant" && (
              <>
                <Link className="btn secondary small" href="/home">
                  Home
                </Link>
                <Link className="btn secondary small" href="/challenges">
                  Challenges
                </Link>
                <Link className="btn secondary small" href="/profile">
                  Update profile
                </Link>
                <Link className="btn secondary small" href="/dashboard">
                  My programmes
                </Link>
              </>
            )}
            <button className="secondary" onClick={signOut}>
              Sign out
            </button>
          </>
        ) : (
          <Link className="btn secondary" href={signInPathFor(pathname)}>
            Sign in
          </Link>
        )}
      </nav>
    </header>
  );
}
