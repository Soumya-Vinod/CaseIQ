import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import AIResponseWindow from '../components/ai/AIResponseWindow';
import QueryInput from '../components/ai/QueryInput';
import LawReferenceViewer from '../components/law/LawReferenceViewer';
import PageTransition from '../components/ui/PageTransition';
import { legalAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';
import toast from 'react-hot-toast';
import { FileText, ChevronRight } from 'lucide-react';

// Stable session ID — persists for the browser session, resets on new chat
function getOrCreateSessionId() {
  let sid = sessionStorage.getItem('caseiq_session_id');
  if (!sid) {
    sid = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    sessionStorage.setItem('caseiq_session_id', sid);
  }
  return sid;
}

const STORAGE_KEY = 'caseiq_chat_guest';

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
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [latestLaws, setLatestLaws] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [sessionId] = useState(getOrCreateSessionId);
  const [lastAIText, setLastAIText] = useState('');
  const historyRef = useRef([]);

  const langMap = { English: 'en', Hindi: 'hi', Marathi: 'mr', Tamil: 'ta' };

  // Load saved messages
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMessages(parsed);
        if (parsed.length > 1) setShowSuggestions(false);
        const last = parsed[parsed.length - 1];
        if (last?.laws) setLatestLaws(last.laws);
        if (last?.sender === 'ai') setLastAIText(last.text || '');
        historyRef.current = parsed;
      } catch { /* ignore */ }
    } else {
      const welcome = [{
        sender: 'ai',
        text: '👋 Welcome to CaseIQ Legal Assistant.\n\nAsk any legal question about Indian law. I will provide structured, factual information based on BNS, BNSS, IPC, and CrPC.\n\n⚖️ This platform provides legal knowledge, not legal advice.',
      }];
      setMessages(welcome);
      historyRef.current = welcome;
    }
  }, []);

  // Save messages on change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
      historyRef.current = messages;
    }
  }, [messages]);

  const handleSend = useCallback(async (text) => {
    if (!text.trim()) return;
    setShowSuggestions(false);

    const userMsg = { sender: 'user', text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await legalAPI.submitQuery(
        text,
        langMap[language] || 'en',
        sessionId,
      );
      const data = res.data;

      const laws = (data.legal_sections || []).map((s) => ({
        section: `${s.act} ${s.section}`,
        title: s.title,
        description: s.relevance,
        punishment: `Confidence: ${Math.round((s.confidence || 0) * 100)}%`,
      }));

      const responseText = `${data.factual_summary}\n\n---\n${data.disclaimer}`;

      const aiMsg = {
        sender: 'ai',
        text: responseText,
        laws,
        confidence: data.confidence_score,
        historyDepth: data.history_depth || 0,
      };

      setMessages((prev) => [...prev, aiMsg]);
      setLatestLaws(laws);
      setLastAIText(responseText);

    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Failed to process query. Please try again.';
      toast.error(errorMsg);
      setMessages((prev) => [...prev, { sender: 'ai', text: `❌ ${errorMsg}` }]);
    } finally {
      setLoading(false);
    }
  }, [language, sessionId]);

  // Handle pending query from global search or home page
  useEffect(() => {
    const pending = localStorage.getItem('caseiq_pending_query');
    if (pending) {
      handleSend(pending);
      localStorage.removeItem('caseiq_pending_query');
    }
  }, [handleSend]);

  const clearChat = () => {
    // New session on clear
    const newSid = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    sessionStorage.setItem('caseiq_session_id', newSid);
    localStorage.removeItem(STORAGE_KEY);
    const welcome = [{
      sender: 'ai',
      text: '👋 Welcome to CaseIQ Legal Assistant.\n\nAsk any legal question about Indian law.\n\n⚖️ This platform provides legal knowledge, not legal advice.',
    }];
    setMessages(welcome);
    setLatestLaws([]);
    setLastAIText('');
    setShowSuggestions(true);
  };

  // Draft FIR from this conversation
  const handleDraftFIR = () => {
    // Extract what we can from the last AI response to pre-fill FIR
    const userQueries = messages
      .filter((m) => m.sender === 'user')
      .map((m) => m.text)
      .join(' ');

    localStorage.setItem('caseiq_prefill_fir', JSON.stringify({
      description: userQueries.slice(0, 500),
      from_chat: true,
      session_id: sessionId,
      timestamp: Date.now(),
    }));
    navigate('/fir-draft');
  };

  const hasUserMessages = messages.some((m) => m.sender === 'user');
  const turnCount = messages.filter((m) => m.sender === 'user').length;

  return (
    <PageTransition>
      <div className="max-w-5xl mx-auto space-y-8 pb-12">

        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <h2 className="text-4xl font-bold text-[#443627]">AI Legal Assistant</h2>
            <p className="text-[#725E54]">
              Powered by Groq Llama 3.3 — Indian Law Specialist
              {turnCount > 1 && (
                <span className="ml-3 text-xs bg-[#D5DCF9] text-[#443627] px-2 py-0.5 rounded-full font-medium">
                  {turnCount} turn conversation
                </span>
              )}
            </p>
          </div>
          {hasUserMessages && (
            <button
              onClick={clearChat}
              className="text-sm text-slate-400 hover:text-red-500 transition border border-slate-200 px-3 py-1.5 rounded-lg hover:border-red-200"
            >
              New Chat
            </button>
          )}
        </div>

        {!isAuthenticated && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl px-5 py-3 text-sm flex items-center gap-2"
          >
            💡 Sign in to save your conversation history across devices
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

        {/* Draft FIR from conversation — appears after first AI response */}
        <AnimatePresence>
          {hasUserMessages && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-2xl p-4 border border-[#D5DCF9] shadow flex items-center justify-between gap-4"
            >
              <div>
                <p className="text-sm font-semibold text-[#443627]">Ready to take action?</p>
                <p className="text-xs text-[#725E54] mt-0.5">Use this conversation to auto-fill your FIR draft</p>
              </div>
              <button
                onClick={handleDraftFIR}
                className="flex items-center gap-2 bg-[#443627] text-white px-4 py-2 rounded-xl text-sm hover:bg-[#725E54] transition font-medium shadow shrink-0"
              >
                <FileText size={14} />
                Draft FIR
                <ChevronRight size={14} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

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