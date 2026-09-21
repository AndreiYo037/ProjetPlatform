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

  /* A nav where every item is a bordered button reads as five things to do.
     Destinations are quiet links marked by where you are; only sign-in — the
     one thing a signed-out visitor is here to do — stays a button. */
  function navLink(href: string, label: string) {
    return (
      <Link
        key={href}
        className="navlink"
        href={href}
        aria-current={
          pathname === href || pathname.startsWith(`${href}/`) ? "page" : undefined
        }
      >
        {label}
      </Link>
    );
  }

  return (
    <header className="bar">
      <div className="bar-inner">
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
              {actor.actor_type === "platform" && navLink("/admin", "Admin")}
              {actor.company_id && (
                <>
                  {navLink("/company", "Programmes")}
                  {navLink("/company/profile", "Profile")}
                </>
              )}
              {actor.actor_type === "participant" && (
                <>
                  {navLink("/home", "Home")}
                  {navLink("/challenges", "Challenges")}
                  {navLink("/dashboard", "My programmes")}
                  {navLink("/profile", "Profile")}
                </>
              )}
              <span className="bar-who">
                <span className="avatar small" aria-hidden="true">
                  {initials(actor.name)}
                </span>
                <span className="bar-who-name">{actor.name}</span>
              </span>
              <button className="ghost small" onClick={signOut}>
                Sign out
              </button>
            </>
          ) : (
            <Link className="btn secondary" href={signInPathFor(pathname)}>
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

/** Two letters is enough to recognise yourself and never overflows the chip. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1][0] ?? "") : "";
  return (first + last).toUpperCase();
}
