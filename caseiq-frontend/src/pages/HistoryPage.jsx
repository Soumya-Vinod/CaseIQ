import { useEffect, useState } from 'react';
import { legalAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const HistoryPage = () => {
  const { isAuthenticated } = useAuth();
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      setLoading(true);
      legalAPI.getHistory()
        .then((res) => setChatHistory(res.data.results || []))
        .catch(() => loadFromLocal())
        .finally(() => setLoading(false));
    } else {
      loadFromLocal();
    }
  }, [isAuthenticated]);

  const loadFromLocal = () => {
    const saved = localStorage.getItem('caseiq_chat_guest');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const userMsgs = parsed.filter((m) => m.sender === 'user');
        setChatHistory(userMsgs.map((m, i) => ({
          id: i,
          original_query: m.text,
          created_at: new Date().toISOString(),
          status: 'local',
        })));
      } catch {}
    }
  };

  const clearLocalHistory = () => {
    localStorage.removeItem('caseiq_chat_guest');
    setChatHistory([]);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-[#443627]">Query History</h2>
        {!isAuthenticated && chatHistory.length > 0 && (
          <button onClick={clearLocalHistory}
            className="bg-red-100 text-red-700 px-4 py-2 rounded-xl hover:bg-red-200 transition text-sm">
            Clear History
          </button>
        )}
      </div>

      {!isAuthenticated && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl p-4 text-sm">
          💡 Sign in to access your full query history across all devices.
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 border-4 border-[#443627] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : chatHistory.length === 0 ? (
        <div className="bg-white rounded-2xl p-8 text-center text-[#725E54] shadow border border-[#D5DCF9]">
          No query history yet. Ask your first legal question!
        </div>
      ) : (
        <div className="space-y-4">
          {chatHistory.map((item, index) => (
            <div key={item.id || index}
              className="bg-white rounded-2xl p-5 shadow border border-[#D5DCF9] hover:shadow-md transition">
              <p className="text-[#443627] font-medium">{item.original_query}</p>
              <div className="flex justify-between items-center mt-2">
                <span className="text-xs text-[#725E54]">
                  {new Date(item.created_at).toLocaleDateString('en-IN', {
                    day: 'numeric', month: 'short', year: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                  })}
                </span>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  item.status === 'processed'
                    ? 'bg-green-100 text-green-700'
                    : item.status === 'local'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-slate-100 text-slate-600'
                }`}>
                  {item.status === 'local' ? 'Guest' : item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoryPage;