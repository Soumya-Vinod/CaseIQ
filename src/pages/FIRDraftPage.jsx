import { useState, useEffect } from "react";
import FIRForm from "../components/fir/FIRForm";
import FIRPreview from "../components/fir/FIRPreview";
import FIRDownload from "../components/fir/FIRDownload";

const FIRDraftPage = () => {
  const [generatedFIR, setGeneratedFIR] = useState(null);

  // Save FIR drafts
  useEffect(() => {
    if (generatedFIR) {
      const existing = JSON.parse(localStorage.getItem("caseiq_fir")) || [];
      const updated = [...existing, generatedFIR];
      localStorage.setItem("caseiq_fir", JSON.stringify(updated));
    }
  }, [generatedFIR]);

  return (
    <div className="max-w-5xl mx-auto space-y-14 pb-16">

      {/* HEADER SECTION */}
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold text-[#443627]">
          FIR / Complaint Draft Generator
        </h2>

        <p className="text-lg text-[#725E54] max-w-3xl mx-auto">
          Provide accurate details below to generate a structured,
          legally formatted FIR draft ready for submission.
        </p>
      </div>

      {/* FORM SECTION */}
      <div
        className="
          bg-[#D5DCF9]
          rounded-3xl
          p-10
          shadow-lg
          border border-[#A7B0CA]
          transition
        "
      >
        <div className="flex items-center gap-3 mb-6">
          <span className="text-2xl">📝</span>
          <h3 className="text-xl font-semibold text-[#443627]">
            Enter Incident Details
          </h3>
        </div>

        <FIRForm onGenerate={setGeneratedFIR} />
      </div>

      {/* PREVIEW SECTION */}
      {generatedFIR && (
        <div
          className="
            bg-white
            rounded-3xl
            p-10
            shadow-xl
            border border-[#D5DCF9]
            animate-fadeIn
            transition
          "
        >
          <div className="flex items-center gap-3 mb-6">
            <span className="text-2xl">📄</span>
            <h3 className="text-xl font-semibold text-[#443627]">
              Generated FIR Preview
            </h3>
          </div>

          <FIRPreview data={generatedFIR} />

          {/* DOWNLOAD BUTTON */}
          <div className="flex justify-end mt-8">
            <button
              className="
                bg-[#443627]
                text-white
                px-6
                py-3
                rounded-xl
                hover:bg-[#725E54]
                transition-all
                duration-300
                shadow-md
                hover:shadow-lg
                hover:-translate-y-0.5
              "
            >
              <FIRDownload data={generatedFIR} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FIRDraftPage;
