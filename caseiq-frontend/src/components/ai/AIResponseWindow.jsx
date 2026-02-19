import { useEffect, useRef } from "react";
import { useSettings } from "../../context/SettingsContext";

const AIResponseWindow = ({ messages = [], loading }) => {
  const { darkMode } = useSettings();
  const bottomRef = useRef(null);

  // Auto scroll when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div
      className={`h-[500px] overflow-y-auto rounded-xl p-6 transition-colors duration-300 border shadow-lg ${
        darkMode
          ? "bg-slate-800 border-slate-700"
          : "bg-white border-slate-200"
      }`}
    >
      {/* Empty State */}
      {messages.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
          <div className="text-5xl">⚖️</div>

          <h3 className="text-lg font-semibold text-slate-600">
            Welcome to CaseIQ AI Assistant
          </h3>

          <p className="text-sm text-slate-400 max-w-md">
            Ask any legal question related to FIR filing, BNS sections,
            rights after arrest, or criminal law procedures.
          </p>
        </div>
      )}

      {/* Messages */}
      <div className="space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[75%] px-4 py-3 rounded-xl text-sm ${
                msg.sender === "user"
                  ? "bg-indigo-600 text-white"
                  : darkMode
                  ? "bg-slate-700 text-slate-200"
                  : "bg-slate-100 text-slate-800"
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-start">
            <div
              className={`px-4 py-3 rounded-xl text-sm animate-pulse ${
                darkMode
                  ? "bg-slate-700 text-slate-300"
                  : "bg-slate-200 text-slate-600"
              }`}
            >
              AI is typing...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default AIResponseWindow;
