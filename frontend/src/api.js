export const API = import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000";

const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const authEndpoints = new Set([
  "/api/auth/login",
  "/api/auth/register",
  "/api/admin/login",
  "/api/auth/token",
  "/api/admin/token",
  "/api/auth/refresh",
  "/api/auth/logout",
]);
let refreshInFlight;

function csrfToken() {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)campus_x_mart_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function addCsrfHeader(headers, method) {
  if (unsafeMethods.has(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }
}

async function refreshSession() {
  const headers = new Headers();
  addCsrfHeader(headers, "POST");
  const response = await fetch(`${API}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers,
  });
  return response.ok;
}

export async function apiFetch(path, init = {}, retry = true) {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers || {});
  addCsrfHeader(headers, method);
  const response = await fetch(`${API}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include",
  });

  if (response.status !== 401 || !retry || authEndpoints.has(path)) return response;

  refreshInFlight ||= refreshSession().finally(() => {
    refreshInFlight = undefined;
  });
  if (!(await refreshInFlight)) return response;
  return apiFetch(path, init, false);
}

export async function api(path, method = "GET", body) {
  const headers = new Headers();
  if (body !== undefined) headers.set("Content-Type", "application/json");
  const response = await apiFetch(path, {
    method,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  if (response.status === 204) return {};

  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
  return payload;
}
