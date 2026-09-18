"use client";

import { useEffect, useRef, useState } from "react";
import SkillPicker, { type SkillChoice } from "@/components/SkillPicker";
import {
  addProjectLink,
  createProject,
  deleteProject,
  getProjectSkillOptions,
  removeProjectLink,
  setProjectSkills,
  updateProject,
  uploadProjectFile,
  type ProjectEntry,
} from "@/lib/api";

/**
 * One project, open for editing.
 *
 * The rule the sheet is built around: on a verified project the description is
 * theirs and the facts are not. So the title, associated experience and dates
 * render as plain text with a note saying where they came from, and only the
 * description, the consent setting and the visibility toggle are inputs. The
 * API refuses the rest anyway — this just means they never get to try and lose
 * their typing to an error.
 *
 * Skills are the same boundary the other way. A self-declared project gets the
 * drawer; a verified one does not, because what it demonstrated is for a judge
 * to attest, not for the participant to claim.
 */

const VISIBILITY = [
  { value: "private", label: "Nobody", hint: "The work stays off your public page." },
  { value: "link_only", label: "Anyone with your profile link", hint: "Shown on your page." },
  { value: "public", label: "Everyone", hint: "Shown on your page." },
];

export default function ProjectSheet({
  entry,
  onClose,
  onSaved,
}: {
  /** Null opens the sheet in create mode for a new self-declared project. */
  entry: ProjectEntry | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const creating = entry === null;
  const verified = entry?.verified ?? false;

  const [title, setTitle] = useState(entry?.title ?? "");
  const [experience, setExperience] = useState(entry?.associated_experience ?? "");
  const [startedAt, setStartedAt] = useState(entry?.started_at ?? "");
  const [endedAt, setEndedAt] = useState(entry?.ended_at ?? "");
  const [ongoing, setOngoing] = useState(entry?.ongoing ?? false);
  const [description, setDescription] = useState(entry?.description ?? "");
  const [visibility, setVisibility] = useState(entry?.artifact_visibility ?? "private");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const shared = {
        description: description.trim() || null,
        artifact_visibility: visibility,
      };
      const own = {
        title: title.trim(),
        associated_experience: experience.trim() || null,
        started_at: startedAt || null,
        ended_at: ongoing ? null : endedAt || null,
        ongoing,
      };
      if (creating) {
        await createProject({ ...shared, ...own });
      } else if (verified) {
        // The facts are the platform's; only the description goes up.
        await updateProject(entry.id, shared);
      } else {
        await updateProject(entry.id, { ...shared, ...own });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that.");
      setBusy(false);
    }
  }

  async function remove() {
    if (!entry || verified) return;
    setBusy(true);
    try {
      await deleteProject(entry.id);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete that.");
      setBusy(false);
    }
  }

  return (
    <div className="sheet-backdrop" onClick={onClose} role="presentation">
      <div
        className="sheet"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={creating ? "Add a project" : title}
      >
        <div className="sheet-head">
          <div>
            <h2>{creating ? "Add a project" : title}</h2>
            <p className="small muted" style={{ margin: 0 }}>
              {verified
                ? "Verified. The company and the dates came from the programme — yours to describe, not to restate."
                : "Self-declared. Shown after verified work, always."}
            </p>
          </div>
          <button className="secondary" onClick={onClose} disabled={busy}>
            Close
          </button>
        </div>

        {error && <div className="notice bad">{error}</div>}

        {verified && entry ? (
          <p className="small muted">
            {entry.associated_experience}
            {entry.started_at && ` · ${entry.started_at}`}
            {entry.ongoing ? " – ongoing" : entry.ended_at && ` – ${entry.ended_at}`}
          </p>
        ) : (
          <>
            <div className="field">
              <label htmlFor="project-title">Project name</label>
              <input
                id="project-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="A clear title describing the work"
              />
            </div>
            <div className="field">
              <label htmlFor="project-experience">Associated experience</label>
              <input
                id="project-experience"
                type="text"
                value={experience}
                onChange={(e) => setExperience(e.target.value)}
                placeholder="The job, course or event this sat under"
              />
            </div>
            <div className="row" style={{ gap: "0.75rem", alignItems: "flex-end" }}>
              <div className="field" style={{ flex: 1 }}>
                <label htmlFor="project-start">Started</label>
                <input
                  id="project-start"
                  type="date"
                  value={startedAt}
                  onChange={(e) => setStartedAt(e.target.value)}
                />
              </div>
              <div className="field" style={{ flex: 1 }}>
                <label htmlFor="project-end">Ended</label>
                <input
                  id="project-end"
                  type="date"
                  value={ongoing ? "" : endedAt}
                  disabled={ongoing}
                  onChange={(e) => setEndedAt(e.target.value)}
                />
              </div>
            </div>
            <div className="check">
              <input
                id="project-ongoing"
                type="checkbox"
                checked={ongoing}
                onChange={(e) => setOngoing(e.target.checked)}
              />
              <label htmlFor="project-ongoing">Still working on it</label>
            </div>
          </>
        )}

        <div className="field">
          <label htmlFor="project-description">Description</label>
          <textarea
            id="project-description"
            rows={6}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="The problem you solved, what you actually did, and what changed because of it."
          />
        </div>

        {!creating && <SkillDrawer entry={entry} verified={verified} onSaved={onSaved} />}

        {!creating && <LinksEditor entry={entry} onSaved={onSaved} />}

        <div className="field">
          <label htmlFor="project-visibility">Who can see the links and files</label>
          <select
            id="project-visibility"
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
          >
            {VISIBILITY.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <div className="hint">
            {VISIBILITY.find((o) => o.value === visibility)?.hint} Set per project — consent
            given to one company for one week is not consent to a public page.
          </div>
        </div>

        <div className="row" style={{ gap: "0.75rem", marginTop: "1rem" }}>
          <button onClick={save} disabled={busy || (creating && !title.trim())}>
            {creating ? "Add project" : "Save"}
          </button>
          {!creating && !verified && (
            <button className="secondary" onClick={remove} disabled={busy}>
              Delete
            </button>
          )}
        </div>
        {creating && (
          <p className="small muted">
            Links, files and skills can be added once the project is saved.
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * URLs and uploads, saving immediately rather than on the sheet's Save.
 *
 * They are their own rows on the server, so batching them would mean
 * reconciling a client-side list against server ids for no benefit.
 */
function LinksEditor({ entry, onSaved }: { entry: ProjectEntry; onSaved: () => void }) {
  const [links, setLinks] = useState(entry.links);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const filePicker = useRef<HTMLInputElement>(null);

  async function addUrl() {
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await addProjectLink(entry.id, { url: url.trim() });
      setLinks(updated.links);
      setUrl("");
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add that link.");
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    try {
      const updated = await uploadProjectFile(entry.id, file);
      setLinks(updated.links);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload that file.");
    } finally {
      setBusy(false);
      if (filePicker.current) filePicker.current.value = "";
    }
  }

  async function remove(linkId: string) {
    setBusy(true);
    try {
      const updated = await removeProjectLink(entry.id, linkId);
      setLinks(updated.links);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="field">
      <label htmlFor="link-url">Project URL or file</label>
      {links.length > 0 && (
        <div className="row" style={{ flexWrap: "wrap", gap: "0.4rem", marginBottom: "0.5rem" }}>
          {links.map((link) => (
            <button
              key={link.id}
              className="secondary"
              disabled={busy}
              onClick={() => remove(link.id)}
              title="Remove this"
            >
              {link.filename ? "📎 " : ""}
              {link.label ?? link.filename ?? link.url} ✕
            </button>
          ))}
        </div>
      )}
      {error && <div className="notice bad">{error}</div>}
      <div className="row" style={{ gap: "0.5rem" }}>
        <input
          id="link-url"
          type="url"
          style={{ flex: 1 }}
          value={url}
          disabled={busy}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addUrl();
            }
          }}
          placeholder="https://"
        />
        <button className="secondary" onClick={addUrl} disabled={busy || !url.trim()}>
          Add
        </button>
      </div>
      <input
        ref={filePicker}
        type="file"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload(file);
        }}
      />
      <button
        className="secondary"
        disabled={busy}
        onClick={() => filePicker.current?.click()}
        style={{ marginTop: "0.5rem" }}
      >
        Attach a file
      </button>
      <div className="hint">
        For work that does not live at a URL. Up to 20MB — PDF, image, document or zip.
      </div>
    </div>
  );
}

/** Self-declared skills, in their own bordered well so a claim never sits on
 * the same visual plane as an attested capability. */
function SkillDrawer({
  entry,
  verified,
  onSaved,
}: {
  entry: ProjectEntry;
  verified: boolean;
  onSaved: () => void;
}) {
  const [options, setOptions] = useState<SkillChoice[]>([]);
  const [selected, setSelected] = useState<string[]>(entry.skills.map((s) => String(s.id)));
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (verified) return;
    getProjectSkillOptions()
      .then((rows) =>
        // Nothing is "suggested" here: a self-declared project has no role
        // template to rank against, so everything is reached by typing.
        setOptions(rows.map((row) => ({ ...row, id: String(row.id), suggested: false }))),
      )
      .catch(() => setOptions([]));
  }, [verified]);

  if (verified) {
    return (
      <p className="small muted">
        Skills on a verified project come from the judges who watched it, and appear under your
        capabilities.
      </p>
    );
  }

  async function toggle(id: string) {
    const next = selected.includes(id)
      ? selected.filter((existing) => existing !== id)
      : [...selected, id];
    setSelected(next);
    setBusy(true);
    try {
      await setProjectSkills(entry.id, next);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="drawer">
      <strong className="small">Skills</strong>
      <p className="small muted" style={{ marginTop: "0.2rem" }}>
        Your own claim, and shown as one. Skills a judge watched you use are attested separately
        and carry their name.
      </p>
      <SkillPicker
        options={options}
        selectedIds={selected}
        disabled={busy}
        onToggle={toggle}
        ranked={false}
      />
    </div>
  );
}
