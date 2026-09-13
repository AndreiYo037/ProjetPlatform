/**
 * API client.
 *
 * Types come from the FastAPI OpenAPI schema via `pnpm gen:api`, so a backend
 * change that breaks a screen fails typecheck rather than production.
 */

import type { components, paths } from "./api-types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * Browser calls go through the Next same-origin proxy (`/backend`) so the
 * session cookie is first-party. `localhost` and `127.0.0.1` are different
 * sites; a Lax cookie set by one is invisible to the other, which is why
 * admin sign-in accepted the code and then bounced back to login.
 */
export function apiUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  if (typeof window !== "undefined") return `/backend${suffix}`;
  return `${API_BASE_URL}${suffix}`;
}

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
export type PublicListingSummary = Schemas["PublicListingSummary"];
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
  const response = await fetch(apiUrl(path), {
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
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        const messages = body.detail
          .map((item: { msg?: string }) => item?.msg)
          .filter((msg: unknown): msg is string => typeof msg === "string");
        if (messages.length) detail = messages.join(" ");
      }
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
export const signup = (input: {
  actorType: Exclude<ActorTypeParam, "platform">;
  email: string;
  password: string;
}) =>
  api.post<Actor>("/auth/signup", {
    actor_type: input.actorType,
    email: input.email,
    password: input.password,
  });
export const signInWithAdminCode = (code: string) => api.post<Actor>("/auth/admin-code", { code });
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

export type PersonProfile = {
  name: string;
  email: string;
  organisation: string | null;
  year_course: string | null;
  job_title: string | null;
  phone: string | null;
};

export const getCompanyHome = (companyId: string) =>
  api.get<CompanyHome>(`/companies/${companyId}/home`);
export const updateCompanyProfile = (
  companyId: string,
  body: { name?: string; your_name?: string },
) => api.patch<CompanyHome["company"]>(`/companies/${companyId}`, body);
export const getMyProfile = () => api.get<PersonProfile>("/me/profile");
export const updateMyProfile = (body: Partial<Omit<PersonProfile, "email">>) =>
  api.patch<PersonProfile>("/me/profile", body);
export const getProgramme = (id: string) => api.get<ProgrammeDetail>(`/programmes/${id}`);
export const listProgrammes = () => api.get<ProgrammeOut[]>("/programmes");

export type ClusterGroup = { cluster: string; roles: RoleSummary[] };
export type RoleSummary = { id: string; name: string; slug: string; cluster: string; aliases: string[] };
export const getRoleClusters = () => api.get<ClusterGroup[]>("/roles/clusters");
export const getRoleImplications = (roleId: string) =>
  api.get<RoleImplications>(`/roles/${roleId}/implications`);

// The submission deadline and the pitch day are not sent: both derive from
// kickoff on the server, so there is nothing here to keep in step.
export type CreateProgrammeInput = {
  role_id: string;
  title: string;
  slug: string;
  delivery_mode?: string;
  capacity?: number | null;
  applications_open_at?: string | null;
  applications_close_at?: string | null;
  /** Kickoff. Must be one of the Wednesdays getKickoffDays returns. */
  start_at?: string | null;
  problem_statement?: string | null;
  deliverable_spec?: string | null;
  winners_count?: number;
};
export type UpdateProgrammeInput = Partial<CreateProgrammeInput> & {
  brief_url?: string | null;
};
export const createProgramme = (data: CreateProgrammeInput) =>
  api.post<ProgrammeDetail>("/programmes", data);
export const updateProgramme = (id: string, data: UpdateProgrammeInput) =>
  api.patch<ProgrammeDetail>(`/programmes/${id}`, data);

/** One choosable week: pick the kickoff, the other two dates follow. */
export type KickoffOption = {
  kickoff_at: string;
  submit_deadline_at: string;
  pitch_at: string;
};
/** The Wednesdays a company may kick off on, so nobody types a rejected date. */
export const getKickoffDays = () => api.get<KickoffOption[]>("/programmes/kickoff-days");

export type PublicationCheck = { ready: boolean; problems: string[] };
export const getPublicationCheck = (id: string) =>
  api.get<PublicationCheck>(`/programmes/${id}/publication-check`);
export const publishProgramme = (id: string) =>
  api.post<ProgrammeDetail>(`/programmes/${id}/publish`);

export const getListing = (company: string, programme: string) =>
  api.get<PublicListing>(`/public/x/${company}/${programme}`);

export const listCompanyChallenges = (company: string) =>
  api.get<PublicListingSummary[]>(`/public/x/${company}`);

export type ChallengeDirectoryParams = {
  roleSlug?: string;
  cluster?: string;
  limit?: number;
  offset?: number;
};
export const listChallenges = (params: ChallengeDirectoryParams = {}) => {
  const query = new URLSearchParams();
  if (params.roleSlug) query.set("role_slug", params.roleSlug);
  if (params.cluster) query.set("cluster", params.cluster);
  if (params.limit != null) query.set("limit", String(params.limit));
  if (params.offset != null) query.set("offset", String(params.offset));
  const qs = query.toString();
  return api.get<PublicListingSummary[]>(`/public/challenges${qs ? `?${qs}` : ""}`);
};

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
