import axios, { AxiosError, type AxiosRequestConfig } from "axios";

export const API_BASE_URL: string = (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE_URL });

// ---- token storage (wrapped: storage can be blocked in private windows) ----
const store = {
  get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  del: (k: string) => { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};
export const tokens = {
  access: () => store.get("access_token"),
  refresh: () => store.get("refresh_token"),
  save: (access: string, refresh?: string) => { store.set("access_token", access); if (refresh) store.set("refresh_token", refresh); },
  clear: () => { store.del("access_token"); store.del("refresh_token"); store.del("current_user"); },
};

api.interceptors.request.use((config) => {
  const token = tokens.access();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ---- silent refresh: one refresh in flight at a time; queued requests retry with the new token ----
let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokens.refresh();
  if (!refresh) return null;
  try {
    // plain axios: this call must not pass through the interceptors below
    const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refresh });
    tokens.save(res.data.access_token, res.data.refresh_token);
    return res.data.access_token as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined;
    const url = original?.url ?? "";
    const isAuthCall = url.includes("/auth/login") || url.includes("/auth/register") || url.includes("/auth/refresh");
    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken().finally(() => { refreshing = null; });
      const newToken = await refreshing;
      if (newToken) {
        original.headers = { ...(original.headers as any), Authorization: `Bearer ${newToken}` };
        return api(original);
      }
    }
    if (error.response?.status === 401 && !isAuthCall) {
      tokens.clear();
      if (!window.location.pathname.startsWith("/login")) window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export function getErrorMessage(error: any, fallback = "Something went wrong. Please try again."): string {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d: any) => d.msg).join(", ");
  if (error?.response?.status === 429) return "Too many requests. Please wait a moment and try again.";
  if (error?.message === "Network Error") return "Could not reach the server. Please make sure the backend is running.";
  return fallback;
}

type P = Record<string, unknown>;
const form = (file: File, extra: Record<string, string> = {}) => {
  const f = new FormData();
  f.append("file", file);
  Object.entries(extra).forEach(([k, v]) => f.append(k, v));
  return f;
};

// ---------- Auth ----------
export const registerUser = (payload: P) => api.post("/auth/register", payload);
export const loginUser = (payload: P) => api.post("/auth/login", payload);
export const logoutUser = () => api.post("/auth/logout", { refresh_token: tokens.refresh() });

// ---------- Profile ----------
export const getMe = () => api.get("/users/me");
export const updateProfile = (payload: P) => api.put("/users/me/profile", payload);
export const getReadiness = () => api.get("/users/me/readiness");
export const autofillProfile = (overwrite = false) => api.post("/users/me/profile/autofill", { overwrite });
export const uploadPhoto = (file: File) => api.post("/users/me/photo", form(file));
export const deletePhoto = () => api.delete("/users/me/photo");
export const fetchPhotoBlob = () => api.get("/users/me/photo", { responseType: "blob" });

// ---------- Resume ----------
export const uploadResume = (file: File, label = "") => api.post("/resume/upload", form(file), { params: label ? { label } : {} });
export const getResume = () => api.get("/resume");
export const getResumeById = (id: number) => api.get(`/resume/${id}`);
export const listResumeVersions = () => api.get("/resume/versions");
export const activateResume = (id: number) => api.post(`/resume/${id}/activate`);
export const deleteResume = (id: number) => api.delete(`/resume/${id}`);
export const listJobDescriptions = () => api.get("/resume/job-descriptions");
export const matchResume = (payload: P) => api.post("/resume/match", payload);
export const listMatches = () => api.get("/resume/matches");

// ---------- Interviews ----------
export const startInterview = (payload: P) => api.post("/interviews/start", payload);
export const submitInterviewAnswer = (id: number, payload: P) => api.post(`/interviews/${id}/answer`, payload);
export const completeInterview = (id: number) => api.post(`/interviews/${id}/complete`);
export const getInterviewHistory = () => api.get("/interviews/history");
export const getInterviewDetail = (id: number | string) => api.get(`/interviews/${id}`);
export const analyzeSpeech = (payload: P) => api.post("/speech/analyze", payload);

// ---------- Coding ----------
export const listCodingQuestions = (params: P = {}) => api.get("/coding/questions", { params });
export const getCodingQuestion = (id: number | string) => api.get(`/coding/questions/${id}`);
export const runCode = (payload: P) => api.post("/coding/run", payload);
export const submitCode = (payload: P) => api.post("/coding/submit", payload);
export const listSubmissions = (params: P = {}) => api.get("/coding/submissions", { params });
export const getSubmission = (id: number) => api.get(`/coding/submissions/${id}`);
export const startAssessment = (payload: P) => api.post("/coding/assessments", payload);
export const listAssessments = () => api.get("/coding/assessments");
export const getAssessment = (id: number | string) => api.get(`/coding/assessments/${id}`);
export const finishAssessment = (id: number) => api.post(`/coding/assessments/${id}/finish`);

// ---------- Insights ----------
export const getSkillGap = (role?: string) => api.get("/skill-gap", { params: role ? { role } : {} });
export const listRoles = () => api.get("/skill-gap/roles");
export const getAnalytics = () => api.get("/analytics/me");
export const getRoadmap = () => api.get("/roadmap");
export const createRoadmap = (payload: P) => api.post("/roadmap", payload);
export const refreshRoadmap = () => api.post("/roadmap/refresh");
export const setTaskStatus = (id: number, status: "todo" | "done") => api.patch(`/roadmap/tasks/${id}`, { status });
export const listCompanies = () => api.get("/companies");
export const getCompany = (slug: string) => api.get(`/companies/${slug}`);

// ---------- RAG ----------
export const ragStatus = () => api.get("/rag/status");
export const ragDocuments = () => api.get("/rag/documents");
export const ragUpload = (file: File, docType = "notes") => api.post("/rag/documents", form(file, { doc_type: docType }));
export const ragIndexResume = () => api.post("/rag/documents/from-resume");
export const ragDelete = (id: number) => api.delete(`/rag/documents/${id}`);
export const ragSearch = (payload: P) => api.post("/rag/search", payload);
export const ragChat = (payload: P) => api.post("/rag/chat", payload);
export const ragHistory = () => api.get("/rag/chat/history");
export const ragClearHistory = () => api.delete("/rag/chat/history");

// ---------- Platform ----------
export const getAiStatus = () => api.get("/ai/status");

// ---------- Legacy (kept for the original pages) ----------
export const evaluateAnswer = (payload: P) => api.post("/evaluate", payload);
export const transcribeAudio = (blob: Blob) => {
  const f = new FormData();
  f.append("file", blob, "answer.webm");
  return api.post("/speech/transcribe", f);
};
export const getPerformance = () => api.get("/performance");
export const getPreparationPlan = () => api.get("/preparation-plan");
export const regeneratePreparationPlan = () => api.post("/preparation-plan/regenerate");

export default api;
