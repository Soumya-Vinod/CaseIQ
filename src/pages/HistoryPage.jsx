import { useEffect, useState } from "react";

const HistoryPage = () => {
  const [chatHistory, setChatHistory] = useState([]);

  useEffect(() => {
    const savedMessages = localStorage.getItem("caseiq_chat");
    if (savedMessages) {
      setChatHistory(JSON.parse(savedMessages));
    }
  }, []);

  const clearHistory = () => {
    localStorage.removeItem("caseiq_chat");
    setChatHistory([]);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h2
        className="text-3xl font-bold text-indigo-600 dark:text-indigo-400
"
      >
        Chat History
      </h2>

      {chatHistory.length === 0 ? (
        <p className="text-slate-500">No chat history available.</p>
      ) : (
        <div className="bg-white shadow-md rounded-xl p-6 border space-y-4">
          {chatHistory.map((msg, index) => (
            <div key={index}>
              <span className="font-semibold">
                {msg.sender === "user" ? "You" : "AI"}:
              </span>{" "}
              {msg.text}
            </div>
          ))}
        </div>
      )}

      {chatHistory.length > 0 && (
        <button
          onClick={clearHistory}
          className="bg-red-600 text-white px-5 py-2 rounded-lg hover:bg-red-700 transition"
        >
          Clear History
        </button>
      )}
    </div>
  );
};

export default HistoryPage;
