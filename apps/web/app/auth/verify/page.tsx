"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { verifyMagicLink } from "@/lib/api";

function Verifier() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const attempted = useRef(false);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("That link is missing its token.");
      return;
    }
    // The token is single-use, so React's development double-invoke would burn
    // it and show "already used" on a perfectly good link.
    if (attempted.current) return;
    attempted.current = true;

    verifyMagicLink(token)
      .then((result) => {
        // FR-013 — land on what they clicked through for, signed in.
        const destination =
          result.next ?? (result.actor.company_id ? "/company" : "/");
        router.replace(destination);
        router.refresh();
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Sign-in failed."));
  }, [params, router]);

  if (error) {
    return (
      <>
        <div className="notice bad">{error}</div>
        <a className="btn" href="/signin">
          Request a new link
        </a>
      </>
    );
  }
  return <p className="muted">Signing you in…</p>;
}

export default function VerifyPage() {
  return (
    <main className="narrow">
      <h1>Signing in</h1>
      <Suspense fallback={<p className="muted">Signing you in…</p>}>
        <Verifier />
      </Suspense>
    </main>
  );
}
