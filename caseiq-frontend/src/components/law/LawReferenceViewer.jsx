import LawCard from "./LawCard";

const LawReferenceViewer = ({ laws }) => {
  if (!laws || laws.length === 0) return null;

  return (
    <div className="space-y-4 mt-6">
      <h3 className="text-lg font-semibold">
        Relevant Legal Sections
      </h3>

      {laws.map((law, index) => (
        <LawCard
          key={index}
          section={law.section}
          title={law.title}
          description={law.description}
          punishment={law.punishment}
        />
      ))}
    </div>
  );
};

export default LawReferenceViewer;
