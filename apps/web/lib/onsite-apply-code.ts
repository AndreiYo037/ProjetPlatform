/** Session hand-off of the on-site room code from the listing page to apply. */

export function applyCodeStorageKey(company: string, programme: string) {
  return `projet:apply-code:${company}/${programme}`;
}

export function storeApplyCode(company: string, programme: string, code: string) {
  sessionStorage.setItem(applyCodeStorageKey(company, programme), code.trim());
}

export function readApplyCode(company: string, programme: string): string {
  return (sessionStorage.getItem(applyCodeStorageKey(company, programme)) ?? "").trim();
}

export function clearApplyCode(company: string, programme: string) {
  sessionStorage.removeItem(applyCodeStorageKey(company, programme));
}
