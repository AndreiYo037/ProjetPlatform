import ProjetVerifiedStamp from "@/components/ProjetVerifiedStamp";

/**
 * Attested skills as a flat list — one chip per skill, never grouped onto a
 * capability axis. The API already returns them this way (`attested_skills`
 * in profile.py): a skill that maps to two capabilities used to render under
 * both headings, and one judge's single tag read as two endorsements.
 */

export type TaggedSkill = {
  name: string;
  id?: string;
  attesters?: string[];
  weight: number;
};

/** Portfolio.skills / PublicProfile.skills, as sent by the API, in the shape
 * SkillTags renders. The API already sorts by strength and dedupes. */
export function toTaggedSkills(
  skills: { name: string; attesters: string[]; programme_count: number }[],
): TaggedSkill[] {
  return skills.map((skill) => ({
    name: skill.name,
    attesters: skill.attesters,
    weight: skill.programme_count,
  }));
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
