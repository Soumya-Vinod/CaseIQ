// Thin, named aliases onto the generated schema so the rest of the app
// doesn't reach into `components["schemas"][...]` everywhere.
import type { components } from "./schema";

export type QueryIn = components["schemas"]["QueryIn"];
export type QueryOut = components["schemas"]["QueryOut"];
export type RetrievedSection = components["schemas"]["RetrievedSection"];
export type JudicialStatusOut = components["schemas"]["JudicialStatusOut"];
export type SectionOut = components["schemas"]["SectionOut"];
export type SectionDetailOut = components["schemas"]["SectionDetailOut"];
export type PreviousVersionOut = components["schemas"]["PreviousVersionOut"];
export type NewsOut = components["schemas"]["NewsOut"];
export type ComplaintIn = components["schemas"]["ComplaintIn"];
export type ComplaintOut = components["schemas"]["ComplaintOut"];
export type ComplaintType = components["schemas"]["ComplaintType"];
