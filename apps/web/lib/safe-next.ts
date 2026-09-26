/** An in-app path from ?next=. Rejects off-site and protocol-relative targets. */
export function safeNext(value: string | null): string | null {
  if (!value) return null;
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return null;
  return value;
}
