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

/**
 * An address the browser can fetch, wherever the page was rendered.
 *
 * Unlike `apiUrl`, an `<img src>` is resolved by the browser even on a
 * server-rendered page, so it always goes through the same-origin proxy rather
 * than the server-side base URL. An absolute link the company pasted is left
 * exactly as it is.
 */
export function assetUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  if (/^https?:\/\//.test(path)) return path;
  return `/backend${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * A pasted URL the browser should open off-site.
 *
 * `www.tiktok.com` with no scheme is a relative path to the current page, so
 * on a scoring card it becomes `/judging/www.tiktok.com` and the API treats
 * that as a participant id. Prefix https when nothing else is there.
 */
export function externalHref(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  const trimmed = url.trim();
  if (!trimmed) return undefined;
  if (/^[a-z][a-z0-9+.-]*:/i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("//")) return `https:${trimmed}`;
  return `https://${trimmed}`;
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
export type CompanySummary = Schemas["CompanySummary"];
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
  google_email: string | null;
  organisation: string | null;
  org_type: string | null;
  year_course: string | null;
  job_title: string | null;
  linkedin_url: string | null;
  cv_url: string | null;
};

export const getCompanyHome = (companyId: string) =>
  api.get<CompanyHome>(`/companies/${companyId}/home`);
export const updateCompanyProfile = (
  companyId: string,
  body: { name?: string; your_name?: string; website_url?: string },
) => api.patch<CompanySummary>(`/companies/${companyId}`, body);
export const removeCompanyLogo = (companyId: string) =>
  api.del<CompanySummary>(`/companies/${companyId}/logo`);

/** Multipart, so it goes round the JSON helper. Raster images only: an SVG is
 *  a document that can carry script, and the logo is served unsigned. */
export async function uploadCompanyLogo(
  companyId: string,
  file: File,
): Promise<CompanySummary> {
  const form = new FormData();
  form.set("file", file);
  const response = await fetch(apiUrl(`/companies/${companyId}/logo`), {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? "Could not upload that logo.");
  return body as CompanySummary;
}

export const getMyProfile = () => api.get<PersonProfile>("/me/profile");
export const updateMyProfile = (
  body: Partial<Omit<PersonProfile, "cv_url">>,
) => api.patch<PersonProfile>("/me/profile", body);

export async function uploadMyCv(file: File): Promise<PersonProfile> {
  const form = new FormData();
  form.set("file", file);
  const response = await fetch(apiUrl("/me/profile/cv"), {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? "Could not upload that CV.");
  return body as PersonProfile;
}
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

/** One angle from a drafting run. A run returns two or three of them. */
export type ProblemStatementAngle = {
  id: string;
  batch_id: string | null;
  angle: number;
  title: string;
  context: string;
  question: string;
  outputs: string[];
  grounding: string | null;
  based_on_live_listing: boolean;
  model: string | null;
  /** The angle as plain text, in the shape the brief is written in. */
  rendered: string;
  accepted_at: string | null;
};
/**
 * Research the company and draft two or three angles on the chosen role.
 * Slow by design: it searches the web before it writes anything.
 */
export const draftProblemStatements = (
  id: string,
  body: { company_url?: string | null; admin_notes?: string | null } = {},
) => api.post<ProblemStatementAngle[]>(`/programmes/${id}/problem-statement/draft`, body);
export const listProblemStatementDrafts = (id: string) =>
  api.get<ProblemStatementAngle[]>(`/programmes/${id}/problem-statement/drafts`);
/** Accept an angle, edited or as drafted. Nothing is ever published unread. */
export const setProblemStatement = (
  id: string,
  body: { problem_statement: string; deliverable_spec?: string | null; from_draft_id?: string },
) => api.put<ProgrammeDetail>(`/programmes/${id}/problem-statement`, body);

/**
 * One entry in a programme's data pack.
 *
 * `uploaded` separates the company's own material from the role's seeded
 * public sources: the company can delete what it added, but a seeded source is
 * excluded rather than deleted so it can come back.
 */
export type DataPackResource = {
  id: string;
  label: string;
  url: string | null;
  provenance: string;
  licence: string | null;
  included: boolean;
  confidential: boolean;
  uploaded: boolean;
  verification_status: string;
  last_verified_at: string | null;
};

export const listDataPack = (programmeId: string) =>
  api.get<DataPackResource[]>(`/programmes/${programmeId}/data-pack`);
export const addDataPackResource = (
  programmeId: string,
  body: { label: string; url_or_storage_key?: string | null; licence?: string | null; confidential?: boolean },
) => api.post<DataPackResource>(`/programmes/${programmeId}/data-pack`, body);
export const updateDataPackResource = (
  programmeId: string,
  resourceId: string,
  body: { label?: string; licence?: string | null; included?: boolean; confidential?: boolean },
) => api.patch<DataPackResource>(`/programmes/${programmeId}/data-pack/${resourceId}`, body);
export const deleteDataPackResource = (programmeId: string, resourceId: string) =>
  api.del<void>(`/programmes/${programmeId}/data-pack/${resourceId}`);

/** Multipart, so it bypasses the JSON helper the way the apply form does. */
export async function uploadDataPackFile(
  programmeId: string,
  file: File,
  options: { label?: string; licence?: string; confidential?: boolean } = {},
): Promise<DataPackResource> {
  const form = new FormData();
  form.set("file", file);
  if (options.label) form.set("label", options.label);
  if (options.licence) form.set("licence", options.licence);
  form.set("confidential", options.confidential ? "true" : "false");
  const response = await fetch(apiUrl(`/programmes/${programmeId}/data-pack/upload`), {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? "Could not upload that file.");
  return body as DataPackResource;
}

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

export type SubmissionCard = Schemas["SubmissionCard"];
export type ScoringCard = Schemas["ScoringCard"];

/** Judging day: one card per participant, in the order they pitch. */
export const listSubmissionCards = (programmeId: string) =>
  api.get<SubmissionCard[]>(`/programmes/${programmeId}/submissions`);
export const getScoringCard = (programmeId: string, participantId: string) =>
  api.get<ScoringCard>(`/programmes/${programmeId}/participants/${participantId}/score`);
/** Auto-saving: a judge is watching a pitch, not filling in a form. */
export const updateScoringCard = (
  programmeId: string,
  participantId: string,
  body: {
    ratings?: Record<string, number>;
    would_refer?: string | null;
    skill_ids?: string[];
  },
) =>
  api.patch<ScoringCard>(
    `/programmes/${programmeId}/participants/${participantId}/score`,
    body,
  );

export type Portfolio = Schemas["Portfolio"];
export type PublicProfile = Schemas["PublicProfile"];
export type ProjectEntry = Schemas["ProjectEntryOut"];
export type ProjectSkillOption = Schemas["SkillOptionOut"];
export type TestimonialOut = Schemas["TestimonialOut"];
export type TestimonialDraftOut = Schemas["TestimonialDraftOut"];
export type CloseoutOut = Schemas["CloseoutOut"];

/** What the participant keeps: attested skills, company endorsements, testimonials. */
export const getPortfolio = () => api.get<Portfolio>("/me/portfolio");

/** Case-study entries: verified ones seeded from a programme, self-declared
 * ones the participant writes from scratch. Verified always sorts first. */
export const getProjects = () => api.get<ProjectEntry[]>("/me/projects");

export const createProject = (body: {
  title: string;
  associated_experience?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  ongoing?: boolean;
  description?: string | null;
  artifact_visibility?: string;
}) => api.post<ProjectEntry>("/me/projects", body);

export const updateProject = (
  id: string,
  body: Partial<{
    title: string;
    associated_experience: string | null;
    started_at: string | null;
    ended_at: string | null;
    ongoing: boolean;
    description: string | null;
    artifact_visibility: string;
    visible: boolean;
  }>,
) => api.patch<ProjectEntry>(`/me/projects/${id}`, body);

export const deleteProject = (id: string) => api.del<void>(`/me/projects/${id}`);

export const addProjectLink = (id: string, body: { url: string; label?: string | null }) =>
  api.post<ProjectEntry>(`/me/projects/${id}/links`, body);

/** For work that does not live at a URL. The file is stored privately and
 * comes back as a signed, expiring link. */
export const uploadProjectFile = (id: string, file: File, label?: string) => {
  const form = new FormData();
  form.append("file", file);
  if (label) form.append("label", label);
  return api.post<ProjectEntry>(`/me/projects/${id}/files`, form);
};

export const removeProjectLink = (id: string, linkId: string) =>
  api.del<ProjectEntry>(`/me/projects/${id}/links/${linkId}`);

/** Replaces the entry's claimed (unverified) skills wholesale — the list
 * sent is the list kept. Allowed on verified work too: these are claims,
 * not judge attestations. */
export const setProjectSkills = (id: string, skillIds: string[]) =>
  api.put<ProjectEntry>(`/me/projects/${id}/skills`, { skill_ids: skillIds });

/** The whole taxonomy. A self-declared project has no role to rank against,
 * so nothing is suggested and everything is reached by typing. */
export const getProjectSkillOptions = () =>
  api.get<ProjectSkillOption[]>("/me/skills/options");

/** The public page — FR-1201. No session; a bare fetch answers it the same
 * way the browser does. Null on a 404, since "no profile at that handle" is
 * an ordinary outcome here, not an error to surface as one. */
export async function getPublicProfile(handle: string): Promise<PublicProfile | null> {
  try {
    return await api.get<PublicProfile>(`/p/${encodeURIComponent(handle)}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export const getTestimonial = (programmeId: string, participantId: string) =>
  api.get<TestimonialOut | null>(
    `/programmes/${programmeId}/participants/${participantId}/testimonial`,
  );
export const writeTestimonial = (
  programmeId: string,
  participantId: string,
  body: { body: string; publish?: boolean },
) =>
  api.put<TestimonialOut>(
    `/programmes/${programmeId}/participants/${participantId}/testimonial`,
    body,
  );
/** Fills the box from endorsed skills and the brief. Does not save or publish. */
export const draftTestimonial = (programmeId: string, participantId: string) =>
  api.post<TestimonialDraftOut>(
    `/programmes/${programmeId}/participants/${participantId}/testimonial/draft`,
  );
/** Turns the evening's scores into what participants keep. Safe to repeat. */
export const closeProgramme = (programmeId: string) =>
  api.post<CloseoutOut>(`/programmes/${programmeId}/close`);

function withProgramme(path: string, programmeId?: string): string {
  if (!programmeId) return path;
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}programme_id=${encodeURIComponent(programmeId)}`;
}

export const getDashboard = (programmeId?: string) =>
  api.get<Dashboard>(withProgramme("/me/dashboard", programmeId));
export const putSubmissionLink = (slot: string, driveUrl: string, programmeId?: string) =>
  api.put<SubmissionOut>(withProgramme("/me/submission/link", programmeId), {
    slot,
    drive_url: driveUrl,
  });
export const deleteSubmissionSlot = (slot: string, programmeId?: string) =>
  api.del<SubmissionOut>(withProgramme(`/me/submission/link/${slot}`, programmeId));
export const recheckSubmission = (programmeId?: string) =>
  api.post<SubmissionOut>(withProgramme("/me/submission/recheck", programmeId));

/** Multipart, so it goes round the JSON helper. A slot filled this way is
 *  already the frozen copy — there is no accessibility check to run. */
export async function uploadSubmissionFile(
  slot: string,
  file: File,
  programmeId?: string,
): Promise<SubmissionOut> {
  const form = new FormData();
  form.set("slot", slot);
  form.set("file", file);
  const response = await fetch(apiUrl(withProgramme("/me/submission/upload", programmeId)), {
    method: "PUT",
    body: form,
    credentials: "include",
  });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? "Could not upload that file.");
  return body as SubmissionOut;
}
export const markThreadRead = (threadId: string, acknowledge = false, programmeId?: string) =>
  api.post<void>(
    withProgramme(`/me/threads/${threadId}/read?acknowledge=${acknowledge}`, programmeId),
  );

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

/** Multipart, so it goes round the JSON helper. A file can ride along with the
 *  message or be the message — "here is the dataset" needs no words. */
export async function postAnnouncement(
  programmeId: string,
  input: { body?: string; file?: File | null; requiresAck?: boolean },
): Promise<ThreadOut> {
  const form = new FormData();
  form.set("body", input.body ?? "");
  form.set("requires_ack", String(Boolean(input.requiresAck)));
  if (input.file) form.set("file", input.file);
  const response = await fetch(apiUrl(`/programmes/${programmeId}/announcements`), {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? "Could not post that.");
  return body as ThreadOut;
}

export async function attachToThread(threadId: string, file: File): Promise<ThreadOut> {
  const form = new FormData();
  form.set("file", file);
  const response = await fetch(apiUrl(`/threads/${threadId}/attachments`), {
    method: "POST",
    body: form,
    credentials: "include",
  });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, body?.detail ?? "Could not attach that.");
  return body as ThreadOut;
}

export const acceptOffer = (token: string) =>
  api.post<{ participant_id: string; programme_title: string; message: string }>("/accept", {
    token,
  });
export const declineOffer = (token: string) =>
  api.post<{ declined: boolean; promoted: number }>("/decline", { token });
