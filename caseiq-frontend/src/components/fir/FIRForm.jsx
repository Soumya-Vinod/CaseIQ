import { useState } from "react";

const FIRForm = ({ onGenerate }) => {
  const [formData, setFormData] = useState({
    fullName: "",
    contact: "",
    email: "",
    address: "",
    policeStation: "",
    incidentDate: "",
    incidentTime: "",
    incidentLocation: "",
    description: "",
    suspectName: "",
    suspectDescription: "",
    witnessName: "",
    witnessContact: "",
    firType: "Cognizable",
    applicableSection: "",
    idProofType: "",
    idProofNumber: "",
    evidenceDetails: "",
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onGenerate(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* ---------------- COMPLAINANT INFO ---------------- */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Complainant Information</h3>

        <div className="grid md:grid-cols-2 gap-4">
          <input
            type="text"
            name="fullName"
            placeholder="Full Name *"
            value={formData.fullName}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            required
          />

          <input
            type="text"
            name="contact"
            placeholder="Contact Number *"
            value={formData.contact}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            required
          />

          <input
            type="email"
            name="email"
            placeholder="Email Address *"
            value={formData.email}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            required
          />

          <input
            type="text"
            name="policeStation"
            placeholder="Police Station *"
            value={formData.policeStation}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            required
          />
        </div>

        <textarea
          name="address"
          placeholder="Complete Address *"
          value={formData.address}
          onChange={handleChange}
          className="w-full border rounded-lg p-3 mt-4"
          rows="3"
          required
        />
      </div>

      {/* ---------------- INCIDENT DETAILS ---------------- */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Incident Details</h3>

        <div className="grid md:grid-cols-2 gap-4">
          <input
            type="date"
            name="incidentDate"
            value={formData.incidentDate}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            required
          />

          <input
            type="time"
            name="incidentTime"
            value={formData.incidentTime}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            required
          />
        </div>

        <input
          type="text"
          name="incidentLocation"
          placeholder="Location of Incident *"
          value={formData.incidentLocation}
          onChange={handleChange}
          className="w-full border rounded-lg p-3 mt-4"
          required
        />

        <textarea
          name="description"
          placeholder="Detailed Description of Incident *"
          value={formData.description}
          onChange={handleChange}
          className="w-full border rounded-lg p-3 mt-4"
          rows="4"
          required
        />
      </div>

      {/* ---------------- LEGAL DETAILS ---------------- */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Legal Details</h3>

        <select
          name="firType"
          value={formData.firType}
          onChange={handleChange}
          className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
        >
          <option value="Cognizable">Cognizable Offence</option>
          <option value="Non-Cognizable">Non-Cognizable Offence</option>
        </select>

        <input
          type="text"
          name="applicableSection"
          placeholder="Applicable BNS Section (if known)"
          value={formData.applicableSection}
          onChange={handleChange}
          className="w-full border rounded-lg p-3 mt-4"
        />
      </div>

      {/* ---------------- SUSPECT INFO ---------------- */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Suspect Information</h3>

        <input
          type="text"
          name="suspectName"
          placeholder="Suspect Name (if known)"
          value={formData.suspectName}
          onChange={handleChange}
          className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
        />

        <textarea
          name="suspectDescription"
          placeholder="Suspect Description (appearance, clothing, etc.)"
          value={formData.suspectDescription}
          onChange={handleChange}
          className="w-full border rounded-lg p-3 mt-4"
          rows="3"
        />
      </div>

      {/* ---------------- WITNESS INFO ---------------- */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Witness Information</h3>

        <div className="grid md:grid-cols-2 gap-4">
          <input
            type="text"
            name="witnessName"
            placeholder="Witness Name"
            value={formData.witnessName}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />

          <input
            type="text"
            name="witnessContact"
            placeholder="Witness Contact"
            value={formData.witnessContact}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>
      </div>

      {/* ---------------- ID & EVIDENCE ---------------- */}
      <div>
        <h3 className="text-lg font-semibold mb-4">
          Identification & Evidence
        </h3>

        <div className="grid md:grid-cols-2 gap-4">
          <input
            type="text"
            name="idProofType"
            placeholder="ID Proof Type (Aadhar / PAN / DL)"
            value={formData.idProofType}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />

          <input
            type="text"
            name="idProofNumber"
            placeholder="ID Proof Number"
            value={formData.idProofNumber}
            onChange={handleChange}
            className="w-full rounded-lg p-3 border border-slate-300 dark:border-slate-600 
bg-white dark:bg-slate-900 
text-slate-800 dark:text-slate-200 
placeholder-slate-400 dark:placeholder-slate-500 
focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>

        <textarea
          name="evidenceDetails"
          placeholder="Evidence attached (CCTV, photos, documents...)"
          value={formData.evidenceDetails}
          onChange={handleChange}
          className="w-full border rounded-lg p-3 mt-4"
          rows="3"
        />
      </div>

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition"
        >
          Generate FIR Draft
        </button>
      </div>
    </form>
  );
};

export default FIRForm;
