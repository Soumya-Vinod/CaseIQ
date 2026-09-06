import createClient from "openapi-fetch";
import { clearTokens, getAccessToken } from "../utils/auth";
import type { paths } from "./schema";

// Base URL is the bare server origin (no /api/v1) — the generated `paths`
// type keys already include the full "/api/v1/..." prefix from the OpenAPI
// schema, so baseUrl + path would double it if baseUrl included the prefix
// too. Set per environment via VITE_API_BASE_URL (.env.development locally,
// a Vercel env var for the deployed build).
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const api = createClient<paths>({ baseUrl });

// Phase B: attach the access token when one exists. Every OTHER call in this
// app already worked fine with no Authorization header at all (OptionalUser
// on the backend), so this is additive -- an anonymous request is still a
// normal, fully-functional request, exactly as before.
//
// On a 401, clear the session rather than attempting a silent refresh: the
// backend's /auth/refresh endpoint exists and could exchange the refresh
// token for a new pair, but retrying the ORIGINAL failed request after a
// silent refresh needs real retry plumbing (the request body may already be
// consumed, risk of a retry loop on a persistently-401ing endpoint). Kept
// minimal, per instruction: an expired session prompts a clean re-login
// instead of failing invisibly, rather than a transparent-refresh flow this
// this pass doesn't attempt.
api.use({
  onRequest({ request }) {
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401 && getAccessToken()) {
      clearTokens();
    }
    return response;
  },
});
