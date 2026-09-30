// Admin API client. Tokens live in sessionStorage (not localStorage) so the
// admin session never outlives the tab and is isolated from the public app's
// origin. The backend enforces admin auth on every /admin/* route — this client
// is convenience, not the security boundary.

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export { apiUrl };

const ACCESS_KEY = "admin_access_token";
const REFRESH_KEY = "admin_refresh_token";
const USER_KEY = "admin_user";

export interface AdminSessionUser {
  id?: string;
  email: string;
  full_name?: string;
  profile_picture?: string;
}

export function getStoredUser(): AdminSessionUser | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function hasSession(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(sessionStorage.getItem(ACCESS_KEY));
}

export function saveSession(
  accessToken: string,
  refreshToken: string,
  user: AdminSessionUser,
): void {
  sessionStorage.setItem(ACCESS_KEY, accessToken);
  sessionStorage.setItem(REFRESH_KEY, refreshToken);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthStorage(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = sessionStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        sessionStorage.setItem(ACCESS_KEY, data.access_token);
        if (data.refresh_token) {
          sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
        }
        return data.access_token;
      }
    }
  } catch (e) {
    console.error("Error refreshing token:", e);
  }

  clearAuthStorage();
  return null;
}

export async function logout(): Promise<void> {
  const refreshToken = sessionStorage.getItem(REFRESH_KEY);
  if (refreshToken) {
    try {
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (e) {
      console.error("Error during logout:", e);
    }
  }
  clearAuthStorage();
}

export async function authedFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const token = sessionStorage.getItem(ACCESS_KEY);

  const headers = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = {
        ...options.headers,
        Authorization: `Bearer ${newToken}`,
      };
      res = await fetch(url, { ...options, headers: retryHeaders });
    } else if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return res;
}

/**
 * Fetch an admin endpoint. A 403 means the caller is authenticated but not an
 * admin — clear the session and bounce to the denied screen rather than looping.
 */
export async function adminFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const res = await authedFetch(url, options);
  if (res.status === 403) {
    clearAuthStorage();
    if (typeof window !== "undefined") {
      window.location.href = "/login?denied=1";
    }
  }
  return res;
}

/** Kick off the Google sign-in flow, stashing the state token for CSRF checks. */
export async function startGoogleLogin(): Promise<void> {
  const res = await fetch(`${apiUrl}/api/v1/auth/google/url?client=admin`);
  if (!res.ok) {
    throw new Error("Could not reach the authentication service.");
  }
  const data = await res.json();
  if (!data.url) {
    throw new Error("No login URL returned by the server.");
  }
  if (data.state) {
    sessionStorage.setItem("google_oauth_state", data.state);
  }
  window.location.href = data.url;
}
