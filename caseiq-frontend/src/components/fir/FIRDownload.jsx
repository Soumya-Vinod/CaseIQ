import jsPDF from "jspdf";

const FIRDownload = ({ data }) => {
  if (!data) return null;

  const handleDownload = () => {
    const doc = new jsPDF();

    doc.setFontSize(12);

    doc.text("To,", 10, 20);
    doc.text("The Station House Officer,", 10, 30);
    doc.text("[Police Station Name]", 10, 40);

    doc.text(
      `Subject: Complaint regarding incident at ${data.location}`,
      10,
      60
    );

    doc.text(
      `I, ${data.name}, would like to report an incident that occurred on ${data.incidentDate} at ${data.location}.`,
      10,
      80,
      { maxWidth: 180 }
    );

    doc.text("Incident Description:", 10, 100);
    doc.text(data.description, 10, 110, { maxWidth: 180 });

    doc.text("Kindly take necessary legal action.", 10, 150);
    doc.text(`Contact: ${data.contact}`, 10, 170);

    doc.save("FIR_Draft.pdf");
  };

  return (
    <button
      onClick={handleDownload}
      className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition"
    >
      Download as PDF
    </button>
  );
};

export default FIRDownload;
