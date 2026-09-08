// Thin, named aliases onto the generated schema so the rest of the app
// doesn't reach into `components["schemas"][...]` everywhere.
import type { components } from "./schema";

export type QueryIn = components["schemas"]["QueryIn"];
export type QueryOut = components["schemas"]["QueryOut"];
export type RetrievedSection = components["schemas"]["RetrievedSection"];
export type OffenceAttributesOut = components["schemas"]["OffenceAttributesOut"];
export type JudicialStatusOut = components["schemas"]["JudicialStatusOut"];
export type SectionOut = components["schemas"]["SectionOut"];
export type SectionDetailOut = components["schemas"]["SectionDetailOut"];
export type PreviousVersionOut = components["schemas"]["PreviousVersionOut"];
export type NewsOut = components["schemas"]["NewsOut"];
export type ComplaintIn = components["schemas"]["ComplaintIn"];
export type ComplaintOut = components["schemas"]["ComplaintOut"];
export type ComplaintType = components["schemas"]["ComplaintType"];
export type HelplineOut = components["schemas"]["HelplineOut"];
export type OffenceResultOut = components["schemas"]["OffenceResultOut"];
export type CognizabilitySearchOut = components["schemas"]["CognizabilitySearchOut"];
export type UserOut = components["schemas"]["UserOut"];
export type AuthOut = components["schemas"]["AuthOut"];
export type LoginIn = components["schemas"]["LoginIn"];
export type RegisterIn = components["schemas"]["RegisterIn"];
export type UpdatePreferencesIn = components["schemas"]["UpdatePreferencesIn"];
export type Tokens = components["schemas"]["Tokens"];
export type ConversationSummaryOut = components["schemas"]["ConversationSummaryOut"];
export type ConversationDetailOut = components["schemas"]["ConversationDetailOut"];
export type ConversationTurnOut = components["schemas"]["ConversationTurnOut"];
