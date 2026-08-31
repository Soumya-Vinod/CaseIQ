/**
 * `QueryOut.structured_data` is `object` in the OpenAPI schema (generated as
 * `Record<string, never>`) DELIBERATELY -- see the architecture decision
 * earlier in this project: it's LLM output, untyped and untrusted by design,
 * not a contract the backend guarantees. The shape below documents what
 * app/services/llm.py's prompt CURRENTLY asks the model to return, but
 * every field is optional and every consumer must check before rendering --
 * never assume a field exists just because it's listed here. On the
 * abstention path this is always `{}`.
 */
export interface StructuredData {
  situation_overview?: string;
  severity?: "low" | "medium" | "high" | "critical" | string;
  severity_reason?: string;
  laws_applicable?: {
    act?: string;
    section?: string;
    title?: string;
    why_applies?: string;
    ipc_equivalent?: string | null;
  }[];
  punishments?: {
    offence?: string;
    imprisonment?: string;
    fine?: string;
    bailable?: string;
    cognizable?: string;
  }[];
  immediate_steps?: {
    step?: number;
    action?: string;
    details?: string;
    urgency?: string;
  }[];
  critical_deadlines?: {
    deadline?: string;
    what?: string;
    consequence?: string;
  }[];
  your_rights?: {
    right?: string;
    explanation?: string;
    law?: string;
  }[];
  dos_and_donts?: {
    dos?: string[];
    donts?: string[];
  };
}

/** True non-empty array, not just "is an array" -- an empty list from the
 * LLM shouldn't render an empty section header. */
export function nonEmptyArray<T>(v: T[] | undefined): v is T[] {
  return Array.isArray(v) && v.length > 0;
}

export function nonEmptyString(v: string | undefined): v is string {
  return typeof v === "string" && v.trim().length > 0;
}
