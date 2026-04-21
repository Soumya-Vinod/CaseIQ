import { useState, useRef } from "react";
import { useReactToPrint } from "react-to-print";
import { motion, AnimatePresence } from "framer-motion";
import FIRWizard from "../components/fir/FIRWizard";
import FIRPreview from "../components/fir/FIRPreview";
import FIRDownload from "../components/fir/FIRDownload";
import PageTransition from "../components/ui/PageTransition";
import { complaintsAPI } from "../services/api";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const FIRDraftPage = () => {
  const { isAuthenticated } = useAuth();
  const [generatedFIR, setGeneratedFIR] = useState(null);
  const [backendDraft, setBackendDraft] = useState(null);
  const [complaintId, setComplaintId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const printRef = useRef();

  const handlePrint = useReactToPrint({ content: () => printRef.current });

  const handleGenerate = async (formData) => {
    setGeneratedFIR(formData);
    setError("");
    setLoading(true);

    const existing = JSON.parse(localStorage.getItem("caseiq_fir")) || [];
    localStorage.setItem("caseiq_fir", JSON.stringify([...existing, formData]));

    try {
      const res = await complaintsAPI.generateDraft({
        complaint_type: "fir",
        complainant_name: formData.fullName,
        complainant_address: formData.address,
        complainant_phone: formData.contact,
        police_station_name: formData.policeStation,
        incident_date: formData.incidentDate,
        incident_location: formData.incidentLocation,
        incident_description: formData.description,
        accused_details:
          `${formData.suspectName || ""} — ${formData.suspectDescription || ""}`.trim(),
        witnesses: formData.witnessName
          ? `${formData.witnessName} (${formData.witnessContact || "No contact"})`
          : "",
        evidence_description: formData.evidenceDetails || "",
        relief_sought:
          "Registration of FIR, arrest of accused, and necessary legal action.",
        applicable_sections: formData.applicableSection
          ? [formData.applicableSection]
          : [],
        language: "en",
      });
      setBackendDraft(res.data.generated_draft);
      setComplaintId(res.data.complaint_id);
      toast.success("FIR draft generated successfully!");
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        "AI draft generation failed. Basic PDF still available.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageTransition>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,500&family=DM+Sans:wght@300;400;500;600&display=swap');

        :root {
          --gold-bright:   #FFD700;
          --gold-main:     #D4AF37;
          --gold-mid:      #C9A84C;
          --gold-muted:    #9A7D3A;
          --black-0:       #0B0B0B;
          --black-1:       #111111;
          --surface:       rgba(18,18,18,0.95);
          --border-gold:   rgba(212,175,55,0.17);
          --border-gold-h: rgba(212,175,55,0.42);
          --text-primary:  #E8E8E8;
          --text-muted:    #6B6B75;
          --serif:         'Cormorant Garamond', Georgia, serif;
          --sans:          'DM Sans', system-ui, sans-serif;
          --ease-gold:     cubic-bezier(0.4, 0, 0.2, 1);
        }

        html, body, #root { background: var(--black-0) !important; }

        .fir-shell {
          min-height: 100vh;
          background: var(--black-0);
          background-image:
            radial-gradient(ellipse 80% 45% at 50% -8%, rgba(212,175,55,0.11) 0%, transparent 60%),
            radial-gradient(ellipse 40% 28% at 92% 85%, rgba(212,175,55,0.05) 0%, transparent 55%);
          font-family: var(--sans);
          position: relative;
        }

        .fir-shell::before {
          content: '';
          position: fixed;
          inset: 0;
          background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
          pointer-events: none;
          z-index: 0;
        }

        .fir-root {
          max-width: 900px;
          margin: 0 auto;
          padding: 52px 28px 88px;
          display: flex;
          flex-direction: column;
          gap: 32px;
          position: relative;
          z-index: 1;
        }

        /* ── HEADER ── */
        .fir-eyebrow {
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 3.5px;
          text-transform: uppercase;
          color: var(--gold-muted);
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
        }

        .fir-eyebrow::before {
          content: '';
          display: block;
          width: 32px;
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--gold-muted));
        }

        .fir-title {
          font-family: var(--serif);
          font-size: clamp(2rem, 4.5vw, 3rem);
          font-weight: 700;
          font-style: italic;
          background: linear-gradient(135deg, var(--gold-main) 0%, var(--gold-bright) 50%, var(--gold-mid) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          filter: drop-shadow(0 0 28px rgba(212,175,55,0.25));
          line-height: 1.05;
          margin: 0 0 10px;
        }

        .fir-subtitle {
          font-size: 0.85rem;
          color: var(--text-muted);
          max-width: 500px;
          line-height: 1.65;
        }

        /* ── DIVIDER ── */
        .fir-divider {
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--border-gold), rgba(212,175,55,0.35), var(--border-gold), transparent);
        }

        /* ── WIZARD CARD ── */
        .fir-wizard-card {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-top: 1px solid rgba(212,175,55,0.3);
          border-radius: 22px;
          padding: 36px 32px;
          box-shadow:
            0 1px 0 rgba(212,175,55,0.15) inset,
            0 20px 60px rgba(0,0,0,0.65);
          position: relative;
          overflow: hidden;
        }

        .fir-wizard-card::before {
          content: '';
          position: absolute;
          top: 0; left: 10%; right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent);
        }

        .fir-wizard-card::after {
          content: '';
          position: absolute;
          top: -50px; right: -50px;
          width: 200px; height: 200px;
          background: radial-gradient(circle, rgba(212,175,55,0.07) 0%, transparent 70%);
          pointer-events: none;
        }

        /* ── LOADING ── */
        .fir-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          padding: 60px 20px;
        }

        .fir-spinner-wrap {
          position: relative;
          width: 56px;
          height: 56px;
        }

        .fir-spinner-outer {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          border: 2px solid rgba(212,175,55,0.15);
          border-top-color: var(--gold-main);
          animation: fir-spin 1s linear infinite;
        }

        .fir-spinner-inner {
          position: absolute;
          inset: 8px;
          border-radius: 50%;
          border: 2px solid rgba(212,175,55,0.08);
          border-bottom-color: var(--gold-mid);
          animation: fir-spin 0.7s linear infinite reverse;
        }

        @keyframes fir-spin { to { transform: rotate(360deg); } }

        .fir-loading-title {
          font-family: var(--serif);
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--gold-mid);
          text-align: center;
        }

        .fir-loading-sub {
          font-size: 0.78rem;
          color: var(--text-muted);
          text-align: center;
          max-width: 340px;
          line-height: 1.6;
        }

        /* ── ERROR BANNER ── */
        .fir-error {
          background: rgba(180,60,40,0.07);
          border: 1px solid rgba(180,60,40,0.25);
          border-left: 3px solid rgba(220,80,60,0.6);
          color: #E07060;
          border-radius: 12px;
          padding: 14px 18px;
          font-size: 0.82rem;
          line-height: 1.55;
        }

        /* ── DARK INPUTS GLOBAL (covers FIRWizard children) ── */
.fir-wizard-card input,
.fir-wizard-card textarea,
.fir-wizard-card select {
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid rgba(212, 175, 55, 0.25) !important;
  border-radius: 10px !important;
  color: #E8E8E8 !important;
  font-family: var(--sans) !important;
  font-size: 14px !important;
  padding: 11px 14px !important;
  outline: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

.fir-wizard-card input::placeholder,
.fir-wizard-card textarea::placeholder {
  color: #4A4A55 !important;
}

.fir-wizard-card input:focus,
.fir-wizard-card textarea:focus,
.fir-wizard-card select:focus {
  border-color: var(--gold-main) !important;
  box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.15) !important;
  background: rgba(212, 175, 55, 0.04) !important;
}

.fir-wizard-card select option {
  background: #111111 !important;
  color: #E8E8E8 !important;
}

/* Labels */
.fir-wizard-card label {
  color: #9A9AA6 !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  letter-spacing: 0.4px !important;
  text-transform: uppercase !important;
  margin-bottom: 6px !important;
  display: block !important;
}

        /* ── AI DRAFT CARD ── */
        .fir-ai-card {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-top: 1px solid rgba(212,175,55,0.3);
          border-radius: 20px;
          padding: 28px;
          position: relative;
          overflow: hidden;
        }

        .fir-ai-card::before {
          content: '';
          position: absolute;
          top: 0; left: 8%; right: 8%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent);
        }

        .fir-ai-title {
          font-family: var(--serif);
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--gold-mid);
          margin: 0 0 18px;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .fir-ai-body {
          background: rgba(10,10,10,0.6);
          border: 1px solid rgba(212,175,55,0.1);
          border-radius: 12px;
          padding: 22px;
          white-space: pre-wrap;
          font-size: 0.8rem;
          color: #9A9AA6;
          line-height: 1.8;
          font-family: 'DM Mono', 'Fira Mono', monospace;
          max-height: 440px;
          overflow-y: auto;
          scrollbar-width: thin;
          scrollbar-color: rgba(212,175,55,0.3) transparent;
        }

        .fir-ai-body::-webkit-scrollbar { width: 4px; }
        .fir-ai-body::-webkit-scrollbar-thumb { background: rgba(212,175,55,0.3); border-radius: 4px; }

        /* ── PRINT CARD ── */
        .fir-print-card {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-top: 1px solid rgba(212,175,55,0.3);
          border-radius: 20px;
          padding: 36px 32px;
          position: relative;
          overflow: hidden;
        }

        .fir-print-card::before {
          content: '';
          position: absolute;
          top: 0; left: 8%; right: 8%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent);
        }

        /* Print header visible only when printing */
        .fir-print-header {
          display: none;
        }

        @media print {
          .fir-print-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
            padding-bottom: 20px;
            border-bottom: 1px solid #ccc;
          }
        }

        /* ── ACTION BAR ── */
        .fir-action-bar {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-radius: 16px;
          padding: 18px 24px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
          flex-wrap: wrap;
          position: relative;
          overflow: hidden;
        }

        .fir-action-bar::before {
          content: '';
          position: absolute;
          top: 0; left: 8%; right: 8%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.35), transparent);
        }

        /* buttons shared */
        .fir-btn {
          font-family: var(--sans);
          font-size: 0.78rem;
          font-weight: 600;
          padding: 10px 20px;
          border-radius: 10px;
          border: none;
          cursor: pointer;
          transition: all 0.22s var(--ease-gold);
          letter-spacing: 0.4px;
          text-transform: uppercase;
          display: inline-flex;
          align-items: center;
          gap: 7px;
          white-space: nowrap;
        }

        .fir-btn--ghost {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.08);
          color: var(--text-muted);
        }

        .fir-btn--ghost:hover {
          border-color: var(--border-gold-h);
          color: var(--gold-mid);
          background: rgba(212,175,55,0.04);
        }

        .fir-btn--silver {
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.1);
          color: var(--text-primary);
        }

        .fir-btn--silver:hover {
          background: rgba(255,255,255,0.1);
          border-color: rgba(255,255,255,0.2);
          transform: translateY(-1px);
        }

        .fir-btn--gold {
          background: linear-gradient(135deg, #B8960C 0%, var(--gold-main) 50%, var(--gold-bright) 100%);
          color: #0B0B0B;
          box-shadow: 0 4px 16px rgba(212,175,55,0.3);
          position: relative;
          overflow: hidden;
        }

        .fir-btn--gold::before {
          content: '';
          position: absolute;
          top: 0; left: -100%;
          width: 100%; height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
          transition: left 0.4s ease;
        }

        .fir-btn--gold:hover {
          transform: translateY(-2px) scale(1.02);
          box-shadow: 0 8px 28px rgba(212,175,55,0.45);
          filter: brightness(1.07);
        }

        .fir-btn--gold:hover::before { left: 100%; }

        .fir-action-btn-group {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }

        /* Guest notice */
        .fir-guest-notice {
          text-align: center;
          font-size: 0.8rem;
          color: var(--gold-muted);
          padding: 6px 0;
        }

        @media (max-width: 640px) {
          .fir-root { padding: 28px 16px 60px; gap: 24px; }
          .fir-wizard-card { padding: 22px 16px; }
          .fir-print-card { padding: 22px 16px; }
          .fir-action-bar { flex-direction: column; align-items: stretch; }
          .fir-action-btn-group { justify-content: flex-end; }
        }
      `}</style>

      <div className="fir-shell">
        <div className="fir-root">
          {/* Header */}
          <div>
            <p className="fir-eyebrow">AI-Powered Legal Tools</p>
            <h2 className="fir-title">FIR / Complaint Draft Generator</h2>
            <p className="fir-subtitle">
              Complete the step-by-step form below. Our AI will generate a
              legally structured FIR draft based on BNS provisions.
            </p>
          </div>

          <div className="fir-divider" />

          {/* Wizard */}
          {!generatedFIR && (
            <div className="fir-wizard-card">
              <FIRWizard onGenerate={handleGenerate} />
            </div>
          )}

          {/* Loading */}
          <AnimatePresence>
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fir-loading"
              >
                <div className="fir-spinner-wrap">
                  <div className="fir-spinner-outer" />
                  <div className="fir-spinner-inner" />
                </div>
                <p className="fir-loading-title">Generating your FIR draft…</p>
                <p className="fir-loading-sub">
                  Analysing incident details and mapping applicable BNS / BNSS
                  sections
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error */}
          {error && <div className="fir-error">⚠️ {error}</div>}

          {/* Output */}
          <AnimatePresence>
            {generatedFIR && !loading && (
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "20px",
                }}
              >
                {/* AI Draft */}
                {backendDraft && (
                  <div className="fir-ai-card">
                    <h4 className="fir-ai-title">
                      🤖 AI-Generated Legal Draft
                    </h4>
                    <div className="fir-ai-body">{backendDraft}</div>
                  </div>
                )}

                {/* Print Preview */}
                <div ref={printRef} className="fir-print-card">
                  <div className="fir-print-header">
                    <span style={{ fontWeight: 700, fontSize: "1.2rem" }}>
                      CaseIQ
                    </span>
                    <span style={{ color: "#aaa" }}>|</span>
                    <span style={{ color: "#888", fontSize: "0.85rem" }}>
                      AI-Powered Legal Knowledge Platform
                    </span>
                  </div>
                  <FIRPreview data={generatedFIR} />
                </div>

                {/* Action Bar */}
                <div className="fir-action-bar">
                  <button
                    onClick={() => {
                      setGeneratedFIR(null);
                      setBackendDraft(null);
                      setComplaintId(null);
                    }}
                    className="fir-btn fir-btn--ghost"
                  >
                    ← Start New Draft
                  </button>

                  <div className="fir-action-btn-group">
                    <button
                      onClick={handlePrint}
                      className="fir-btn fir-btn--silver"
                    >
                      🖨️ Print
                    </button>

                    <FIRDownload data={generatedFIR} />

                    {complaintId && (
                      <button
                        onClick={() =>
                          complaintsAPI.downloadPDF(
                            complaintId,
                            generatedFIR.fullName,
                          )
                        }
                        className="fir-btn fir-btn--gold"
                      >
                        ⬇️ Professional PDF
                      </button>
                    )}
                  </div>
                </div>

                {!isAuthenticated && (
                  <p className="fir-guest-notice">
                    💡 Sign in to save and access your FIR drafts from any
                    device
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </PageTransition>
  );
};

export default FIRDraftPage;
