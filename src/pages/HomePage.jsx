import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const HomePage = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [recentQueries, setRecentQueries] = useState([]);

  useEffect(() => {
    const savedChat = JSON.parse(localStorage.getItem("caseiq_chat")) || [];
    const userMessages = savedChat
      .filter((msg) => msg.sender === "user")
      .map((msg) => msg.text)
      .slice(-4)
      .reverse();

    setRecentQueries(userMessages);
  }, []);

  const handleSubmit = () => {
    if (!query.trim()) return;
    localStorage.setItem("caseiq_pending_query", query);
    setQuery("");
    navigate("/chat");
  };

  const handleRecentClick = (text) => {
    localStorage.setItem("caseiq_pending_query", text);
    navigate("/chat");
  };

  return (
    <div className="max-w-6xl mx-auto space-y-16 pb-20">

      {/* HERO */}
      <div className="text-center space-y-6">
        <h1 className="text-4xl md:text-5xl font-bold text-[#443627]">
          Welcome to CaseIQ
        </h1>

        <p className="text-lg text-[#725E54] max-w-2xl mx-auto">
          A calm and intelligent legal companion helping you understand your
          rights, draft FIRs, and explore Indian criminal law.
        </p>
      </div>

      {/* FEATURE CARDS */}
      <div className="grid md:grid-cols-4 gap-6">

        <div
          onClick={() => navigate("/chat")}
          className="bg-[#8EDCE6] hover:scale-[1.03] transition-transform duration-300 rounded-2xl p-6 cursor-pointer shadow-md"
        >
          <div className="text-3xl mb-3">💬</div>
          <h3 className="font-semibold text-[#443627]">Ask a Query</h3>
          <p className="text-sm text-[#443627]/80 mt-2">
            Instant legal explanations powered by AI.
          </p>
        </div>

        <div
          onClick={() => navigate("/fir-draft")}
          className="bg-[#D5DCF9] hover:scale-[1.03] transition-transform duration-300 rounded-2xl p-6 cursor-pointer shadow-md"
        >
          <div className="text-3xl mb-3">📄</div>
          <h3 className="font-semibold text-[#443627]">Draft FIR</h3>
          <p className="text-sm text-[#443627]/80 mt-2">
            Generate structured FIR drafts easily.
          </p>
        </div>

        <div
          onClick={() => navigate("/education")}
          className="bg-[#A7B0CA] hover:scale-[1.03] transition-transform duration-300 rounded-2xl p-6 cursor-pointer shadow-md"
        >
          <div className="text-3xl mb-3">🛡️</div>
          <h3 className="font-semibold text-white">Know Your Rights</h3>
          <p className="text-sm text-white/90 mt-2">
            Understand your constitutional protections.
          </p>
        </div>

        <div
          onClick={() => navigate("/education")}
          className="bg-[#725E54] hover:scale-[1.03] transition-transform duration-300 rounded-2xl p-6 cursor-pointer shadow-md"
        >
          <div className="text-3xl mb-3">📚</div>
          <h3 className="font-semibold text-white">Legal Learning</h3>
          <p className="text-sm text-white/90 mt-2">
            Learn BNS / BNSS concepts simply.
          </p>
        </div>
      </div>

      {/* QUERY SECTION */}
      <div className="bg-white rounded-3xl p-8 shadow-lg border border-[#D5DCF9]">
        <h2 className="text-xl font-semibold text-[#443627] mb-4">
          Ask Your Legal Query
        </h2>

        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type your legal question here..."
          rows="4"
          className="w-full rounded-xl border border-[#A7B0CA] focus:ring-2 focus:ring-[#8EDCE6] focus:outline-none p-4 bg-[#F8FAFC] transition"
        />

        <div className="flex justify-between items-center mt-4">
          <button
            onClick={handleSubmit}
            className="bg-[#443627] text-white px-6 py-2 rounded-xl hover:bg-[#725E54] transition"
          >
            Submit Query
          </button>

          <span className="text-sm text-[#725E54]">
            Language: English
          </span>
        </div>
      </div>

      {/* BOTTOM SECTION */}
      <div className="grid md:grid-cols-2 gap-8">

        {/* RECENT QUERIES */}
        <div className="bg-[#F4F6FA] rounded-2xl p-6 shadow-md border border-[#D5DCF9]">
          <h3 className="font-semibold text-[#443627] mb-4">
            Recent Queries
          </h3>

          {recentQueries.length === 0 ? (
            <p className="text-sm text-[#725E54]">
              No recent queries yet.
            </p>
          ) : (
            <ul className="space-y-3">
              {recentQueries.map((item, index) => (
                <li
                  key={index}
                  onClick={() => handleRecentClick(item)}
                  className="p-3 rounded-lg bg-white hover:bg-[#D5DCF9] transition cursor-pointer text-[#443627]"
                >
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* QUICK ACTIONS */}
        <div className="bg-[#F4F6FA] rounded-2xl p-6 shadow-md border border-[#D5DCF9] space-y-4">
          <h3 className="font-semibold text-[#443627]">
            Quick Actions
          </h3>

          <button
            onClick={() => navigate("/fir-draft")}
            className="w-full bg-[#8EDCE6] text-[#443627] py-2 rounded-xl hover:opacity-90 transition"
          >
            Draft a New FIR
          </button>

          <button
            onClick={() => navigate("/education")}
            className="w-full bg-[#A7B0CA] text-white py-2 rounded-xl hover:opacity-90 transition"
          >
            Learn About Your Rights
          </button>

          <button
            onClick={() => navigate("/education")}
            className="w-full bg-[#443627] text-white py-2 rounded-xl hover:bg-[#725E54] transition"
          >
            Understand BNS / BNSS Basics
          </button>
        </div>

      </div>
    </div>
  );
};

export default HomePage;
