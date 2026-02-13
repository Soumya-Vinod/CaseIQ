const legalTopics = [
  {
    title: "Right to File an FIR",
    content:
      "Every citizen has the right to file an FIR at any police station, including Zero FIR in case of jurisdiction issues.",
  },
  {
    title: "Rights of an Arrested Person",
    content:
      "An arrested person has the right to remain silent and the right to legal representation.",
  },
  {
    title: "Zero FIR",
    content:
      "Zero FIR can be filed at any police station regardless of jurisdiction and later transferred.",
  },
  {
    title: "Protection for Women",
    content:
      "Women have special legal protections under various provisions including mandatory presence of female officers.",
  },
];

const AwarenessCards = () => {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {legalTopics.map((topic, index) => (
        <div
          key={index}
          className="bg-white shadow-md rounded-xl p-6 border hover:shadow-lg transition"
        >
          <h3
            className="font-semibold text-indigo-600 dark:text-indigo-400
 mb-2"
          >
            {topic.title}
          </h3>
          <p className="text-sm text-slate-600">{topic.content}</p>
        </div>
      ))}
    </div>
  );
};

export default AwarenessCards;
