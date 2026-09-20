"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import ActorGateNotice from "@/components/ActorGateNotice";
import { listProgrammes, roleLabel, type ProgrammeOut } from "@/lib/api";
import { useActor } from "@/lib/useActor";

function isPast(programme: ProgrammeOut) {
  const end = programme.submit_deadline_at ?? programme.pitch_at;
  return Boolean(end && new Date(end) <= new Date());
}

function ProgrammeRows({ items }: { items: ProgrammeOut[] }) {
  if (items.length === 0) return null;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Programme</th>
            <th>Company</th>
            <th>Role</th>
            <th>Status</th>
            <th>Capacity</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((programme) => (
            <tr key={programme.id}>
              <td>{programme.title}</td>
              <td className="muted">{programme.company?.name ?? "—"}</td>
              <td className="muted">{roleLabel(programme) || "—"}</td>
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
  );
}

export default function AdminPage() {
  const [programmes, setProgrammes] = useState<ProgrammeOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const gate = useActor("platform");
  const ready = gate.status === "ready";

  useEffect(() => {
    if (!ready) return;
    listProgrammes()
      .then(setProgrammes)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load."));
  }, [ready]);

  const groups = useMemo(() => {
    const rows = programmes ?? [];
    return {
      active: rows.filter(
        (row) => row.status !== "draft" && row.status !== "complete" && !isPast(row),
      ),
      drafts: rows.filter((row) => row.status === "draft"),
      closed: rows.filter((row) => row.status === "complete"),
      past: rows.filter(
        (row) => row.status !== "draft" && row.status !== "complete" && isPast(row),
      ),
    };
  }, [programmes]);

  if (!ready) return <ActorGateNotice gate={gate} />;
  if (error) return <main><div className="notice bad">{error}</div></main>;
  if (!programmes) return <main><p className="muted">Loading…</p></main>;

  return (
    <main>
      <h1>Programmes</h1>
      <p className="lede">Every programme you can see, newest first.</p>

      <h2>Active</h2>
      {groups.active.length === 0 ? (
        <p className="muted small">Nothing running right now.</p>
      ) : (
        <ProgrammeRows items={groups.active} />
      )}

      <h2>Drafts</h2>
      {groups.drafts.length === 0 ? (
        <p className="muted small">No unpublished challenges.</p>
      ) : (
        <ProgrammeRows items={groups.drafts} />
      )}

      <h2>Closed</h2>
      {groups.closed.length === 0 ? (
        <p className="muted small">No closed-out programmes yet.</p>
      ) : (
        <ProgrammeRows items={groups.closed} />
      )}

      {groups.past.length > 0 && (
        <>
          <h2>Past</h2>
          <ProgrammeRows items={groups.past} />
        </>
      )}
    </main>
  );
}
