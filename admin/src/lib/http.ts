import { adminFetch, apiUrl } from "@/lib/api";

/** GET an admin endpoint as JSON, throwing on non-2xx (403 is handled by adminFetch). */
export async function getJson<T>(path: string): Promise<T> {
  const res = await adminFetch(`${apiUrl}/api/v1${path}`);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}
