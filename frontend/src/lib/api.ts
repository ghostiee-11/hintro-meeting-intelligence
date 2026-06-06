import type {
  ActionItem,
  Analytics,
  AnalysisResult,
  ApiError,
  ApiSuccess,
  AuthUser,
  MeetingDetail,
  MeetingSummary,
  Paginated,
  SearchHit,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "hintro_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiClientError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const body = (await res.json().catch(() => null)) as
    | ApiSuccess<T>
    | ApiError
    | null;

  if (!res.ok || !body || body.success === false) {
    const err = (body as ApiError | null)?.error;
    throw new ApiClientError(
      err?.code || "ERROR",
      err?.message || `Request failed (${res.status})`,
      res.status,
    );
  }
  return (body as ApiSuccess<T>).data;
}

export const api = {
  // Auth
  register: (email: string, name: string, password: string) =>
    request<{ token: string; user: AuthUser }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, name, password }),
    }),
  login: (email: string, password: string) =>
    request<{ token: string; user: AuthUser }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<AuthUser>("/api/auth/me"),

  // Meetings
  listMeetings: (params: Record<string, string | number | undefined>) =>
    request<Paginated<MeetingSummary>>(`/api/meetings${query(params)}`),
  getMeeting: (id: string) => request<MeetingDetail>(`/api/meetings/${id}`),
  createMeeting: (payload: unknown) =>
    request<MeetingDetail>("/api/meetings", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  analyze: (id: string) =>
    request<AnalysisResult>(`/api/meetings/${id}/analyze`, { method: "POST" }),

  // Action items
  listActionItems: (params: Record<string, string | number | undefined>) =>
    request<Paginated<ActionItem>>(`/api/action-items${query(params)}`),
  overdue: (params: Record<string, string | number | undefined> = {}) =>
    request<Paginated<ActionItem>>(`/api/action-items/overdue${query(params)}`),
  createActionItem: (payload: unknown) =>
    request<ActionItem>("/api/action-items", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateStatus: (id: string, status: string) =>
    request<ActionItem>(`/api/action-items/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // Standout
  analytics: () => request<Analytics>("/api/analytics"),
  search: (q: string) => request<SearchHit[]>(`/api/search${query({ q })}`),
};

function query(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== "" && v !== null,
  );
  if (entries.length === 0) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of entries) sp.set(k, String(v));
  return `?${sp.toString()}`;
}

/** Builds the SSE URL for streaming analysis (EventSource cannot send headers). */
export function analyzeStreamUrl(meetingId: string): string {
  const token = getToken();
  return `${API_URL}/api/meetings/${meetingId}/analyze/stream?token=${encodeURIComponent(token || "")}`;
}
