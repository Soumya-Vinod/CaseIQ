import { useEffect, useState } from 'react';
import RecentSearches from '../components/dashboard/RecentSearches';
import HistoryPanel from '../components/dashboard/HistoryPanel';
import { legalAPI, complaintsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const DashboardPage = () => {
  const { isAuthenticated, user } = useAuth();
  const [chatCount, setChatCount] = useState(0);
  const [firCount, setFirCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      setLoading(true);
      Promise.allSettled([
        legalAPI.getHistory(),
        complaintsAPI.getHistory(),
      ]).then(([chatRes, firRes]) => {
        if (chatRes.status === 'fulfilled') setChatCount(chatRes.value.data.count || 0);
        if (firRes.status === 'fulfilled') setFirCount(firRes.value.data.count || 0);
      }).finally(() => setLoading(false));
    } else {
      const chats = JSON.parse(localStorage.getItem('caseiq_chat_guest')) || [];
      const firs = JSON.parse(localStorage.getItem('caseiq_fir')) || [];
      setChatCount(chats.filter((m) => m.sender === 'user').length);
      setFirCount(firs.length);
    }
  }, [isAuthenticated]);

  return (
    <div className="max-w-6xl mx-auto space-y-14 pb-16">

      <div className="space-y-3">
        <h2 className="text-4xl font-bold text-[#443627]">Dashboard Overview</h2>
        <p className="text-[#725E54] text-lg">
          {isAuthenticated
            ? `Welcome back, ${user?.full_name || user?.email}`
            : 'Track your legal queries and FIR drafting activity.'}
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="relative overflow-hidden bg-[#D5DCF9] rounded-3xl p-8 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
          <div className="absolute -top-6 -right-6 w-32 h-32 bg-[#8EDCE6] opacity-30 rounded-full blur-2xl" />
          <h3 className="text-sm uppercase tracking-wide text-[#725E54] font-medium">Total Queries</h3>
          <p className="text-5xl font-bold text-[#443627] mt-4">
            {loading ? '—' : chatCount}
          </p>
          <p className="text-sm text-[#725E54] mt-2">Legal questions asked</p>
        </div>

        <div className="relative overflow-hidden bg-[#8EDCE6] rounded-3xl p-8 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
          <div className="absolute -top-6 -right-6 w-32 h-32 bg-[#D5DCF9] opacity-30 rounded-full blur-2xl" />
          <h3 className="text-sm uppercase tracking-wide text-[#443627] font-medium">FIR Drafts</h3>
          <p className="text-5xl font-bold text-[#443627] mt-4">
            {loading ? '—' : firCount}
          </p>
          <p className="text-sm text-[#443627]/80 mt-2">FIR documents generated</p>
        </div>
      </div>

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