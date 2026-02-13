import { useEffect, useState } from "react";
import RecentSearches from "../components/dashboard/RecentSearches";
import HistoryPanel from "../components/dashboard/HistoryPanel";

const DashboardPage = () => {
  const [chatCount, setChatCount] = useState(0);
  const [firCount, setFirCount] = useState(0);

  useEffect(() => {
    const chats = JSON.parse(localStorage.getItem("caseiq_chat")) || [];
    const firs = JSON.parse(localStorage.getItem("caseiq_fir")) || [];

    setChatCount(chats.length);
    setFirCount(firs.length);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-14 pb-16">

      {/* HEADER */}
      <div className="space-y-3">
        <h2 className="text-4xl font-bold text-[#443627]">
          Dashboard Overview
        </h2>

        <p className="text-[#725E54] text-lg">
          Track your legal queries and FIR drafting activity in one place.
        </p>
      </div>

      {/* STATS SECTION */}
      <div className="grid md:grid-cols-2 gap-8">

        {/* CHAT CARD */}
        <div className="relative overflow-hidden bg-[#D5DCF9] rounded-3xl p-8 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

          <div className="absolute -top-6 -right-6 w-32 h-32 bg-[#8EDCE6] opacity-30 rounded-full blur-2xl" />

          <h3 className="text-sm uppercase tracking-wide text-[#725E54] font-medium">
            Total Chat Messages
          </h3>

          <p className="text-5xl font-bold text-[#443627] mt-4">
            {chatCount}
          </p>

          <p className="text-sm text-[#725E54] mt-2">
            AI conversations initiated
          </p>
        </div>

        {/* FIR CARD */}
        <div className="relative overflow-hidden bg-[#8EDCE6] rounded-3xl p-8 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

          <div className="absolute -top-6 -right-6 w-32 h-32 bg-[#D5DCF9] opacity-30 rounded-full blur-2xl" />

          <h3 className="text-sm uppercase tracking-wide text-[#443627] font-medium">
            Total FIR Drafts
          </h3>

          <p className="text-5xl font-bold text-[#443627] mt-4">
            {firCount}
          </p>

          <p className="text-sm text-[#443627]/80 mt-2">
            FIR documents generated
          </p>
        </div>

      </div>

      {/* PANELS SECTION */}
      <div className="grid md:grid-cols-2 gap-8">

        <div className="bg-white rounded-3xl p-6 shadow-md border border-[#D5DCF9] hover:shadow-lg transition">
          <RecentSearches />
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-md border border-[#D5DCF9] hover:shadow-lg transition">
          <HistoryPanel />
        </div>

      </div>

    </div>
  );
};

export default DashboardPage;
