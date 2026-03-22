import { useState, useRef } from 'react';
import { useReactToPrint } from 'react-to-print';
import { motion, AnimatePresence } from 'framer-motion';
import FIRWizard from '../components/fir/FIRWizard';
import FIRPreview from '../components/fir/FIRPreview';
import FIRDownload from '../components/fir/FIRDownload';
import PageTransition from '../components/ui/PageTransition';
import { complaintsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const FIRDraftPage = () => {
  const { isAuthenticated } = useAuth();
  const [generatedFIR, setGeneratedFIR] = useState(null);
  const [backendDraft, setBackendDraft] = useState(null);
  const [complaintId, setComplaintId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const printRef = useRef();

  const handlePrint = useReactToPrint({ content: () => printRef.current });

  const handleGenerate = async (formData) => {
    setGeneratedFIR(formData);
    setError('');
    setLoading(true);

    const existing = JSON.parse(localStorage.getItem('caseiq_fir')) || [];
    localStorage.setItem('caseiq_fir', JSON.stringify([...existing, formData]));

    try {
      const res = await complaintsAPI.generateDraft({
        complaint_type: 'fir',
        complainant_name: formData.fullName,
        complainant_address: formData.address,
        complainant_phone: formData.contact,
        police_station_name: formData.policeStation,
        incident_date: formData.incidentDate,
        incident_location: formData.incidentLocation,
        incident_description: formData.description,
        accused_details: `${formData.suspectName || ''} — ${formData.suspectDescription || ''}`.trim(),
        witnesses: formData.witnessName ? `${formData.witnessName} (${formData.witnessContact || 'No contact'})` : '',
        evidence_description: formData.evidenceDetails || '',
        relief_sought: 'Registration of FIR, arrest of accused, and necessary legal action.',
        applicable_sections: formData.applicableSection ? [formData.applicableSection] : [],
        language: 'en',
      });
      setBackendDraft(res.data.generated_draft);
      setComplaintId(res.data.complaint_id);
      toast.success('FIR draft generated successfully!');
    } catch (err) {
      const msg = err.response?.data?.error || 'AI draft generation failed. Basic PDF still available.';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto space-y-12 pb-16">

        {/* Header */}
        <div className="text-center space-y-3">
          <h2 className="text-4xl font-bold text-[#443627]">FIR / Complaint Draft Generator</h2>
          <p className="text-lg text-[#725E54] max-w-2xl mx-auto">
            Complete the step-by-step form below. Our AI will generate a legally structured FIR draft.
          </p>
        </div>

        {/* Wizard Form */}
        {!generatedFIR && (
          <div className="bg-white rounded-3xl p-10 shadow-xl border border-[#D5DCF9]">
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
              className="flex flex-col items-center gap-4 py-12"
            >
              <div className="w-14 h-14 border-4 border-[#443627] border-t-transparent rounded-full animate-spin" />
              <p className="text-[#725E54] font-medium">AI is generating your FIR draft...</p>
              <p className="text-sm text-slate-400">Analysing incident details and mapping to applicable BNS sections</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        {error && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl p-4 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* Preview */}
        <AnimatePresence>
          {generatedFIR && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* AI Draft */}
              {backendDraft && (
                <div className="bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6]/40 rounded-3xl p-8 border border-[#A7B0CA] shadow-lg">
                  <h4 className="font-bold text-[#443627] mb-4 text-lg flex items-center gap-2">
                    🤖 AI-Generated Legal Draft
                  </h4>
                  <div className="bg-white/70 rounded-2xl p-6 whitespace-pre-wrap text-sm text-[#443627] leading-relaxed font-mono">
                    {backendDraft}
                  </div>
                </div>
              )}

              {/* Print View */}
              <div ref={printRef} className="bg-white rounded-3xl p-10 shadow-xl border border-[#D5DCF9] print:shadow-none print:border-none">
                <div className="hidden print:flex items-center justify-center gap-3 mb-8 pb-6 border-b">
                  <span className="text-2xl font-bold text-[#443627]">CaseIQ</span>
                  <span className="text-slate-400">|</span>
                  <span className="text-slate-500 text-sm">AI-Powered Legal Knowledge Platform</span>
                </div>
                <FIRPreview data={generatedFIR} />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap justify-between items-center gap-4 bg-white rounded-2xl p-5 border border-[#D5DCF9] shadow">
                <button
                  onClick={() => { setGeneratedFIR(null); setBackendDraft(null); setComplaintId(null); }}
                  className="border border-[#A7B0CA] text-[#443627] px-5 py-2.5 rounded-xl hover:bg-[#D5DCF9]/40 transition text-sm font-medium"
                >
                  ← Start New Draft
                </button>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handlePrint}
                    className="bg-[#A7B0CA] text-white px-5 py-2.5 rounded-xl hover:opacity-90 transition text-sm font-medium shadow"
                  >
                    🖨️ Print
                  </button>

                  <FIRDownload data={generatedFIR} />

                  {complaintId && (
                    <button
                      onClick={() => complaintsAPI.downloadPDF(complaintId, generatedFIR.fullName)}
                      className="bg-[#443627] text-white px-5 py-2.5 rounded-xl hover:bg-[#725E54] transition text-sm font-medium shadow"
                    >
                      ⬇️ Professional PDF
                    </button>
                  )}
                </div>
              </div>

              {!isAuthenticated && (
                <p className="text-center text-sm text-amber-600">
                  💡 Sign in to save and access your FIR drafts from any device
                </p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
};

export default FIRDraftPage;