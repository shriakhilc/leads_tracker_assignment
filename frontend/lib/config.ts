// Server-side base URL for the FastAPI backend (reachable inside the docker network).
export const API_INTERNAL_URL =
  process.env.API_INTERNAL_URL ?? "http://api:8000/api/v1";

export const COOKIE_NAME = "lt_token";
