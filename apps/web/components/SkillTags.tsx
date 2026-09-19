import ProjetVerifiedStamp from "@/components/ProjetVerifiedStamp";

/**
 * Attested skills as a flat list. One skill that maps onto two capabilities
 * is still one chip — the grouping is a taxonomy concern, not a profile one.
 *
 * Projet-attested and self-declared stay two different chips. Weight only
 * counts repeats inside the same kind: programmes for attested, projects for
 * claimed. The same name on a second project is a heavier outlined tag, not a
 * second one, and never folds into a filled attested pill.
 */

export type TaggedSkill = {
  name: string;
  id?: string;
  attesters?: string[];
  weight: number;
};

function byWeight(a: TaggedSkill, b: TaggedSkill) {
  return b.weight - a.weight || a.name.localeCompare(b.name);
}

export function flattenAttestedSkills(
  groups: { skills: { name: string; attesters: string[]; programme_count?: number }[] }[],
): TaggedSkill[] {
  const byName = new Map<string, TaggedSkill>();
  for (const group of groups) {
    for (const skill of group.skills) {
      const existing = byName.get(skill.name);
      const weight = skill.programme_count ?? 1;
      if (!existing) {
        byName.set(skill.name, {
          name: skill.name,
          attesters: [...skill.attesters],
          weight,
        });
        continue;
      }
      existing.weight = Math.max(existing.weight, weight);
      for (const attester of skill.attesters) {
        if (!existing.attesters?.includes(attester)) existing.attesters?.push(attester);
      }
    }
  }
  return [...byName.values()].sort(byWeight);
}

function projectSkillCounts(
  projects: { visible?: boolean; skills: { name: string; id?: string }[] }[],
) {
  const counts = new Map<string, { name: string; id?: string; weight: number }>();
  for (const project of projects) {
    if (project.visible === false) continue;
    const seen = new Set<string>();
    for (const skill of project.skills) {
      if (seen.has(skill.name)) continue;
      seen.add(skill.name);
      const existing = counts.get(skill.name);
      if (existing) existing.weight += 1;
      else counts.set(skill.name, { name: skill.name, id: skill.id, weight: 1 });
    }
  }
  return counts;
}

/** Attested first (filled), then claims (outlined). Never mix the two. */
export function skillsForProfile(
  groups: { skills: { name: string; attesters: string[]; programme_count?: number }[] }[],
  projects: { visible?: boolean; skills: { name: string; id?: string }[] }[],
) {
  const attested = flattenAttestedSkills(groups);
  const attestedNames = new Set(attested.map((skill) => skill.name));
  const claimed = [...projectSkillCounts(projects).values()]
    .filter((skill) => !attestedNames.has(skill.name))
    .sort(byWeight);

  return { attested, claimed };
}

function skillTitle(
  skill: { attesters?: string[]; weight?: number },
  claimed: boolean,
) {
  if (claimed) {
    return skill.weight && skill.weight > 1
      ? `Added by you on ${skill.weight} projects`
      : "Added by you — not attested on a Projet programme";
  }
  const who = skill.attesters?.length ? skill.attesters.join(", ") : undefined;
  if (skill.weight && skill.weight > 1) {
    return who
      ? `Attested on ${skill.weight} programmes · ${who}`
      : `Attested on ${skill.weight} programmes`;
  }
  return who;
}

/** Repeats read as strength, not a stamped count. Cap at four bars. */
function SkillMeter({ weight }: { weight?: number }) {
  if (weight == null || weight < 2) return null;
  const bars = Math.min(weight, 4);
  return (
    <span className="skill-meter" aria-hidden="true">
      {Array.from({ length: bars }, (_, index) => (
        <span key={index} />
      ))}
    </span>
  );
}

export function SkillTags({
  skills,
  claimed = false,
}: {
  skills: { name: string; id?: string; attesters?: string[]; weight?: number }[];
  claimed?: boolean;
}) {
  if (skills.length === 0) return null;
  return (
    <div className="skill-list">
      {skills.map((skill) => (
        <span
          className={claimed ? "skill claimed" : "skill"}
          key={skill.id ?? skill.name}
          title={skillTitle(skill, claimed)}
        >
          {!claimed && <ProjetVerifiedStamp />}
          {skill.name}
          <SkillMeter weight={skill.weight} />
        </span>
      ))}
    </div>
  );
}

export function SkillsBlock({
  attested,
  claimed,
}: {
  attested: TaggedSkill[];
  claimed: TaggedSkill[];
}) {
  if (attested.length === 0 && claimed.length === 0) return null;
  return (
    <>
      <h2>Skills</h2>
      <SkillTags skills={attested} />
      {claimed.length > 0 && (
        <>
          <p className="small muted">
            {attested.length > 0
              ? "Outlined tags were added by you — not attested on a Projet programme."
              : "Added by you — not attested on a Projet programme."}
          </p>
          <SkillTags skills={claimed} claimed />
        </>
      )}
    </>
  );
}
