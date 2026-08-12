const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CSRF_COOKIE = "ss_csrf";

/** Auth paths that must not trigger refresh-on-401 (avoid loops / public flows). */
const NO_REFRESH_PATHS = new Set([
  "/auth/login",
  "/auth/refresh",
  "/auth/logout",
  "/auth/logout-all",
  "/auth/2fa/verify",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/accept-invite",
]);

let csrfToken = "";
let refreshInFlight: Promise<boolean> | null = null;
/** App Router navigate — registered by AuthProvider so 401 is a soft client transition. */
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

export function setCsrfToken(token: string | null | undefined) {
  if (token) csrfToken = token;
}

export function getCsrfToken() {
  return ensureCsrfHeader();
}

function readCsrfFromCookie(): string {
  if (typeof document === "undefined") return "";
  const parts = document.cookie.split("; ");
  for (const part of parts) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    if (part.slice(0, eq) === CSRF_COOKIE) {
      try {
        return decodeURIComponent(part.slice(eq + 1));
      } catch {
        return part.slice(eq + 1);
      }
    }
  }
  return "";
}

/** Memory token, else readable `ss_csrf` double-submit cookie (survives hard refresh). */
function ensureCsrfHeader(): string {
  if (!csrfToken) {
    const fromCookie = readCsrfFromCookie();
    if (fromCookie) csrfToken = fromCookie;
  }
  return csrfToken;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function parseError(res: Response) {
  let detail = "Request failed";
  try {
    const body = await res.json();
    detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* ignore */
  }
  throw new ApiError(detail, res.status);
}

async function refreshSession() {
  if (!refreshInFlight) {
    const csrf = ensureCsrfHeader();
    // #region agent log
    fetch('http://127.0.0.1:7734/ingest/641bf763-dc10-4f7a-825b-05bd4821faeb',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'1d8612'},body:JSON.stringify({sessionId:'1d8612',runId:'post-fix',hypothesisId:'B',location:'api.ts:refreshSession',message:'refresh attempt',data:{hasMemoryCsrf:Boolean(csrf),csrfLen:csrf.length,fromCookie:Boolean(readCsrfFromCookie())},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    refreshInFlight = fetch(`${API}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: csrf ? { "X-CSRF-Token": csrf } : {},
    })
      .then(async (r) => {
        // #region agent log
        fetch('http://127.0.0.1:7734/ingest/641bf763-dc10-4f7a-825b-05bd4821faeb',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'1d8612'},body:JSON.stringify({sessionId:'1d8612',runId:'post-fix',hypothesisId:'B',location:'api.ts:refreshSession:result',message:'refresh response',data:{status:r.status,ok:r.ok},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        if (!r.ok) return false;
        const body = await r.json().catch(() => ({}));
        if (body?.csrf_token) setCsrfToken(body.csrf_token);
        return true;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const method = (options.method || "GET").toUpperCase();
  const csrf = ensureCsrfHeader();
  if (method !== "GET" && method !== "HEAD" && csrf) {
    headers.set("X-CSRF-Token", csrf);
  }

  const res = await fetch(`${API}/api/v1${path}`, {
    ...options,
    credentials: "include",
    headers,
  });

  // #region agent log
  const canRefresh = !NO_REFRESH_PATHS.has(path);
  if (res.status === 401 || res.status === 403) {
    fetch('http://127.0.0.1:7734/ingest/641bf763-dc10-4f7a-825b-05bd4821faeb',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'1d8612'},body:JSON.stringify({sessionId:'1d8612',runId:'post-fix',hypothesisId:'A',location:'api.ts:api',message:'auth-sensitive response',data:{path,method,status:res.status,canRefresh,hasCsrf:Boolean(ensureCsrfHeader())},timestamp:Date.now()})}).catch(()=>{});
  }
  // #endregion

  if (res.status === 401 && canRefresh) {
    const ok = await refreshSession();
    // #region agent log
    fetch('http://127.0.0.1:7734/ingest/641bf763-dc10-4f7a-825b-05bd4821faeb',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'1d8612'},body:JSON.stringify({sessionId:'1d8612',runId:'post-fix',hypothesisId:'A',location:'api.ts:api:401-refresh',message:'refresh outcome',data:{path,ok},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (ok) {
      const retryCsrf = ensureCsrfHeader();
      if (retryCsrf) headers.set("X-CSRF-Token", retryCsrf);
      const retry = await fetch(`${API}/api/v1${path}`, {
        ...options,
        credentials: "include",
        headers,
      });
      if (retry.status === 204) return undefined as T;
      if (!retry.ok) await parseError(retry);
      const data = (await retry.json()) as T & { csrf_token?: string };
      if (data && typeof data === "object" && "csrf_token" in data) setCsrfToken(data.csrf_token);
      return data;
    }
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      onUnauthorized?.();
    }
    throw new ApiError("Not authenticated", 401);
  }

  if (!res.ok) await parseError(res);
  if (res.status === 204) return undefined as T;
  const data = (await res.json()) as T & { csrf_token?: string };
  if (data && typeof data === "object" && "csrf_token" in data) setCsrfToken(data.csrf_token);
  return data;
}

export const endpoints = {
  me: () => api<{ user: AuthUser; csrf_token?: string }>("/auth/me"),
  login: (email: string, password: string) =>
    api<LoginResult>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  verify2fa: (temp_token: string, code: string) =>
    api<LoginResult>("/auth/2fa/verify", {
      method: "POST",
      body: JSON.stringify({ temp_token, code }),
    }),
  setup2fa: () => api<{ secret: string; otpauth_url: string; enabled: boolean }>("/auth/2fa/setup", { method: "POST" }),
  enable2fa: (code: string) =>
    api<LoginResult>("/auth/2fa/enable", { method: "POST", body: JSON.stringify({ code }) }),
  disable2fa: (code: string) =>
    api<LoginResult>("/auth/2fa/disable", { method: "POST", body: JSON.stringify({ code }) }),
  authProviders: () => api<{ google: boolean; totp_available: boolean }>("/auth/providers"),
  googleStartUrl: () => `${API}/api/v1/auth/google/start`,
  logout: () => api<{ message: string }>("/auth/logout", { method: "POST" }),
  logoutAll: () => api<{ message: string }>("/auth/logout-all", { method: "POST" }),
  dashboard: () => api<Dashboard>("/dashboard"),
  desk: () => api<Desk>("/desk"),
  clients: (opts?: string | { q?: string; archived?: boolean }) => {
    const params =
      typeof opts === "string" ? { q: opts } : opts || {};
    const sp = new URLSearchParams();
    if (params.q) sp.set("q", params.q);
    if (params.archived) sp.set("archived", "true");
    const qs = sp.toString();
    return api<Client[]>(`/clients${qs ? `?${qs}` : ""}`);
  },
  client: (id: string) => api<Client>(`/clients/${id}`),
  createClient: (data: Partial<Client> & { business_name: string }) =>
    api<Client>("/clients", { method: "POST", body: JSON.stringify(data) }),
  updateClient: (id: string, data: Partial<Client>) =>
    api<Client>(`/clients/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  archiveClient: (id: string) => api<void>(`/clients/${id}/archive`, { method: "POST" }),
  projects: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return api<Project[]>(`/projects${qs}`);
  },
  project: (id: string) => api<ProjectDetail>(`/projects/${id}`),
  createProject: (data: unknown) =>
    api<ProjectDetail>("/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id: string, data: unknown) =>
    api<ProjectDetail>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  archiveProject: (id: string) => api<void>(`/projects/${id}/archive`, { method: "POST" }),
  createMilestone: (projectId: string, data: unknown) =>
    api(`/projects/${projectId}/milestones`, { method: "POST", body: JSON.stringify(data) }),
  tasks: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return api<Task[]>(`/tasks${qs}`);
  },
  createTask: (data: unknown) => api<Task>("/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: string, data: unknown) =>
    api<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  archiveTask: (id: string) => api<void>(`/tasks/${id}/archive`, { method: "POST" }),
  task: (id: string) => api<Task>(`/tasks/${id}`),
  taskComments: (id: string) => api<TaskComment[]>(`/tasks/${id}/comments`),
  addTaskComment: (id: string, body: string) =>
    api<TaskComment>(`/tasks/${id}/comments`, { method: "POST", body: JSON.stringify({ body }) }),
  updateTaskComment: (taskId: string, commentId: string, body: string) =>
    api<TaskComment>(`/tasks/${taskId}/comments/${commentId}`, {
      method: "PATCH",
      body: JSON.stringify({ body }),
    }),
  deleteTaskComment: (taskId: string, commentId: string) =>
    api<void>(`/tasks/${taskId}/comments/${commentId}`, { method: "DELETE" }),
  employees: (opts?: string | { q?: string; archived?: boolean }) => {
    const params = typeof opts === "string" ? { q: opts } : opts || {};
    const sp = new URLSearchParams();
    if (params.q) sp.set("q", params.q);
    if (params.archived) sp.set("archived", "true");
    const qs = sp.toString();
    return api<Employee[]>(`/employees${qs ? `?${qs}` : ""}`);
  },
  employee: (id: string) => api<Employee>(`/employees/${id}`),
  createEmployee: (data: unknown) =>
    api<Employee>("/employees", { method: "POST", body: JSON.stringify(data) }),
  updateEmployee: (id: string, data: unknown) =>
    api<Employee>(`/employees/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deactivateEmployee: (id: string) => api<void>(`/employees/${id}`, { method: "DELETE" }),
  inviteEmployee: (data: unknown) =>
    api<{ employee: Employee; invite_url: string; dev_note?: string }>("/employees/invite", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  departments: () => api<Department[]>("/employees/departments"),
  changePassword: (current_password: string, new_password: string) =>
    api<{ ok: boolean }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
  forgotPassword: (email: string) =>
    api<{ ok: boolean; message: string; reset_url?: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, new_password: string) =>
    api<{ ok: boolean }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),
  peekInvite: (token: string) =>
    api<{ email: string; first_name: string; last_name: string; role_key: string; display_name: string }>(
      `/auth/invite/${token}`,
    ),
  acceptInvite: (data: { token: string; password: string; first_name?: string; last_name?: string }) =>
    api<LoginResult>("/auth/accept-invite", { method: "POST", body: JSON.stringify(data) }),
  reports: () => api<ReportsPayload>("/reports"),
  companySettings: () => api<CompanySettings>("/admin/settings"),
  updateCompanySettings: (data: Partial<CompanySettings>) =>
    api<CompanySettings>("/admin/settings", { method: "PATCH", body: JSON.stringify(data) }),
  permissionsMatrix: () => api<PermissionsMatrix>("/admin/permissions"),
  updatePermissionOverrides: (overrides: Record<string, string[]>) =>
    api<PermissionsMatrix>("/admin/permissions/overrides", {
      method: "PUT",
      body: JSON.stringify({ overrides }),
    }),
  integrations: () => api<IntegrationStatus[]>("/admin/integrations"),
  templates: (kind?: string) =>
    api<HqTemplate[]>("/admin/templates" + (kind ? `?kind=${encodeURIComponent(kind)}` : "")),
  createTemplate: (data: Partial<HqTemplate> & { kind: string; title: string }) =>
    api<HqTemplate>("/admin/templates", { method: "POST", body: JSON.stringify(data) }),
  updateTemplate: (id: string, data: Partial<HqTemplate>) =>
    api<HqTemplate>(`/admin/templates/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTemplate: (id: string) => api<{ ok: boolean }>(`/admin/templates/${id}`, { method: "DELETE" }),
  notifications: () => api<AppNotification[]>("/notifications"),
  markNotificationRead: (id: string) =>
    api<AppNotification>(`/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () => api("/notifications/read-all", { method: "POST" }),
  activity: (projectId?: string) =>
    api<Activity[]>(`/activity${projectId ? `?project_id=${projectId}` : ""}`),
  search: (q: string) => api<{ results: SearchHit[] }>(`/search?q=${encodeURIComponent(q)}`),
  askAi: (question: string) =>
    api<{ answer: string; citations: string[] }>("/ai/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  leads: () => api<Lead[]>("/leads"),
  invoices: () => api<Invoice[]>("/invoices"),
  chatChannels: () => api<ChatChannel[]>("/chat/channels"),
  chatMessages: (slug: string) => api<ChatMessage[]>("/chat/channels/" + slug + "/messages"),
  sendChatMessage: (slug: string, body: string) =>
    api<ChatMessage>(`/chat/channels/${slug}/messages`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),
  audit: (limit = 50) => api<AuditEntry[]>(`/audit?limit=${limit}`),
  auditFiltered: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return api<AuditEntry[]>(`/audit${qs}`);
  },
  calendarEvents: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return api<CalendarEvent[]>(`/calendar/events${qs}`);
  },
  docs: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return api<DocListItem[]>(`/docs${qs}`);
  },
  doc: (id: string) => api<Doc>(`/docs/${id}`),
  createDoc: (data: Partial<Doc> & { title: string; content?: Record<string, unknown> }) =>
    api<Doc>("/docs", { method: "POST", body: JSON.stringify(data) }),
  updateDoc: (id: string, data: Partial<Doc> & { content?: Record<string, unknown>; yjs_state_b64?: string }) =>
    api<Doc>(`/docs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteDoc: (id: string) => api<void>(`/docs/${id}`, { method: "DELETE" }),
  files: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return api<FileAsset[]>(`/files${qs}`);
  },
  file: (id: string) => api<FileAsset>(`/files/${id}`),
  uploadFile: async (file: File, meta: { name?: string; kind?: string; notes?: string; project_id?: string; client_id?: string } = {}) => {
    const body = new FormData();
    body.append("file", file);
    if (meta.name) body.append("name", meta.name);
    if (meta.kind) body.append("kind", meta.kind);
    if (meta.notes) body.append("notes", meta.notes);
    if (meta.project_id) body.append("project_id", meta.project_id);
    if (meta.client_id) body.append("client_id", meta.client_id);
    return api<FileAsset>("/files", { method: "POST", body });
  },
  updateFile: (id: string, data: Partial<FileAsset>) =>
    api<FileAsset>(`/files/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteFile: (id: string) => api<void>(`/files/${id}`, { method: "DELETE" }),
  downloadFile: async (id: string, filename: string) => {
    const headers = new Headers();
    const csrf = getCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
    const res = await fetch(`${API}/api/v1/files/${id}/download`, {
      credentials: "include",
      headers,
    });
    if (!res.ok) {
      let detail = "Download failed";
      try {
        const body = await res.json();
        detail = typeof body.detail === "string" ? body.detail : detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(detail, res.status);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  first_name: string;
  last_name: string;
  role_key: string;
  avatar_url: string | null;
  is_superadmin: boolean;
  permissions: string[];
  employee_id: string | null;
  org_id?: string | null;
  totp_enabled?: boolean;
};

export type LoginResult = {
  user?: AuthUser | null;
  csrf_token?: string | null;
  needs_2fa?: boolean;
  temp_token?: string | null;
};

export type KpiCard = {
  key: string;
  label: string;
  value: string | number;
  delta?: number | null;
  delta_label?: string | null;
  tone?: string;
  hint?: string | null;
};

export type AttentionItem = { severity: string; title: string; href?: string | null };

export type Activity = {
  id: string;
  actor_id: string | null;
  verb: string;
  entity_type: string;
  entity_id: string | null;
  project_id: string | null;
  client_id: string | null;
  summary: string;
  meta: Record<string, unknown>;
  created_at: string;
  actor?: { id: string; display_name: string; email: string; role_key: string; avatar_url?: string | null } | null;
};

export type Dashboard = {
  greeting_name: string;
  kpis: KpiCard[];
  attention: AttentionItem[];
  activity: Activity[];
  briefing: string;
  recommended_actions: string[];
  health: Record<string, unknown>;
};

export type Task = {
  id: string;
  title: string;
  description: string | null;
  project_id: string | null;
  assignee_id: string | null;
  reviewer_id: string | null;
  created_by_id: string;
  parent_id: string | null;
  priority: string;
  status: string;
  due_date: string | null;
  start_date: string | null;
  estimated_minutes: number | null;
  actual_minutes: number | null;
  tags: string[];
  checklist: { id?: string; label: string; done?: boolean }[];
  sort_order: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  project_name?: string | null;
  assignee_name?: string | null;
  reviewer_name?: string | null;
  archived?: boolean;
};

export type TaskComment = {
  id: string;
  task_id: string;
  author_id: string;
  body: string;
  created_at: string;
  author?: {
    id: string;
    display_name: string;
    email: string;
    role_key: string;
    avatar_url?: string | null;
  } | null;
};

export type AppNotification = {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  href: string | null;
  priority: string;
  read_at: string | null;
  created_at: string;
};

export type Project = {
  id: string;
  name: string;
  slug: string;
  client_id: string;
  project_manager_id: string | null;
  project_type: string;
  description: string | null;
  start_date: string | null;
  target_completion_date: string | null;
  budget: number | string | null;
  budget_currency: string;
  status: string;
  health: string;
  priority: string;
  progress: number;
  tech_stack: string[];
  repository_url: string | null;
  production_url: string | null;
  staging_url: string | null;
  hours_spent: number;
  is_pinned: boolean;
  created_at: string;
  client_name?: string | null;
  manager_name?: string | null;
  team_count?: number;
  open_tasks?: number;
  blocked_tasks?: number;
  archived?: boolean;
};

export type ProjectDetail = Project & {
  members: {
    id: string;
    user_id: string;
    role_on_project: string;
    user?: { id: string; display_name: string; email: string; role_key: string; avatar_url?: string | null } | null;
  }[];
  milestones: {
    id: string;
    title: string;
    phase: string;
    description: string | null;
    owner_id: string | null;
    start_date: string | null;
    due_date: string | null;
    status: string;
    sort_order: number;
    deliverables: string[];
  }[];
};

export type Client = {
  id: string;
  business_name: string;
  slug: string;
  primary_contact_name: string | null;
  phone: string | null;
  whatsapp: string | null;
  email: string | null;
  location: string | null;
  website: string | null;
  industry: string | null;
  lead_source: string | null;
  account_manager_id: string | null;
  status: string;
  lifetime_value: number | string;
  notes: string | null;
  onboarding_step: number;
  onboarding_complete: boolean;
  created_at: string;
  active_projects?: number;
  pending_invoices?: number | string;
  archived?: boolean;
};

export type Employee = {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  role_key: string;
  job_title: string;
  department_id: string | null;
  department_name: string | null;
  manager_id: string | null;
  employment_type: string;
  location: string | null;
  joining_date: string | null;
  weekly_capacity_hours: number;
  availability: string;
  skills: string[];
  phone: string | null;
  is_active: boolean;
  leave_balance_days: number;
  active_projects: number;
  utilization: number;
  salary: number | string | null;
  salary_currency: string | null;
  created_at: string;
};

export type Department = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  parent_id: string | null;
};

export type Desk = {
  focus: Task[];
  due_today: Task[];
  upcoming: Task[];
  blocked: Task[];
  projects: Project[];
  notifications: AppNotification[];
  activity: Activity[];
};

export type SearchHit = {
  type: string;
  id: string;
  title: string;
  subtitle?: string | null;
  href: string;
};

export type Lead = {
  id: string;
  business_name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  industry: string | null;
  location: string | null;
  requested_service: string | null;
  estimated_value: number | string;
  currency: string;
  source: string | null;
  stage: string;
  assigned_to_id: string | null;
  probability: number;
  notes: string | null;
};

export type Invoice = {
  id: string;
  number: string;
  client_id: string;
  project_id: string | null;
  amount: number | string;
  tax: number | string;
  discount: number | string;
  currency: string;
  due_date: string | null;
  status: string;
  payment_method: string | null;
  notes: string | null;
  client_name?: string | null;
};

export type ChatChannel = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  topic: string | null;
};

export type ChatMessage = {
  id: string;
  channel_id: string;
  author_id: string;
  body: string;
  created_at: string;
  author?: { id: string; display_name: string; email: string; role_key: string; avatar_url?: string | null } | null;
};

export type AuditEntry = {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  ip_address: string | null;
  user_agent?: string | null;
  meta: Record<string, unknown>;
  created_at: string;
  user_name?: string | null;
  user_email?: string | null;
};

export type DocListItem = {
  id: string;
  title: string;
  slug: string;
  kind: string;
  status: string;
  summary: string | null;
  project_id: string | null;
  client_id: string | null;
  created_by_id: string;
  updated_by_id: string | null;
  updated_at: string;
  created_at: string;
  project_name?: string | null;
  client_name?: string | null;
  author_name?: string | null;
};

export type Doc = DocListItem & {
  content: Record<string, unknown>;
  plain_text?: string | null;
};

export type FileAsset = {
  id: string;
  name: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  kind: string;
  notes: string | null;
  project_id: string | null;
  client_id: string | null;
  uploaded_by_id: string;
  created_at: string;
  updated_at: string;
  project_name?: string | null;
  client_name?: string | null;
  uploader_name?: string | null;
  download_url?: string | null;
};

export type CalendarEvent = {
  id: string;
  title: string;
  date: string;
  kind: string;
  status?: string | null;
  project_id?: string | null;
  project_name?: string | null;
  href?: string | null;
  priority?: string | null;
};

export type ReportsPayload = {
  revenue_collected: number;
  revenue_outstanding: number;
  revenue_overdue: number;
  invoice_count: number;
  paid_count: number;
  lead_total: number;
  lead_won: number;
  lead_conversion_pct: number;
  active_projects: number;
  at_risk_projects: number;
  utilization_pct: number;
  active_clients: number;
  headcount: number;
  open_tasks: number;
  invoices_by_status: { label: string; value: number }[];
  leads_by_stage: { label: string; value: number }[];
  projects_by_health: { label: string; value: number }[];
};

export type CompanySettings = {
  id: string;
  name: string;
  slug: string;
  notes?: string | null;
  legal_name?: string | null;
  billing_entity?: string | null;
  public_site?: string | null;
  hq_domain?: string | null;
  client_portal_domain?: string | null;
  careers_domain?: string | null;
  timezone: string;
  currency: string;
};

export type PermissionsMatrix = {
  roles: Record<string, string[]>;
  all_permissions: string[];
  labels: Record<string, string>;
  overrides: Record<string, string[]>;
};

export type IntegrationStatus = {
  key: string;
  label: string;
  configured: boolean;
  detail: string;
  docs_hint?: string | null;
};

export type HqTemplate = {
  id: string;
  kind: string;
  title: string;
  description?: string | null;
  body: Record<string, unknown>;
};

export const ROLE_LABELS: Record<string, string> = {
  founder: "Founder",
  operations_manager: "Operations Manager",
  project_manager: "Project Manager",
  developer: "Developer",
  designer: "Designer",
  automation_engineer: "Automation Engineer",
  marketing: "Marketing / SEO",
  sales: "Sales",
  finance: "Finance",
  freelancer: "Freelancer",
};

export const PROJECT_TYPES = [
  "Website",
  "E-commerce",
  "Mobile App",
  "AI Automation",
  "WhatsApp Automation",
  "Custom Software",
  "SEO",
  "Digital Transformation",
  "Other",
];
