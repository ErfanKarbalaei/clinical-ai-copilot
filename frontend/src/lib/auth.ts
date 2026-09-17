/**
 * Minimal client-side auth (Task 18 MVP).
 *
 * Token storage: localStorage + a cookie so SERVER COMPONENTS can forward
 * it to the backend as `Authorization: Bearer …` (the backend stays
 * header-only; the frontend never sees the JWT secret).
 */

const TOKEN_KEY = "clinical_copilot_token";
const COOKIE_NAME = "access_token";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: "doctor" | "admin";
  is_active: boolean;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

function writeCookie(token: string): void {
  // readable by the Next server on request → forwarded as Bearer
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(
    token
  )}; path=/; max-age=${8 * 60 * 60}; samesite=lax`;
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  writeCookie(token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; samesite=lax`;
}

export async function login(
  email: string,
  password: string
): Promise<AuthUser> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }
  );
  if (!response.ok) {
    let detail = "ورود ناموفق بود.";
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // keep the generic message
    }
    throw new Error(detail);
  }
  const { access_token } = (await response.json()) as {
    access_token: string;
  };
  setToken(access_token);
  return fetchMe();
}

export async function fetchMe(): Promise<AuthUser> {
  const token = getToken();
  if (!token) throw new Error("no token");
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/me`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!response.ok) {
    clearToken();
    throw new Error("session expired");
  }
  return (await response.json()) as AuthUser;
}
