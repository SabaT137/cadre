// Server-only helpers shared by the route handlers and proxy.
export const TOKEN_COOKIE = "cadre_token";
export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");
export const TOKEN_MAX_AGE = 60 * 60 * 12; // matches the backend JWT expiry (12h)
