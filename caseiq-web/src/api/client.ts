import createClient from "openapi-fetch";
import type { paths } from "./schema";

// Base URL is the bare server origin (no /api/v1) — the generated `paths`
// type keys already include the full "/api/v1/..." prefix from the OpenAPI
// schema, so baseUrl + path would double it if baseUrl included the prefix
// too. Set per environment via VITE_API_BASE_URL (.env.development locally,
// a Vercel env var for the deployed build).
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const api = createClient<paths>({ baseUrl });
