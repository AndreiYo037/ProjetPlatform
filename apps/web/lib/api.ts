/**
 * API client.
 *
 * Types come from the FastAPI OpenAPI schema via `pnpm gen:api`, so a backend
 * change that breaks a screen fails typecheck rather than production.
 */

import type { components, paths } from "./api-types";

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

type Schemas = components["schemas"];

export type Actor = Schemas["ActorResponse"];
export type CompanyHome = Schemas["CompanyHome"];
export type ProgrammeOut = Schemas["ProgrammeOut"];
export type ProgrammeDetail = Schemas["ProgrammeDetail"];
export type PublicListing = Schemas["PublicListing"];
export type ApplicationOut = Schemas["ApplicationOut"];
export type ApplicationDetail = Schemas["ApplicationDetail"];
export type ClusterOut = Schemas["ClusterOut"];
export type RoleImplications = Schemas["RoleImplications"];
export type CriterionOut = Schemas["CriterionOut"];
export type SeatsOut = Schemas["SeatsOut"];
export type Dashboard = Schemas["Dashboard"];
export type SubmissionOut = Schemas["SubmissionOut"];
export type ThreadOut = Schemas["ThreadOut"];
export type ThreadSummary = Schemas["ThreadSummary"];
export type Readiness = paths["/readyz"]["get"]["responses"]["200"]["content"]["application/json"];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers:
      init?.body instanceof FormData
        ? init.headers
        : { "Content-Type": "application/json", ...init?.headers },
    // Sessions are cookie-borne (FR-012), so every request carries them.
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `${init?.method ?? "GET"} ${path} failed`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* the body was not JSON; the generic message stands */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

// -- endpoints used by more than one screen ----------------------------------

export type ActorTypeParam = "participant" | "company_user" | "platform";

export const getSession = () => api.get<Actor | null>("/auth/session");
export const login = (email: string, password: string, actorType: ActorTypeParam) =>
  api.post<Actor>("/auth/login", { email, password, actor_type: actorType });
export const logout = () => api.post<{ signed_out: boolean }>("/auth/logout");
export const requestPasswordReset = (email: string, actorType: ActorTypeParam) =>
  api.post<{ sent: boolean; message: string }>("/auth/password/forgot", {
    email,
    actor_type: actorType,
  });
export const confirmPasswordReset = (token: string, password: string) =>
  api.post<Actor>("/auth/password/reset", { token, password });
export const setInitialPassword = (token: string, password: string) =>
  api.post<Actor>("/auth/password/set", { token, password });

export const getCompanyHome = (companyId: string) =>
  api.get<CompanyHome>(`/companies/${companyId}/home`);
export const getProgramme = (id: string) => api.get<ProgrammeDetail>(`/programmes/${id}`);
export const listProgrammes = () => api.get<ProgrammeOut[]>("/programmes");

export const getListing = (company: string, programme: string) =>
  api.get<PublicListing>(`/public/x/${company}/${programme}`);

export const listApplications = (programmeId: string, status?: string) =>
  api.get<ApplicationOut[]>(
    `/programmes/${programmeId}/applications${status ? `?status=${status}` : ""}`,
  );
export const getApplication = (programmeId: string, id: string) =>
  api.get<ApplicationDetail>(`/programmes/${programmeId}/applications/${id}`);
export const scoreApplication = (
  programmeId: string,
  id: string,
  scores: Record<string, number | null>,
) => api.patch<ApplicationOut>(`/programmes/${programmeId}/applications/${id}/score`, scores);
export const disposition = (
  programmeId: string,
  ids: string[],
  action: "offer" | "waitlist" | "reject",
  feedback?: string,
) =>
  api.post<{ updated: number; skipped: string[] }>(
    `/programmes/${programmeId}/applications/disposition`,
    { application_ids: ids, action, feedback },
  );
export const getSeats = (programmeId: string) =>
  api.get<SeatsOut>(`/programmes/${programmeId}/seats`);

export const getDashboard = () => api.get<Dashboard>("/me/dashboard");
export const putSubmissionLink = (slot: string, driveUrl: string) =>
  api.put<SubmissionOut>("/me/submission/link", { slot, drive_url: driveUrl });
export const recheckSubmission = () => api.post<SubmissionOut>("/me/submission/recheck");
export const markThreadRead = (threadId: string, acknowledge = false) =>
  api.post<void>(`/me/threads/${threadId}/read?acknowledge=${acknowledge}`);

export const listThreads = (programmeId: string) =>
  api.get<ThreadOut[]>(`/programmes/${programmeId}/threads`);
export const getThread = (threadId: string) => api.get<ThreadOut>(`/threads/${threadId}`);
export const postReply = (threadId: string, body: string) =>
  api.post<ThreadOut>(`/threads/${threadId}/posts`, { body });
export const createThread = (
  programmeId: string,
  payload: { type: string; title: string; body: string; is_anonymous?: boolean; requires_ack?: boolean },
) => api.post<{ thread: ThreadOut; warning: string | null }>(`/programmes/${programmeId}/threads`, payload);
export const findSimilarThreads = (programmeId: string, title: string) =>
  api.get<{ id: string; title: string; status: string }[]>(
    `/programmes/${programmeId}/threads/similar?title=${encodeURIComponent(title)}`,
  );

export const acceptOffer = (token: string) =>
  api.post<{ participant_id: string; programme_title: string; message: string }>("/accept", {
    token,
  });
export const declineOffer = (token: string) =>
  api.post<{ declined: boolean; promoted: number }>("/decline", { token });
