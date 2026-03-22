import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AIResponseWindow from '../components/ai/AIResponseWindow';
import QueryInput from '../components/ai/QueryInput';
import LawReferenceViewer from '../components/law/LawReferenceViewer';
import PageTransition from '../components/ui/PageTransition';
import { legalAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';
import toast from 'react-hot-toast';

const GUEST_STORAGE_KEY = 'caseiq_chat_guest';

const SUGGESTED_QUERIES = [
  { label: '🚨 Rights during arrest', query: 'What are my rights when I am arrested by police in India?' },
  { label: '📄 How to file FIR', query: 'What is the procedure to file an FIR at a police station?' },
  { label: '💼 Employer not paying salary', query: 'My employer has not paid salary for 3 months. What legal action can I take?' },
  { label: '🏠 Property dispute', query: 'My landlord is refusing to return my security deposit. What are my legal options?' },
  { label: '📱 Cybercrime victim', query: 'I was cheated online and lost money. How do I report cybercrime in India?' },
  { label: '⚖️ Bail process', query: 'How does bail work in India and what are the types of bail available?' },
  { label: '👩 Domestic violence', query: 'What legal protections are available for women facing domestic violence in India?' },
  { label: '🚗 Road accident rights', query: 'I was injured in a road accident. What compensation am I entitled to under Indian law?' },
];

const ChatPage = () => {
  const { isAuthenticated } = useAuth();
  const { language } = useSettings();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [latestLaws, setLatestLaws] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const langMap = { English: 'en', Hindi: 'hi', Marathi: 'mr', Tamil: 'ta' };

  useEffect(() => {
    const saved = localStorage.getItem(GUEST_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMessages(parsed);
        if (parsed.length > 1) setShowSuggestions(false);
        const last = parsed[parsed.length - 1];
        if (last?.laws) setLatestLaws(last.laws);
      } catch {}
    } else {
      setMessages([{
        sender: 'ai',
        text: '👋 Welcome to CaseIQ Legal Assistant.\n\nAsk any legal question about Indian law. I will provide structured, factual information based on BNS, BNSS, IPC, and CrPC.\n\n⚖️ This platform provides legal knowledge, not legal advice.',
      }]);
    }
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(messages));
    }
  }, [messages]);

  const handleSend = useCallback(async (text) => {
    if (!text.trim()) return;
    setShowSuggestions(false);
    setMessages((prev) => [...prev, { sender: 'user', text }]);
    setLoading(true);

    try {
      const res = await legalAPI.submitQuery(text, langMap[language] || 'en');
      const data = res.data;

      const laws = (data.legal_sections || []).map((s) => ({
        section: `${s.act} ${s.section}`,
        title: s.title,
        description: s.relevance,
        punishment: `Confidence: ${Math.round((s.confidence || 0) * 100)}%`,
      }));

      const aiMessage = {
        sender: 'ai',
        text: `${data.factual_summary}\n\n---\n${data.disclaimer}`,
        laws,
        confidence: data.confidence_score,
      };

      setMessages((prev) => [...prev, aiMessage]);
      setLatestLaws(laws);
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Failed to process query. Please try again.';
      toast.error(errorMsg);
      setMessages((prev) => [...prev, { sender: 'ai', text: `❌ ${errorMsg}` }]);
    } finally {
      setLoading(false);
    }
  }, [language]);

  useEffect(() => {
    const pending = localStorage.getItem('caseiq_pending_query');
    if (pending) {
      handleSend(pending);
      localStorage.removeItem('caseiq_pending_query');
    }
  }, [handleSend]);

  const clearChat = () => {
    localStorage.removeItem(GUEST_STORAGE_KEY);
    setMessages([{
      sender: 'ai',
      text: '👋 Welcome to CaseIQ Legal Assistant.\n\nAsk any legal question about Indian law.\n\n⚖️ This platform provides legal knowledge, not legal advice.',
    }]);
    setLatestLaws([]);
    setShowSuggestions(true);
  };

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto space-y-8 pb-12">

        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <h2 className="text-4xl font-bold text-[#443627]">AI Legal Assistant</h2>
            <p className="text-[#725E54]">Powered by Groq Llama 3.3 — Indian Law Specialist</p>
          </div>
          {messages.length > 1 && (
            <button
              onClick={clearChat}
              className="text-sm text-slate-400 hover:text-red-500 transition border border-slate-200 px-3 py-1.5 rounded-lg hover:border-red-200"
            >
              Clear Chat
            </button>
          )}
        </div>

        {!isAuthenticated && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl px-5 py-3 text-sm flex items-center gap-2"
          >
            💡 Sign in to save your query history and access it from any device
          </motion.div>
        )}

        {/* Suggested Queries */}
        <AnimatePresence>
          {showSuggestions && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-3"
            >
              <p className="text-sm font-medium text-[#725E54]">💡 Common legal questions:</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {SUGGESTED_QUERIES.map((sq, i) => (
                  <motion.button
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => handleSend(sq.query)}
                    disabled={loading}
                    className="text-left text-xs bg-white border border-[#D5DCF9] text-[#443627] px-3 py-2.5 rounded-xl hover:bg-[#D5DCF9] hover:border-[#A7B0CA] transition shadow-sm disabled:opacity-50"
                  >
                    {sq.label}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat Window */}
        <div className="bg-gradient-to-br from-[#D5DCF9]/60 to-[#8EDCE6]/60 backdrop-blur-md rounded-3xl shadow-xl p-6 border border-white/40">
          <AIResponseWindow messages={messages} loading={loading} />
          <div className="mt-4">
            <QueryInput onSend={handleSend} disabled={loading} />
          </div>
        </div>

        {/* Law References */}
        <AnimatePresence>
          {latestLaws.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gradient-to-br from-[#A7B0CA]/60 to-[#D5DCF9]/60 backdrop-blur-md rounded-3xl shadow-lg p-6 border border-white/40"
            >
              <h3 className="text-xl font-semibold text-[#443627] mb-4">
                📚 Relevant Legal Sections
              </h3>
              <LawReferenceViewer laws={latestLaws} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageTransition>
  );
};

export default ChatPage;