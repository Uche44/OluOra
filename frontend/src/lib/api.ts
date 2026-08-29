const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (res.ok) {
      const data = await res.json();
      const newAccessToken = data.access_token;
      if (newAccessToken) {
        localStorage.setItem("access_token", newAccessToken);
        // Refresh tokens are rotated: persist the new one so future refreshes work.
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }
        return newAccessToken;
      }
    }
  } catch (e) {
    console.error("Error refreshing token:", e);
  }

  // If refresh failed, clear tokens
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  return null;
}

export function clearAuthStorage(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem("refresh_token");
  // Best-effort server-side revocation of the refresh token.
  if (refreshToken) {
    try {
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    } catch (e) {
      console.error("Error during logout:", e);
    }
  }
  clearAuthStorage();
}

export async function authedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("access_token");
  
  const headers = {
    ...options.headers,
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    // Attempt token refresh
    const newToken = await refreshAccessToken();
    if (newToken) {
      // Retry request with new token
      const retryHeaders = {
        ...options.headers,
        "Authorization": `Bearer ${newToken}`
      };
      res = await fetch(url, { ...options, headers: retryHeaders });
    } else {
      // Refresh failed, redirect to login
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
  }

  return res;
}
