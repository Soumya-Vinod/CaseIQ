import { useState } from "react";

const QueryInput = ({ onSend, disabled }) => {
  const [query, setQuery] = useState("");

  const handleSubmit = () => {
    if (!query.trim() || disabled) return;
    onSend(query);
    setQuery("");
  };

  return (
    <div className="flex gap-3 mt-4">
      <input
        type="text"
        placeholder="Type your legal query..."
        value={query}
        disabled={disabled}
        onChange={(e) => setQuery(e.target.value)}
        className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
      />

      <button
        onClick={handleSubmit}
        disabled={disabled}
        className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
      >
        Send
      </button>
    </div>
  );
};

export default QueryInput;
