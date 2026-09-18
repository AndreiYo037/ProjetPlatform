"use client";

import { useMemo, useRef, useState } from "react";

/**
 * Tagging skills without scrolling a list of hundreds.
 *
 * Two things make this usable in the ninety seconds between pitches. The list
 * opens on the skills this role was designed to demonstrate, so the common
 * case needs no typing at all. And typing matches loosely — token order,
 * partial words, and typos all still land — because a judge who types
 * "dashbord desin" means Dashboard design and being told "no results" is the
 * fastest way to get a worse tag or none.
 *
 * Matching is lexical, not embedding-based: token prefixes, substrings, a
 * small synonym table for the abbreviations people actually type, and bounded
 * edit distance for typos. That covers what a judge types at speed without a
 * model in the request path.
 */

export type SkillChoice = {
  id: string;
  name: string;
  type: string;
  suggested: boolean;
};

/** What people type instead of what the taxonomy calls it. */
const SYNONYMS: Record<string, string[]> = {
  viz: ["visualisation", "visualization"],
  dataviz: ["visualisation", "visualization"],
  comms: ["communication"],
  comm: ["communication"],
  stats: ["statistics", "statistical"],
  stat: ["statistics", "statistical"],
  db: ["database"],
  ux: ["experience"],
  ui: ["interface"],
  qa: ["testing", "quality"],
  pm: ["product", "project"],
  ops: ["operations", "operational"],
  fin: ["financial", "finance"],
  model: ["modelling", "modeling"],
  modelling: ["modeling"],
  modeling: ["modelling"],
  a11y: ["accessibility"],
  docs: ["documentation"],
  spec: ["specification"],
  req: ["requirements"],
  kpi: ["kpi", "metric"],
  sql: ["sql", "query"],
};

function normalise(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function tokens(value: string) {
  return normalise(value).split(" ").filter(Boolean);
}

function expand(token: string) {
  return [token, ...(SYNONYMS[token] ?? [])];
}

/** Levenshtein, abandoned as soon as it cannot come in under the budget. */
function within(a: string, b: string, budget: number) {
  if (Math.abs(a.length - b.length) > budget) return false;
  let previous = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const current = [i];
    let best = i;
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      const value = Math.min(
        previous[j] + 1,
        current[j - 1] + 1,
        previous[j - 1] + cost,
      );
      current.push(value);
      best = Math.min(best, value);
    }
    if (best > budget) return false;
    previous = current;
  }
  return previous[b.length] <= budget;
}

/**
 * A stand-in for stemming: "prioritise" and "prioritisation" share nine
 * characters before diverging, and nobody typing the verb means a different
 * skill from the noun. Requires a long enough shared prefix to avoid
 * "data" pulling in "database".
 */
function sameStem(a: string, b: string) {
  const limit = Math.min(a.length, b.length);
  let shared = 0;
  while (shared < limit && a[shared] === b[shared]) shared += 1;
  return shared >= 5 && shared >= limit * 0.7;
}

function isSubsequence(needle: string, haystack: string) {
  let index = 0;
  for (const character of haystack) {
    if (character === needle[index]) index += 1;
    if (index === needle.length) return true;
  }
  return index === needle.length;
}

/** 0 means no match. Higher is a better match. */
export function matchScore(name: string, query: string): number {
  const q = normalise(query);
  if (!q) return 1;
  const haystack = normalise(name);

  if (haystack === q) return 1000;
  if (haystack.startsWith(q)) return 900;
  if (haystack.includes(q)) return 800;

  const queryTokens = tokens(q);
  const nameTokens = tokens(haystack);

  const every = (test: (needle: string, candidate: string) => boolean) =>
    queryTokens.every((token) =>
      expand(token).some((variant) =>
        nameTokens.some((candidate) => test(variant, candidate)),
      ),
    );

  // "design dashboard" and "dash des" both mean Dashboard design.
  if (every((needle, candidate) => candidate.startsWith(needle))) return 700;
  if (every((needle, candidate) => candidate.includes(needle))) return 600;
  // "prioritise" for Prioritisation, "model" for modelling.
  if (every(sameStem)) return 500;
  // "dashbord", "visualisaton" — one or two characters out.
  if (every((needle, candidate) => within(needle, candidate, needle.length <= 4 ? 1 : 2))) {
    return 400;
  }
  if (isSubsequence(q.replace(/ /g, ""), haystack.replace(/ /g, ""))) return 200;
  return 0;
}

const SHOWN = 10;

export default function SkillPicker({
  options,
  selectedIds,
  disabled,
  onToggle,
  /** False where there is no role to rank against — a self-declared project
   * has no template, so promising "ranked for this role" would be a lie. */
  ranked = true,
}: {
  options: SkillChoice[];
  selectedIds: string[];
  disabled?: boolean;
  onToggle: (id: string) => void;
  ranked?: boolean;
}) {
  const [query, setQuery] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const selected = new Set(selectedIds);

  const chosen = useMemo(
    () => selectedIds.map((id) => options.find((o) => o.id === id)).filter(Boolean) as SkillChoice[],
    [selectedIds, options],
  );

  const matches = useMemo(() => {
    const pool = options.filter((option) => !selected.has(option.id));
    if (!query.trim()) {
      // Nothing typed: the role's own skills are the whole point of the list.
      return { rows: pool.filter((o) => o.suggested), total: pool.length, browsing: true };
    }
    const scored = pool
      .map((option) => ({ option, score: matchScore(option.name, query) }))
      .filter((entry) => entry.score > 0)
      // A tie goes to the skill this role was built to demonstrate.
      .sort(
        (a, b) =>
          b.score - a.score ||
          Number(b.option.suggested) - Number(a.option.suggested) ||
          a.option.name.localeCompare(b.option.name),
      );
    return { rows: scored.slice(0, SHOWN).map((e) => e.option), total: scored.length, browsing: false };
  }, [options, query, selectedIds]);

  return (
    <div>
      {chosen.length > 0 && (
        <div className="row" style={{ flexWrap: "wrap", gap: "0.4rem", marginBottom: "0.6rem" }}>
          {chosen.map((skill) => (
            <button
              key={skill.id}
              disabled={disabled}
              onClick={() => onToggle(skill.id)}
              title="Remove this tag"
            >
              {skill.name} ✕
            </button>
          ))}
        </div>
      )}

      <div className="field" style={{ marginBottom: "0.5rem" }}>
        <input
          ref={input}
          type="search"
          placeholder={`Search ${options.length} skills`}
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && matches.rows.length > 0) {
              e.preventDefault();
              onToggle(matches.rows[0].id);
              setQuery("");
            }
          }}
        />
      </div>

      <p className="small muted" style={{ margin: "0 0 0.5rem" }}>
        {matches.browsing
          ? ranked
            ? `Ranked for this role. Type to search all ${options.length}.`
            : `Type to search ${options.length} skills.`
          : matches.total === 0
            ? "Nothing matches that."
            : `${matches.total} match${matches.total === 1 ? "" : "es"}${
                matches.total > SHOWN ? `, showing ${SHOWN}` : ""
              }. Enter picks the first.`}
      </p>

      <div className="row" style={{ flexWrap: "wrap", gap: "0.4rem" }}>
        {matches.rows.map((skill) => (
          <button
            key={skill.id}
            className="secondary"
            disabled={disabled}
            onClick={() => {
              onToggle(skill.id);
              setQuery("");
              input.current?.focus();
            }}
          >
            {skill.name}
            {skill.suggested && !matches.browsing && (
              <span className="tag" style={{ marginLeft: "0.4rem" }}>
                this role
              </span>
            )}
          </button>
        ))}
      </div>

      {matches.browsing && matches.rows.length === 0 && ranked && (
        <p className="small muted" style={{ margin: 0 }}>
          This role has no ranked skills yet — search above.
        </p>
      )}
    </div>
  );
}
