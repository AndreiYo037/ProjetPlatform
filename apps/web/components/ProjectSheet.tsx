"use client";

import { useEffect, useState } from "react";
import SkillPicker, { type SkillChoice } from "@/components/SkillPicker";
import {
  addProjectLink,
  createProject,
  deleteProject,
  getProjectSkillOptions,
  removeProjectLink,
  setProjectSkills,
  updateProject,
  type ProjectEntry,
} from "@/lib/api";

/**
 * One case study, open for editing.
 *
 * The rule the whole sheet is built around: on a verified entry the narrative
 * is theirs and the facts are not. So the title, organisation and dates render
 * as plain text with a note saying where they came from, and only the four
 * narrative fields, the artifact consent and the visibility toggle are inputs.
 * The API refuses the rest anyway — this just means they never get to try and
 * lose their typing to a 400.
 *
 * Skills are the same boundary in the other direction. A self-declared entry
 * gets the drawer; a verified one does not, because what it demonstrated is
 * for a judge to attest, not for the participant to claim.
 */

const KINDS = [
  { value: "hackathon", label: "Hackathon" },
  { value: "internship", label: "Internship" },
  { value: "freelance", label: "Freelance" },
  { value: "competition", label: "Competition" },
  { value: "independent", label: "Independent" },
];

const LINK_KINDS = [
  { value: "github", label: "GitHub" },
  { value: "demo", label: "Demo" },
  { value: "video", label: "Video" },
  { value: "deck", label: "Deck" },
  { value: "doc", label: "Doc" },
  { value: "brief", label: "Brief" },
];

const VISIBILITY = [
  { value: "private", label: "Nobody", hint: "The work stays off the public page." },
  { value: "link_only", label: "Anyone with the profile link", hint: "Shown on your page." },
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

  const [kind, setKind] = useState(entry?.kind ?? "hackathon");
  const [title, setTitle] = useState(entry?.title ?? "");
  const [organisation, setOrganisation] = useState(entry?.organisation_name ?? "");
  const [problem, setProblem] = useState(entry?.problem ?? "");
  const [approach, setApproach] = useState(entry?.approach ?? "");
  const [outcome, setOutcome] = useState(entry?.outcome ?? "");
  const [contribution, setContribution] = useState<string[]>(entry?.contribution ?? []);
  const [visibility, setVisibility] = useState(entry?.artifact_visibility ?? "private");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const body = {
        problem: problem.trim() || null,
        approach: approach.trim() || null,
        outcome: outcome.trim() || null,
        contribution: contribution.filter((line) => line.trim()),
        artifact_visibility: visibility,
      };
      if (creating) {
        await createProject({
          ...body,
          kind,
          title: title.trim(),
          organisation_name: organisation.trim() || null,
        });
      } else if (verified) {
        // The facts are the platform's; only the narrative goes up.
        await updateProject(entry.id, body);
      } else {
        await updateProject(entry.id, {
          ...body,
          kind,
          title: title.trim(),
          organisation_name: organisation.trim() || null,
        });
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
                ? "Verified. The company, the dates and the brief came from the programme — yours to describe, not to restate."
                : "Self-declared. Shown after verified work, always."}
            </p>
          </div>
          <button className="secondary" onClick={onClose} disabled={busy}>
            Close
          </button>
        </div>

        {error && <div className="notice bad">{error}</div>}

        {verified && entry ? (
          <div className="facts">
            <p className="small muted" style={{ marginTop: 0 }}>
              {entry.organisation_name}
              {entry.started_at && ` · ${entry.started_at}`}
              {entry.ended_at && ` – ${entry.ended_at}`}
            </p>
          </div>
        ) : (
          <>
            <div className="field">
              <label htmlFor="project-title">Title</label>
              <input
                id="project-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What the work was"
              />
            </div>
            <div className="field">
              <label htmlFor="project-kind">Kind</label>
              <select id="project-kind" value={kind} onChange={(e) => setKind(e.target.value)}>
                {KINDS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="project-org">Organisation</label>
              <input
                id="project-org"
                type="text"
                value={organisation}
                onChange={(e) => setOrganisation(e.target.value)}
                placeholder="Who it was for, if anyone"
              />
            </div>
          </>
        )}

        <div className="field">
          <label htmlFor="project-problem">Problem</label>
          <textarea
            id="project-problem"
            rows={2}
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            placeholder="What was actually wrong."
          />
        </div>
        <div className="field">
          <label htmlFor="project-approach">Approach</label>
          <textarea
            id="project-approach"
            rows={2}
            value={approach}
            onChange={(e) => setApproach(e.target.value)}
            placeholder="What you did about it."
          />
        </div>

        <ContributionEditor lines={contribution} onChange={setContribution} disabled={busy} />

        <div className="field">
          <label htmlFor="project-outcome">Outcome</label>
          <textarea
            id="project-outcome"
            rows={2}
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
            placeholder="What changed because of it."
          />
        </div>

        <div className="field">
          <label htmlFor="project-visibility">Who can see the links</label>
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

        {!creating && <LinksEditor entry={entry} onSaved={onSaved} />}
        {!creating && !verified && <SkillDrawer entry={entry} onSaved={onSaved} />}
        {!creating && verified && (
          <p className="small muted">
            Skills on a verified project come from the judges who watched it, and appear under
            your capabilities.
          </p>
        )}

        <div className="row" style={{ gap: "0.75rem", marginTop: "1rem" }}>
          <button onClick={save} disabled={busy || (!creating ? false : !title.trim())}>
            {creating ? "Add project" : "Save"}
          </button>
          {!creating && !verified && (
            <button className="secondary" onClick={remove} disabled={busy}>
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/** The bullets under "what I did". A list, not a paragraph, because the thing
 * a reader scans for is the specific contribution. */
function ContributionEditor({
  lines,
  onChange,
  disabled,
}: {
  lines: string[];
  onChange: (lines: string[]) => void;
  disabled?: boolean;
}) {
  const [draft, setDraft] = useState("");

  function add() {
    if (!draft.trim()) return;
    onChange([...lines, draft.trim()]);
    setDraft("");
  }

  return (
    <div className="field">
      <label htmlFor="project-contribution">What you did</label>
      {lines.length > 0 && (
        <ul style={{ marginTop: 0 }}>
          {lines.map((line, index) => (
            <li key={index}>
              {line}{" "}
              <button
                className="secondary small"
                disabled={disabled}
                onClick={() => onChange(lines.filter((_, i) => i !== index))}
                style={{ padding: "0.1rem 0.4rem" }}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="row" style={{ gap: "0.5rem" }}>
        <input
          id="project-contribution"
          type="text"
          style={{ flex: 1 }}
          value={draft}
          disabled={disabled}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="One thing you did"
        />
        <button className="secondary" onClick={add} disabled={disabled || !draft.trim()}>
          Add
        </button>
      </div>
    </div>
  );
}

/** Links save immediately rather than on the sheet's Save, because they are
 * their own rows on the server and batching them would mean reconciling a
 * client-side list against server ids for no benefit. */
function LinksEditor({ entry, onSaved }: { entry: ProjectEntry; onSaved: () => void }) {
  const [links, setLinks] = useState(entry.links);
  const [kind, setKind] = useState("github");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    if (!url.trim()) return;
    setBusy(true);
    try {
      const updated = await addProjectLink(entry.id, { kind, url: url.trim() });
      setLinks(updated.links);
      setUrl("");
      onSaved();
    } finally {
      setBusy(false);
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
      <label htmlFor="link-url">Links</label>
      {links.length > 0 && (
        <div className="row" style={{ flexWrap: "wrap", gap: "0.4rem", marginBottom: "0.5rem" }}>
          {links.map((link) => (
            <button
              key={link.id}
              className="secondary"
              disabled={busy}
              onClick={() => remove(link.id)}
              title="Remove this link"
            >
              {link.label ?? link.kind} ✕
            </button>
          ))}
        </div>
      )}
      <div className="row" style={{ gap: "0.5rem" }}>
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          disabled={busy}
          style={{ width: "auto" }}
        >
          {LINK_KINDS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <input
          id="link-url"
          type="url"
          style={{ flex: 1 }}
          value={url}
          disabled={busy}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://"
        />
        <button className="secondary" onClick={add} disabled={busy || !url.trim()}>
          Add
        </button>
      </div>
    </div>
  );
}

/** Self-declared skills, in their own bordered well so a claim never sits on
 * the same visual plane as an attested capability. */
function SkillDrawer({ entry, onSaved }: { entry: ProjectEntry; onSaved: () => void }) {
  const [options, setOptions] = useState<SkillChoice[]>([]);
  const [selected, setSelected] = useState<string[]>(entry.skills.map((s) => s.id));
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getProjectSkillOptions()
      .then((rows) =>
        // Nothing is "suggested" here: a self-declared project has no role
        // template to rank against, so everything is reached by typing.
        setOptions(rows.map((row) => ({ ...row, id: String(row.id), suggested: false }))),
      )
      .catch(() => setOptions([]));
  }, []);

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
      <strong className="small">Skills you used</strong>
      <p className="small muted" style={{ marginTop: "0.2rem" }}>
        Your own claim, and shown as one. Skills a judge watched you use are attested separately
        and carry their name.
      </p>
      <SkillPicker
        options={options}
        selectedIds={selected}
        disabled={busy}
        onToggle={toggle}
      />
    </div>
  );
}
