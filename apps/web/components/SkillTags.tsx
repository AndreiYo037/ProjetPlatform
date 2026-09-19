import ProjetVerifiedStamp from "@/components/ProjetVerifiedStamp";

/**
 * Attested skills as a flat list. One skill that maps onto two capabilities
 * is still one chip — the grouping is a taxonomy concern, not a profile one.
 *
 * Profile Skills are Projet-attested only. Claims live on a project if they
 * live anywhere; they do not appear here.
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

function skillTitle(skill: { attesters?: string[]; weight?: number }) {
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
}: {
  skills: { name: string; id?: string; attesters?: string[]; weight?: number }[];
}) {
  if (skills.length === 0) return null;
  return (
    <div className="skill-list">
      {skills.map((skill) => (
        <span
          className="skill"
          key={skill.id ?? skill.name}
          title={skillTitle(skill)}
        >
          <ProjetVerifiedStamp />
          {skill.name}
          <SkillMeter weight={skill.weight} />
        </span>
      ))}
    </div>
  );
}

export function SkillsBlock({ attested }: { attested: TaggedSkill[] }) {
  if (attested.length === 0) return null;
  return (
    <>
      <h2>Skills</h2>
      <SkillTags skills={attested} />
    </>
  );
}
