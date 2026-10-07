"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { checkAccessCode } from "@/lib/api";
import { storeApplyCode } from "@/lib/onsite-apply-code";

/**
 * On-site challenges ask for the room code on the listing page, before the
 * rest of the application form.
 */
export default function OnsiteApplyGate({
  company,
  programme,
  signedIn,
  applyPath,
}: {
  company: string;
  programme: string;
  signedIn: boolean;
  applyPath: string;
}) {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function continueApply(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) {
      setError("Enter the access code from the organisers.");
      return;
    }
    setChecking(true);
    setError(null);
    try {
      const result = await checkAccessCode(company, programme, trimmed);
      if (!result.valid) {
        setError("That code isn't right. Check with the organisers and try again.");
        return;
      }
    } catch {
      setError("Couldn't check that code right now. Try again.");
      return;
    } finally {
      setChecking(false);
    }
    storeApplyCode(company, programme, trimmed);
    if (signedIn) {
      router.push(applyPath);
      return;
    }
    router.push(`/signin?next=${encodeURIComponent(applyPath)}`);
  }

  return (
    <form className="panel" onSubmit={continueApply} style={{ maxWidth: "28rem" }}>
      <strong>Access code</strong>
      <p className="small muted" style={{ margin: "0.35rem 0 0.75rem" }}>
        Ask the organisers in the room for today’s code, then continue to your
        details.
      </p>
      <div className="field" style={{ marginBottom: "0.75rem" }}>
        <label htmlFor="listing-access-code">Code</label>
        <input
          id="listing-access-code"
          type="text"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          value={code}
          onChange={(e) => {
            setCode(e.target.value);
            setError(null);
          }}
        />
      </div>
      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={checking}>
        {checking ? "Checking…" : signedIn ? "Continue to apply" : "Sign in to apply"}
      </button>
    </form>
  );
}
