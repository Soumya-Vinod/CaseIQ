const LawCard = ({ section, title, description, punishment }) => {
  return (
    <div className="bg-white shadow-md rounded-xl p-5 border space-y-2">
      <h4
        className="font-semibold text-indigo-600 dark:text-indigo-400
"
      >
        {section} - {title}
      </h4>

      <p className="text-sm text-slate-700">{description}</p>

      <p className="text-sm font-medium text-red-600">
        Punishment: {punishment}
      </p>
    </div>
  );
};

export default LawCard;
