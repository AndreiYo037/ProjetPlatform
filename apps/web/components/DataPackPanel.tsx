"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  addDataPackResource,
  deleteDataPackResource,
  listDataPack,
  updateDataPackResource,
  uploadDataPackFile,
  type DataPackResource,
} from "@/lib/api";

/**
 * What the participants get to work with, and what the company keeps back.
 *
 * The role's public sources arrive already in the list, so the company starts
 * by curating rather than by filling in a blank form. Clearing one is a toggle,
 * not a delete: the source belongs to the role, and a company that changes its
 * mind should not have to go and find the URL again.
 *
 * Nothing here reaches an applicant. The pack is released once a seat is
 * accepted, which is what makes it safe to ask for real data at all.
 */
export default function DataPackPanel({ programmeId }: { programmeId: string }) {
  const [resources, setResources] = useState<DataPackResource[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    listDataPack(programmeId)
      .then(setResources)
      .catch(() => setResources([]));
  }, [programmeId]);

  useEffect(load, [load]);

  async function run(work: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await work();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the data pack.");
    } finally {
      setBusy(false);
    }
  }

  const seeded = resources.filter((r) => !r.uploaded);
  const own = resources.filter((r) => r.uploaded);
  const confidentialCount = resources.filter((r) => r.included && r.confidential).length;

  return (
    <>
      <h2>Data pack</h2>
      <p className="small muted">
        What participants get on day one. Public sources for the role are already
        here; clear the ones that do not fit and add whatever of your own you are
        willing to share. Nobody outside the programme sees any of it, and the
        public listing names the public sources only.
      </p>

      {error && <div className="notice bad">{error}</div>}
      {confidentialCount > 0 && (
        <div className="notice warn">
          {confidentialCount === 1 ? "One resource is" : `${confidentialCount} resources are`}{" "}
          marked confidential, so participants acknowledge the terms before the pack opens.
        </div>
      )}

      <div className="panel">
        <strong>Public sources for this role</strong>
        {seeded.length === 0 ? (
          <p className="small muted">The role has no seeded sources yet.</p>
        ) : (
          seeded.map((resource) => (
            <div className="check" key={resource.id}>
              <input
                id={`include-${resource.id}`}
                type="checkbox"
                checked={resource.included}
                disabled={busy}
                onChange={(e) =>
                  run(() =>
                    updateDataPackResource(programmeId, resource.id, {
                      included: e.target.checked,
                    }),
                  )
                }
              />
              <label htmlFor={`include-${resource.id}`}>
                {resource.url ? (
                  <a href={resource.url} target="_blank" rel="noreferrer">
                    {resource.label}
                  </a>
                ) : (
                  resource.label
                )}
                {resource.licence && <span className="small muted"> · {resource.licence}</span>}
                {resource.verification_status !== "verified" && (
                  <span className="tag"> {resource.verification_status}</span>
                )}
              </label>
            </div>
          ))
        )}
      </div>

      <div className="panel">
        <strong>Your own data and resources</strong>
        {own.length === 0 ? (
          <p className="small muted">
            Nothing added yet. A challenge built on your real data gets you work you
            can actually use.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>In the pack</th>
                  <th>Confidential</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {own.map((resource) => (
                  <tr key={resource.id}>
                    <td>
                      {resource.url ? (
                        <a href={resource.url} target="_blank" rel="noreferrer">
                          {resource.label}
                        </a>
                      ) : (
                        resource.label
                      )}
                      {resource.licence && (
                        <div className="small muted">{resource.licence}</div>
                      )}
                    </td>
                    <td>
                      <input
                        aria-label={`Include ${resource.label}`}
                        type="checkbox"
                        checked={resource.included}
                        disabled={busy}
                        onChange={(e) =>
                          run(() =>
                            updateDataPackResource(programmeId, resource.id, {
                              included: e.target.checked,
                            }),
                          )
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label={`Mark ${resource.label} confidential`}
                        type="checkbox"
                        checked={resource.confidential}
                        disabled={busy}
                        onChange={(e) =>
                          run(() =>
                            updateDataPackResource(programmeId, resource.id, {
                              confidential: e.target.checked,
                            }),
                          )
                        }
                      />
                    </td>
                    <td>
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() =>
                          run(() => deleteDataPackResource(programmeId, resource.id))
                        }
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <AddResource programmeId={programmeId} busy={busy} onAdded={load} onError={setError} />
      </div>
    </>
  );
}

/**
 * A link or a file, side by side.
 *
 * An upload is the better answer for anything sensitive: a shared Drive link is
 * a permission the company has to keep right for a week, whereas an upload is a
 * copy served through an expiring signature and pulled when the pack closes.
 */
function AddResource({
  programmeId,
  busy,
  onAdded,
  onError,
}: {
  programmeId: string;
  busy: boolean;
  onAdded: () => void;
  onError: (message: string | null) => void;
}) {
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");
  const [licence, setLicence] = useState("");
  const [confidential, setConfidential] = useState(false);
  const [chosen, setChosen] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function reset() {
    setLabel("");
    setUrl("");
    setLicence("");
    setConfidential(false);
    setChosen(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function submit(work: () => Promise<unknown>) {
    setSaving(true);
    onError(null);
    try {
      await work();
      reset();
      onAdded();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not add that resource.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="field">
        <label htmlFor="dp-label">What it is</label>
        <input
          id="dp-label"
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Anonymised churn export, Q3 2026"
        />
      </div>
      <div className="field">
        <label htmlFor="dp-licence">Terms of use (optional)</label>
        <input
          id="dp-licence"
          type="text"
          value={licence}
          onChange={(e) => setLicence(e.target.value)}
          placeholder="For this programme only, not to be redistributed"
        />
      </div>
      <div className="check">
        <input
          id="dp-confidential"
          type="checkbox"
          checked={confidential}
          onChange={(e) => setConfidential(e.target.checked)}
        />
        <label htmlFor="dp-confidential">
          Confidential. Participants acknowledge the terms before the pack opens, and
          it is never named on the public listing.
        </label>
      </div>

      <div className="field">
        <label htmlFor="dp-url">Link to it</label>
        <input
          id="dp-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://…"
        />
        <button
          className="secondary"
          disabled={busy || saving || !label.trim() || !url.trim()}
          onClick={() =>
            submit(() =>
              addDataPackResource(programmeId, {
                label: label.trim(),
                url_or_storage_key: url.trim(),
                licence: licence.trim() || null,
                confidential,
              }),
            )
          }
        >
          Add link
        </button>
      </div>

      <div className="field">
        <label htmlFor="dp-file">Or upload the file</label>
        <input
          id="dp-file"
          type="file"
          ref={fileInput}
          disabled={busy || saving}
          onChange={(e) => setChosen(e.target.files?.[0] ?? null)}
        />
        <div className="hint">
          CSV, Excel, PDF, Word, slides, images or a zip, up to 100MB. Served through
          an expiring link, so a forwarded URL stops working.
        </div>
        <button
          className="secondary"
          disabled={busy || saving || !chosen}
          onClick={() => {
            if (!chosen) {
              onError("Choose a file first.");
              return;
            }
            submit(() =>
              uploadDataPackFile(programmeId, chosen, {
                label: label.trim() || undefined,
                licence: licence.trim() || undefined,
                confidential,
              }),
            );
          }}
        >
          {saving ? "Uploading…" : chosen ? `Upload ${chosen.name}` : "Upload"}
        </button>
      </div>
    </>
  );
}
