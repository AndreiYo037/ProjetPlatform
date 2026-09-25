"use client";

import { useState } from "react";
import { setPitchSchedule, type ProgrammeDetail } from "@/lib/api";
import { fromDateTimeLocal, formatSlot, toDateTimeLocal } from "@/lib/dates";
import { autosaveLabel, useAutosave } from "@/lib/useAutosave";

export default function PitchingSection({
  programme,
  onSaved,
}: {
  programme: ProgrammeDetail;
  onSaved: () => void;
}) {
  const [startsAt, setStartsAt] = useState(toDateTimeLocal(programme.pitch_starts_at));
  const [duration, setDuration] = useState(
    programme.pitch_duration_minutes ? String(programme.pitch_duration_minutes) : "10",
  );

  const draft = { startsAt, duration };
  const baseline = {
    startsAt: toDateTimeLocal(programme.pitch_starts_at),
    duration: programme.pitch_duration_minutes ? String(programme.pitch_duration_minutes) : "10",
  };

  const { status, error: saveError } = useAutosave(
    draft,
    baseline,
    async (next) => {
      const starts = fromDateTimeLocal(next.startsAt);
      const minutes = Number(next.duration);
      if (!starts || !minutes) return;
      await setPitchSchedule(programme.id, {
        starts_at: starts,
        duration_minutes: minutes,
      });
      onSaved();
    },
  );

  return (
    <div className="panel">
      <strong>Pitching / judging</strong>
      <p className="small muted">
        Date and time the first pitch starts, and minutes per pitch including
        turn-over. One timeslot opens per submission. People who have submitted
        pick first come, first served. Can be set after the challenge is live.
        {autosaveLabel(status) ? ` · ${autosaveLabel(status)}` : ""}
      </p>
      <div className="row" style={{ gap: "1rem" }}>
        <div className="field" style={{ flex: 1 }}>
          <label htmlFor="pitch-start">First pitch</label>
          <input
            id="pitch-start"
            type="datetime-local"
            value={startsAt}
            onChange={(e) => setStartsAt(e.target.value)}
          />
        </div>
        <div className="field" style={{ flex: "0 0 8rem" }}>
          <label htmlFor="pitch-duration">Minutes each</label>
          <input
            id="pitch-duration"
            type="number"
            min={1}
            max={180}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>
      </div>
      {programme.pitch_starts_at && (
        <p className="small muted" style={{ marginBottom: 0 }}>
          First slot {formatSlot(programme.pitch_starts_at)}
          {programme.pitch_duration_minutes
            ? ` · ${programme.pitch_duration_minutes} min each`
            : ""}
        </p>
      )}
      {programme.pitch_meet_link && (
        <p className="small" style={{ margin: "0.5rem 0 0" }}>
          {programme.pitch_meet_link}
        </p>
      )}
      {saveError && <div className="notice bad">{saveError}</div>}
    </div>
  );
}
