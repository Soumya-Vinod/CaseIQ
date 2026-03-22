import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check } from 'lucide-react';

const STEPS = [
  { id: 1, title: 'Complainant', icon: '👤' },
  { id: 2, title: 'Incident', icon: '📍' },
  { id: 3, title: 'Legal', icon: '⚖️' },
  { id: 4, title: 'Suspect', icon: '🔍' },
  { id: 5, title: 'Evidence', icon: '📎' },
];

const inputClass = 'w-full rounded-xl p-3 border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] transition text-[#443627] placeholder-slate-400';
const labelClass = 'block text-sm font-medium text-[#443627] mb-1';

const FIRWizard = ({ onGenerate }) => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    fullName: '', contact: '', email: '', address: '', policeStation: '',
    incidentDate: '', incidentTime: '', incidentLocation: '', description: '',
    firType: 'Cognizable', applicableSection: '',
    suspectName: '', suspectDescription: '',
    witnessName: '', witnessContact: '',
    idProofType: '', idProofNumber: '', evidenceDetails: '',
  });

  const update = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const next = () => setStep((s) => Math.min(STEPS.length, s + 1));
  const prev = () => setStep((s) => Math.max(1, s - 1));

  const handleSubmit = () => onGenerate(formData);

  return (
    <div className="space-y-8">

      {/* Step Progress */}
      <div className="flex items-center justify-between relative">
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-slate-200 z-0" />
        <div
          className="absolute top-5 left-0 h-0.5 bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] z-0 transition-all duration-500"
          style={{ width: `${((step - 1) / (STEPS.length - 1)) * 100}%` }}
        />
        {STEPS.map((s) => (
          <div key={s.id} className="flex flex-col items-center gap-2 z-10">
            <motion.div
              animate={{
                scale: step === s.id ? 1.15 : 1,
                backgroundColor: step > s.id ? '#443627' : step === s.id ? '#8EDCE6' : '#fff',
              }}
              className={`w-10 h-10 rounded-full border-2 flex items-center justify-center text-sm font-bold transition-colors ${
                step > s.id
                  ? 'border-[#443627] text-white'
                  : step === s.id
                  ? 'border-[#8EDCE6] text-[#443627]'
                  : 'border-slate-300 text-slate-400'
              }`}
            >
              {step > s.id ? <Check size={16} className="text-white" /> : s.icon}
            </motion.div>
            <span className={`text-xs font-medium hidden sm:block ${
              step === s.id ? 'text-[#443627]' : 'text-slate-400'
            }`}>
              {s.title}
            </span>
          </div>
        ))}
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.25 }}
          className="space-y-4"
        >
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-[#443627]">👤 Complainant Information</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Full Name *</label>
                  <input name="fullName" value={formData.fullName} onChange={update} placeholder="Enter full name" required className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Contact Number *</label>
                  <input name="contact" value={formData.contact} onChange={update} placeholder="10-digit mobile number" required className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Email Address *</label>
                  <input name="email" type="email" value={formData.email} onChange={update} placeholder="your@email.com" required className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Police Station *</label>
                  <input name="policeStation" value={formData.policeStation} onChange={update} placeholder="Nearest police station" required className={inputClass} />
                </div>
              </div>
              <div>
                <label className={labelClass}>Complete Address *</label>
                <textarea name="address" value={formData.address} onChange={update} placeholder="House/Flat No, Street, City, State, PIN" rows="3" required className={inputClass} />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-[#443627]">📍 Incident Details</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Date of Incident *</label>
                  <input name="incidentDate" type="date" value={formData.incidentDate} onChange={update} required className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Time of Incident *</label>
                  <input name="incidentTime" type="time" value={formData.incidentTime} onChange={update} required className={inputClass} />
                </div>
              </div>
              <div>
                <label className={labelClass}>Location of Incident *</label>
                <input name="incidentLocation" value={formData.incidentLocation} onChange={update} placeholder="Exact location where incident occurred" required className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Detailed Description *</label>
                <textarea name="description" value={formData.description} onChange={update} placeholder="Describe the incident in detail — what happened, how it happened, sequence of events..." rows="5" required className={inputClass} />
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-[#443627]">⚖️ Legal Details</h3>
              <div>
                <label className={labelClass}>Type of Offence</label>
                <select name="firType" value={formData.firType} onChange={update} className={inputClass}>
                  <option value="Cognizable">Cognizable Offence (Police can arrest without warrant)</option>
                  <option value="Non-Cognizable">Non-Cognizable Offence (Requires magistrate order)</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Applicable BNS Section (if known)</label>
                <input name="applicableSection" value={formData.applicableSection} onChange={update} placeholder="e.g. BNS Section 103 (Murder)" className={inputClass} />
              </div>
              <div className="bg-[#D5DCF9]/50 rounded-2xl p-4 text-sm text-[#443627] space-y-2">
                <p className="font-semibold">💡 Common Sections</p>
                <div className="grid grid-cols-2 gap-2 text-xs text-[#725E54]">
                  <span>BNS 103 — Murder</span>
                  <span>BNS 115 — Assault</span>
                  <span>BNS 303 — Theft</span>
                  <span>BNS 308 — Robbery</span>
                  <span>BNS 316 — Cheating</span>
                  <span>BNS 351 — Criminal intimidation</span>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-[#443627]">🔍 Suspect & Witness</h3>
              <div>
                <label className={labelClass}>Suspect Name (if known)</label>
                <input name="suspectName" value={formData.suspectName} onChange={update} placeholder="Full name of suspect" className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Suspect Description</label>
                <textarea name="suspectDescription" value={formData.suspectDescription} onChange={update} placeholder="Physical description — age, height, clothing, identifying marks..." rows="3" className={inputClass} />
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Witness Name</label>
                  <input name="witnessName" value={formData.witnessName} onChange={update} placeholder="Witness full name" className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>Witness Contact</label>
                  <input name="witnessContact" value={formData.witnessContact} onChange={update} placeholder="Witness phone number" className={inputClass} />
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-[#443627]">📎 Identity & Evidence</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>ID Proof Type</label>
                  <select name="idProofType" value={formData.idProofType} onChange={update} className={inputClass}>
                    <option value="">Select ID type</option>
                    <option value="Aadhar">Aadhar Card</option>
                    <option value="PAN">PAN Card</option>
                    <option value="Voter ID">Voter ID</option>
                    <option value="Passport">Passport</option>
                    <option value="Driving License">Driving License</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>ID Proof Number</label>
                  <input name="idProofNumber" value={formData.idProofNumber} onChange={update} placeholder="ID number" className={inputClass} />
                </div>
              </div>
              <div>
                <label className={labelClass}>Evidence Details</label>
                <textarea name="evidenceDetails" value={formData.evidenceDetails} onChange={update} placeholder="List all evidence — CCTV footage, photographs, documents, medical reports, screenshots..." rows="4" className={inputClass} />
              </div>

              {/* Summary before submit */}
              <div className="bg-[#F8FAFC] rounded-2xl p-5 border border-[#D5DCF9] space-y-2 text-sm">
                <p className="font-semibold text-[#443627] mb-3">📋 Summary</p>
                <div className="grid grid-cols-2 gap-2 text-[#725E54]">
                  <span>Complainant: <strong className="text-[#443627]">{formData.fullName || '—'}</strong></span>
                  <span>Station: <strong className="text-[#443627]">{formData.policeStation || '—'}</strong></span>
                  <span>Date: <strong className="text-[#443627]">{formData.incidentDate || '—'}</strong></span>
                  <span>Type: <strong className="text-[#443627]">{formData.firType}</strong></span>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex justify-between items-center pt-4 border-t border-[#D5DCF9]">
        <button
          onClick={prev}
          disabled={step === 1}
          className="px-6 py-3 rounded-xl border border-[#A7B0CA] text-[#443627] hover:bg-[#D5DCF9]/40 transition disabled:opacity-30 disabled:cursor-not-allowed font-medium"
        >
          ← Previous
        </button>

        <span className="text-sm text-[#725E54]">
          Step {step} of {STEPS.length}
        </span>

        {step < STEPS.length ? (
          <button
            onClick={next}
            className="px-6 py-3 rounded-xl bg-[#443627] text-white hover:bg-[#725E54] transition font-medium shadow-md"
          >
            Next →
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            className="px-8 py-3 rounded-xl bg-gradient-to-r from-[#443627] to-[#725E54] text-white hover:opacity-90 transition font-medium shadow-md"
          >
            🤖 Generate FIR Draft
          </button>
        )}
      </div>
    </div>
  );
};

export default FIRWizard;