import { adminFetch, apiUrl } from "@/lib/api";

/** GET an admin endpoint as JSON, throwing on non-2xx (403 is handled by adminFetch). */
export async function getJson<T>(path: string): Promise<T> {
  const res = await adminFetch(`${apiUrl}/api/v1${path}`);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}

/** PATCH an admin endpoint with a JSON body, throwing on non-2xx. */
export async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const res = await adminFetch(`${apiUrl}/api/v1${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}

/** POST a JSON body to an admin endpoint, throwing on non-2xx. */
export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await adminFetch(`${apiUrl}/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}
