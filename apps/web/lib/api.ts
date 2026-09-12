/**
 * Thin API client.
 *
 * Types come from the FastAPI OpenAPI schema via `pnpm gen:api`, so the
 * contract cannot drift silently: a backend change that breaks the frontend
 * fails typecheck rather than production.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    // Magic-link sessions are cookie-borne (FR-012), so every request carries them.
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(response.status, `${init?.method ?? "GET"} ${path} failed`);
  }
  return (await response.json()) as T;
}

export type OutboxHealth = {
  pending: number;
  done: number;
  failed: number;
  stuck: number;
};

export type Readiness = {
  status: "ok" | "degraded";
  checks: {
    database: string;
    roles_seeded?: number;
    outbox?: OutboxHealth;
  };
};

export const getReadiness = () => apiFetch<Readiness>("/readyz");
