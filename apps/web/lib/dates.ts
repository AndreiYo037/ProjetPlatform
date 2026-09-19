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
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: PROGRAMME_TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(iso));
}

export function formatDayRange(
  start: string | null | undefined,
  end: string | null | undefined,
): string | null {
  const from = formatDay(start);
  const to = formatDay(end);
  if (from && to && from !== to) return `${from} – ${to}`;
  return from ?? to;
}
