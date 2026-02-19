const FIRPreview = ({ data }) => {
  if (!data) return null;

  return (
    <div className="bg-white shadow-md rounded-xl p-8 border space-y-6 text-sm">

      <h3 className="text-lg font-semibold text-center">
        FIRST INFORMATION REPORT (FIR)
      </h3>

      <div className="space-y-2">
        <p><strong>Police Station:</strong> {data.policeStation}</p>
        <p><strong>Type of Offence:</strong> {data.firType}</p>
        <p><strong>Applicable Section:</strong> {data.applicableSection || "To be determined by authority"}</p>
      </div>

      <hr />

      <div className="space-y-2">
        <p><strong>Complainant Name:</strong> {data.fullName}</p>
        <p><strong>Contact:</strong> {data.contact}</p>
        <p><strong>Email:</strong> {data.email}</p>
        <p><strong>Address:</strong> {data.address}</p>
        <p><strong>ID Proof:</strong> {data.idProofType} - {data.idProofNumber}</p>
      </div>

      <hr />

      <div className="space-y-2">
        <p><strong>Date of Incident:</strong> {data.incidentDate}</p>
        <p><strong>Time of Incident:</strong> {data.incidentTime}</p>
        <p><strong>Location:</strong> {data.incidentLocation}</p>
      </div>

      <hr />

      <div>
        <p><strong>Incident Description:</strong></p>
        <p className="mt-2">{data.description}</p>
      </div>

      <hr />

      <div className="space-y-2">
        <p><strong>Suspect Name:</strong> {data.suspectName || "Unknown"}</p>
        <p><strong>Suspect Description:</strong> {data.suspectDescription || "Not Provided"}</p>
      </div>

      <hr />

      <div className="space-y-2">
        <p><strong>Witness Name:</strong> {data.witnessName || "None"}</p>
        <p><strong>Witness Contact:</strong> {data.witnessContact || "None"}</p>
      </div>

      <hr />

      <div>
        <p><strong>Evidence Attached:</strong></p>
        <p>{data.evidenceDetails || "No additional evidence mentioned."}</p>
      </div>

      <hr />

      <div className="mt-6 space-y-4">
        <p>
          I hereby declare that the above information is true to the best of my knowledge.
        </p>

        <div className="flex justify-between mt-10">
          <div>
            <p><strong>Date:</strong> {new Date().toLocaleDateString()}</p>
            <p><strong>Place:</strong> {data.incidentLocation}</p>
          </div>

          <div>
            <p><strong>Signature:</strong></p>
            <p>{data.fullName}</p>
          </div>
        </div>
      </div>

    </div>
  );
};

export default FIRPreview;
