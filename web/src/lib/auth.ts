export function setToken(token: string) {
  localStorage.setItem("token", token);
  // Cookie for Next.js middleware (7 days)
  document.cookie = `token=${token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

export function clearToken() {
  localStorage.removeItem("token");
  document.cookie = "token=; path=/; max-age=0";
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}
