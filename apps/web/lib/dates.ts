/** Programme dates are calendar days in Singapore; times of day are fixed. */
const PROGRAMME_TZ = "Asia/Singapore";

export function toDateInput(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: PROGRAMME_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

/** Naive midnight for the API, which pins start to 00:00 and end to 23:59. */
export function fromDateInput(value: string): string | null {
  if (!value) return null;
  return `${value}T00:00:00`;
}

export function formatDay(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const day = new Intl.DateTimeFormat("en-GB", {
    timeZone: PROGRAMME_TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
  return `${day} SGT`;
}

export function formatDayRange(
  start: string | null | undefined,
  end: string | null | undefined,
): string | null {
  const from = formatDay(start);
  const to = formatDay(end);
  if (from && to && from !== to) return `${from.replace(/ SGT$/, "")} – ${to}`;
  return from ?? to;
}

function sgtParts(iso: string) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: PROGRAMME_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return {
    year: get("year"),
    month: get("month"),
    day: get("day"),
    hour: get("hour"),
    minute: get("minute"),
  };
}

/** datetime-local value in Singapore time. */
export function toDateTimeLocal(iso: string | null | undefined): string {
  if (!iso) return "";
  const { year, month, day, hour, minute } = sgtParts(iso);
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

/** HH:MM in Singapore time, for a time picker on a known date. */
export function toTimeInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const { hour, minute } = sgtParts(iso);
  return `${hour}:${minute}`;
}

/** Interpret a datetime-local value as Singapore time. */
export function fromDateTimeLocal(value: string): string | null {
  if (!value) return null;
  return `${value}:00+08:00`;
}

/** Time on a calendar day, as Singapore time. */
export function fromTimeOnDate(dateValue: string, timeValue: string): string | null {
  if (!dateValue || !timeValue) return null;
  return `${dateValue}T${timeValue}:00+08:00`;
}

export function formatSlot(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const when = new Intl.DateTimeFormat("en-GB", {
    timeZone: PROGRAMME_TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(iso));
  return `${when} SGT`;
}

export function formatSlotTime(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const clock = new Intl.DateTimeFormat("en-GB", {
    timeZone: PROGRAMME_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(iso));
  return `${clock} SGT`;
}

/** A calendar day plus a fixed clock, always Singapore. */
export function formatDayClock(
  iso: string | null | undefined,
  time: string,
): string | null {
  const day = formatDay(iso);
  if (!day) return null;
  return `${day.replace(/ SGT$/, "")} · ${time} SGT`;
}
