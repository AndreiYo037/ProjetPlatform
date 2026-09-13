"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { signInWithAdminCode } from "@/lib/api";

/**
 * The admin-only shared-code shortcut (disabled server-side unless
 * PROJET_ADMIN_ACCESS_CODE is configured — a 404 from the API here just means
 * the deploy has not turned it on).
 *
 * Deliberately not offered on the participant or company portals: it signs
 * in as platform admin only, so it has no business appearing anywhere else.
 */
function CodeForm() {
  const params = useSearchParams();
  const router = useRouter();
  const next = params.get("next") ?? undefined;
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signInWithAdminCode(code);
      router.push(next ?? "/admin");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That code is not valid.");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <p className="small" style={{ marginTop: "1.5rem" }}>
        <button type="button" className="secondary small" onClick={() => setOpen(true)}>
          Use an access code instead
        </button>
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="panel" style={{ marginTop: "1.5rem" }}>
      <div className="field">
        <label htmlFor="admin-code">Access code</label>
        <input
          id="admin-code"
          type="password"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          autoComplete="off"
          autoFocus
        />
      </div>
      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={busy || !code}>
        {busy ? "Checking…" : "Sign in with code"}
      </button>
    </form>
  );
}

export default function AdminCodeSignIn() {
  return (
    <Suspense fallback={null}>
      <CodeForm />
    </Suspense>
  );
}
