"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { signInWithAdminCode } from "@/lib/api";

/**
 * The admin-only shared-code shortcut (disabled server-side unless
 * PROJET_ADMIN_ACCESS_CODE is configured — a 404 from the API here just means
 * the deploy has not turned it on).
 *
 * Deliberately not offered on the participant or company portals: it signs
 * in as platform admin only, so it has no business appearing anywhere else.
 */
export default function AdminCodeSignIn() {
  const router = useRouter();
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
      const next = new URLSearchParams(window.location.search).get("next");
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
      <p className="auth-alt">
        <button type="button" className="auth-text" onClick={() => setOpen(true)}>
          Use an access code instead
        </button>
      </p>
    );
  }

  return (
    <form className="auth-code" onSubmit={submit} noValidate>
      {error ? (
        <div className="auth-status" role="alert">
          {error}
        </div>
      ) : null}
      <div className="field">
        <label htmlFor="admin-code">Access code</label>
        <input
          id="admin-code"
          type="password"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          autoComplete="off"
          autoFocus
        />
      </div>
      <button type="submit" className="btn btn-primary auth-submit" disabled={busy || !code}>
        {busy ? "Checking…" : "Sign in with code"}
      </button>
    </form>
  );
}
