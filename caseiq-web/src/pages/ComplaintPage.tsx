import { useState } from "react";
import { api } from "../api/client";
import type { ComplaintIn, ComplaintOut, ComplaintType } from "../api/types";
import { SourcesPanel } from "../components/SourcesPanel";
import styles from "./ComplaintPage.module.css";

const TYPE_LABELS: Record<ComplaintType, string> = {
  fir: "First Information Report (FIR)",
  written_complaint: "Written Complaint",
  magistrate_complaint: "Magistrate Complaint",
  consumer_complaint: "Consumer Complaint",
  cyber_complaint: "Cyber Complaint",
};

type FormState = Omit<ComplaintIn, "complaint_type" | "language"> & {
  complaint_type: ComplaintType | "";
  language: "en" | "hi" | "mr" | "ta";
};

const EMPTY: FormState = {
  complaint_type: "",
  complainant_name: "",
  complainant_address: "",
  complainant_phone: "",
  police_station_name: "",
  police_station_address: "",
  incident_date: "",
  incident_location: "",
  incident_description: "",
  accused_details: "",
  witnesses: "",
  evidence_description: "",
  relief_sought: "",
  language: "en",
};

// Each step's own required fields -- gates the "Next" button, not just final
// submit, so a guided step can't be skipped past silently empty.
const STEPS = [
  { key: "incident", label: "Incident", required: ["complaint_type", "incident_date", "incident_location"] as const },
  { key: "parties", label: "Parties", required: ["complainant_name", "complainant_address"] as const },
  { key: "narrative", label: "What happened", required: ["incident_description"] as const },
  { key: "relief", label: "Relief sought", required: [] as const },
] satisfies { key: string; label: string; required: readonly (keyof FormState)[] }[];

export function ComplaintPage() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComplaintOut | null>(null);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  const missing = STEPS[step].required.filter((k) => !String(form[k] ?? "").trim());
  const canAdvance = missing.length === 0;

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const { data, error: apiError } = await api.POST("/api/v1/complaints", {
        body: { ...form, complaint_type: form.complaint_type as ComplaintType },
      });
      if (apiError) {
        setError("Something went wrong drafting the complaint. Please try again.");
        return;
      }
      setResult(data);
    } catch {
      setError("Could not reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  function startOver() {
    setResult(null);
    setForm(EMPTY);
    setStep(0);
    setError(null);
  }

  if (result) {
    return <ComplaintResult result={result} onStartOver={startOver} />;
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Draft a Complaint</p>
        <h1 className={styles.title}>File a complaint</h1>
        <p className={styles.subtitle}>
          A guided draft, grounded in the same statutory corpus as every CaseIQ answer — the
          sections it cites are the sections it actually found, never invented. Review with a
          qualified advocate before filing.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <ol className={styles.stepper} aria-label="Form progress">
        {STEPS.map((s, i) => (
          <li
            key={s.key}
            className={`${styles.step} ${i === step ? styles.stepActive : ""} ${i < step ? styles.stepDone : ""}`}
          >
            <span className={styles.stepNum}>{i < step ? "✓" : i + 1}</span>
            <span className={styles.stepLabel}>{s.label}</span>
          </li>
        ))}
      </ol>

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault();
          if (step < STEPS.length - 1) setStep(step + 1);
          else void submit();
        }}
      >
        {step === 0 && (
          <fieldset className={styles.fieldset}>
            <label className={styles.field}>
              <span className={styles.label}>Type of complaint</span>
              <select
                className={styles.select}
                value={form.complaint_type}
                onChange={(e) => set("complaint_type", e.target.value as ComplaintType)}
              >
                <option value="" disabled>
                  Select a type…
                </option>
                {Object.entries(TYPE_LABELS).map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Date of incident</span>
              <input
                className={styles.input}
                type="date"
                value={form.incident_date}
                onChange={(e) => set("incident_date", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Location of incident</span>
              <input
                className={styles.input}
                placeholder="e.g. Residence in Shivajinagar, Pune"
                value={form.incident_location}
                onChange={(e) => set("incident_location", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Police station (if known)</span>
              <input
                className={styles.input}
                placeholder="e.g. Shivajinagar Police Station"
                value={form.police_station_name}
                onChange={(e) => set("police_station_name", e.target.value)}
              />
            </label>
          </fieldset>
        )}

        {step === 1 && (
          <fieldset className={styles.fieldset}>
            <label className={styles.field}>
              <span className={styles.label}>Your full name</span>
              <input
                className={styles.input}
                value={form.complainant_name}
                onChange={(e) => set("complainant_name", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Your address</span>
              <textarea
                className={styles.textarea}
                value={form.complainant_address}
                onChange={(e) => set("complainant_address", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Your phone (optional)</span>
              <input
                className={styles.input}
                type="tel"
                value={form.complainant_phone}
                onChange={(e) => set("complainant_phone", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Accused / other party details</span>
              <textarea
                className={styles.textarea}
                placeholder="Name, relationship to you, address if known"
                value={form.accused_details}
                onChange={(e) => set("accused_details", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Witnesses (optional)</span>
              <textarea
                className={styles.textarea}
                value={form.witnesses}
                onChange={(e) => set("witnesses", e.target.value)}
              />
            </label>
          </fieldset>
        )}

        {step === 2 && (
          <fieldset className={styles.fieldset}>
            <label className={styles.field}>
              <span className={styles.label}>What happened</span>
              <textarea
                className={styles.textareaLarge}
                placeholder="Describe the incident in your own words, as fully as you can."
                value={form.incident_description}
                onChange={(e) => set("incident_description", e.target.value)}
                maxLength={4000}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Evidence available (optional)</span>
              <textarea
                className={styles.textarea}
                placeholder="e.g. medical report, photographs, messages"
                value={form.evidence_description}
                onChange={(e) => set("evidence_description", e.target.value)}
              />
            </label>
          </fieldset>
        )}

        {step === 3 && (
          <fieldset className={styles.fieldset}>
            <label className={styles.field}>
              <span className={styles.label}>What relief are you seeking?</span>
              <textarea
                className={styles.textareaLarge}
                placeholder="e.g. Registration of an FIR, a protection order, return of property"
                value={form.relief_sought}
                onChange={(e) => set("relief_sought", e.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Draft language</span>
              <select
                className={styles.select}
                value={form.language}
                onChange={(e) => set("language", e.target.value as FormState["language"])}
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="mr">Marathi</option>
                <option value="ta">Tamil</option>
              </select>
            </label>
          </fieldset>
        )}

        {error && <div className={styles.errorBox}>{error}</div>}

        <div className={styles.navRow}>
          {step > 0 && (
            <button type="button" className={styles.backButton} onClick={() => setStep(step - 1)}>
              Back
            </button>
          )}
          <button
            type="submit"
            className={styles.nextButton}
            disabled={!canAdvance || loading}
          >
            {loading
              ? "Drafting…"
              : step < STEPS.length - 1
                ? "Next"
                : "Generate draft"}
          </button>
        </div>
        {!canAdvance && (
          <p className={styles.hint}>Fill in the required fields above to continue.</p>
        )}
      </form>
    </main>
  );
}

function ComplaintResult({
  result,
  onStartOver,
}: {
  result: ComplaintOut;
  onStartOver: () => void;
}) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Draft Ready</p>
        <h1 className={styles.title}>Your complaint draft</h1>
        <p className={styles.subtitle}>
          Preview before downloading. This is a template for reference, not legal advice — have
          it reviewed by a qualified advocate before you file it.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      <div className={styles.disclaimer}>{result.disclaimer}</div>

      <section className={styles.draftSection}>
        <h2 className={styles.sectionHeading}>Preview</h2>
        {result.generated_draft ? (
          <div className={styles.draftPaper}>
            {result.generated_draft.split("\n").map((line, i) => (
              <p key={i} className={styles.draftLine}>
                {line || " "}
              </p>
            ))}
          </div>
        ) : (
          <div className={styles.draftEmpty}>
            The draft could not be generated. Nothing was downloaded or saved — try again, or
            file directly with your local police station.
          </div>
        )}
      </section>

      <section className={styles.sourcesSection}>
        <SourcesPanel sections={result.legal_sections} />
      </section>

      <div className={styles.actions}>
        {result.pdf_available && result.download_url ? (
          <a
            className={styles.downloadButton}
            href={`${baseUrl}${result.download_url}`}
            target="_blank"
            rel="noreferrer"
          >
            Download PDF
          </a>
        ) : (
          <p className={styles.pdfUnavailable}>
            PDF generation failed for this draft — the text above is still yours to copy.
          </p>
        )}
        <button type="button" className={styles.startOverButton} onClick={onStartOver}>
          Start a new complaint
        </button>
      </div>
    </main>
  );
}
