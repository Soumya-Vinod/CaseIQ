import { useEffect, useState } from "react";

const HistoryPanel = () => {
  const [history, setHistory] = useState([]);

 useEffect(() => {
  const chats = JSON.parse(localStorage.getItem("caseiq_chat")) || [];
  const firs = JSON.parse(localStorage.getItem("caseiq_fir")) || [];

  // 🔥 Only user messages
  const userChats = chats.filter(
    (msg) => msg.sender === "user"
  );

  const combinedHistory = [
    ...userChats.map((msg) => ({
      type: "Chat",
      text: msg.text,
    })),
    ...firs.map((fir) => ({
      type: "FIR",
      text: `FIR drafted for ${fir.fullName}`,
    })),
  ];

  setHistory(combinedHistory.slice(-8).reverse());
}, []);

  return (
    <div className="bg-white shadow-md rounded-xl p-6 border">
      <h3 className="text-lg font-semibold mb-4">
        Activity History
      </h3>

      {history.length === 0 ? (
        <p className="text-slate-500 text-sm">
          No history available.
        </p>
      ) : (
        <ul className="space-y-3">
          {history.map((item, index) => (
            <li
              key={index}
              className="text-sm flex justify-between bg-slate-50 p-2 rounded-lg"
            >
              <span className="font-medium">{item.type}</span>
              <span className="text-slate-600 truncate max-w-[200px]">
                {item.text}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default HistoryPanel;
