"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession, listProgrammes, type ProgrammeOut } from "@/lib/api";

export default function AdminPage() {
  const [programmes, setProgrammes] = useState<ProgrammeOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    getSession()
      .then((actor) => {
        if (!actor) {
          router.replace("/signin?next=/admin");
          return null;
        }
        return listProgrammes();
      })
      .then((rows) => rows && setProgrammes(rows))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load."));
  }, [router]);

  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!programmes) return <main><p className="muted">Loading…</p></main>;

  return (
    <main>
      <h1>Programmes</h1>
      <p className="lede">Every programme you can see, newest first.</p>

      {programmes.length === 0 ? (
        <p className="muted small">No programmes yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Programme</th>
                <th>Role</th>
                <th>Status</th>
                <th>Capacity</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {programmes.map((programme) => (
                <tr key={programme.id}>
                  <td>{programme.title}</td>
                  <td className="muted">{programme.role?.name ?? "—"}</td>
                  <td>
                    <span className={`tag ${programme.status === "open" ? "open" : "closed"}`}>
                      {programme.status}
                    </span>
                  </td>
                  <td className="muted">{programme.capacity ?? "uncapped"}</td>
                  <td>
                    <Link className="btn secondary small" href={`/admin/programmes/${programme.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
