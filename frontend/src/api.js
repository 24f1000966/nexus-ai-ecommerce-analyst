import axios from "axios";

const TOKEN_KEY = "nexus_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Empty in local dev (Vite proxies /api); the deployed backend's origin in production builds.
export const API_ORIGIN = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
export const apiUrl = (path) => `${API_ORIGIN}${path}`;

const client = axios.create({ baseURL: `${API_ORIGIN}/api` });

client.interceptors.request.use((cfg) => {
  const t = tokenStore.get();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && tokenStore.get()) {
      tokenStore.clear();
      window.dispatchEvent(new Event("nexus-logout"));
    }
    return Promise.reject(err);
  }
);

export function errorMessage(err, fallback = "Something went wrong. Please try again.") {
  const d = err?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join("; ");
  if (!err?.response) return "Cannot reach the server. Is the backend running?";
  return fallback;
}

const data = (p) => p.then((r) => r.data);

// auth
export const login = (email, password) => data(client.post("/auth/login", { email, password }));
export const getMe = () => data(client.get("/auth/me"));
export const registerCompany = (formData) => data(client.post("/auth/register-company", formData));

// super admin
export const getAdminStats = () => data(client.get("/admin/stats"));
export const getAdminCompanies = (status) => data(client.get("/admin/companies", { params: status ? { status } : {} }));
export const getCompanyReview = (id) => data(client.get(`/admin/companies/${id}`));
export const decideCompany = (id, action, reason = "") => data(client.post(`/admin/companies/${id}/${action}`, { reason }));
export async function openLetter(id) {
  const r = await client.get(`/admin/companies/${id}/letter`, { responseType: "blob" });
  window.open(URL.createObjectURL(r.data), "_blank");
}

// company admin
export const getMembers = () => data(client.get("/company/members"));
export const addMember = (body) => data(client.post("/company/members", body));
export const setMemberActive = (id, active) => data(client.patch(`/company/members/${id}/active`, null, { params: { active } }));

// analytics
export const getStatus = () => data(client.get("/status"));
export const getKpis = () => data(client.get("/kpis"));
export const getSamples = () => data(client.get("/samples"));
export const getSchema = () => data(client.get("/schema"));
export const askQuestion = (question) => data(client.post("/ask", { question }));
