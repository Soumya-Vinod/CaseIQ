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

function getOrCreateSessionId() {
  let sid = sessionStorage.getItem('caseiq_session_id');
  if (!sid) {
    sid = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    sessionStorage.setItem('caseiq_session_id', sid);
  }
  return sid;
}

const STORAGE_KEY = 'caseiq_chat_guest';

const ChatPage = () => {
  const { isAuthenticated } = useAuth();
  const { language } = useSettings();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [latestLaws, setLatestLaws] = useState([]);
  const [sessionId] = useState(getOrCreateSessionId);
  const [lastAIText, setLastAIText] = useState('');
  const historyRef = useRef([]);

  const langMap = { English: 'en', Hindi: 'hi', Marathi: 'mr', Tamil: 'ta' };

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMessages(parsed);
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

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
      historyRef.current = messages;
    }
  }, [messages]);

  const handleSend = useCallback(async (text) => {
    if (!text.trim()) return;

    const userMsg = { sender: 'user', text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await legalAPI.submitQuery(text, langMap[language] || 'en', sessionId);
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

  useEffect(() => {
    const pending = localStorage.getItem('caseiq_pending_query');
    if (pending) {
      handleSend(pending);
      localStorage.removeItem('caseiq_pending_query');
    }
  }, [handleSend]);

  const clearChat = () => {
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
  };

  const handleDraftFIR = () => {
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
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');

        html, body, #root {
          background-color: #0B0B0B !important;
        }

        .cp-page-shell {
          min-height: 100vh;
          width: 100%;
          background: #0B0B0B;
          background-image:
            radial-gradient(ellipse 80% 50% at 50% -10%, rgba(212,175,55,0.12) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 80%, rgba(184,150,12,0.06) 0%, transparent 55%),
            radial-gradient(ellipse 40% 30% at 10% 70%, rgba(212,175,55,0.04) 0%, transparent 50%);
          position: relative;
        }

        .cp-page-shell::after {
          content: '';
          position: fixed;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
          pointer-events: none;
          z-index: 0;
          opacity: 0.4;
        }

        .cp-root {
          font-family: 'DM Sans', sans-serif;
          max-width: 920px;
          margin: 0 auto;
          padding: 40px 24px 80px;
          display: flex;
          flex-direction: column;
          gap: 28px;
          position: relative;
          z-index: 1;
        }

        .cp-root::before {
          content: '';
          position: absolute;
          top: 60px;
          left: -1px;
          width: 2px;
          height: 120px;
          background: linear-gradient(180deg, transparent, rgba(212,175,55,0.6), transparent);
          border-radius: 2px;
        }

        /* ── HEADER ── */
        .cp-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding-bottom: 8px;
        }

        .cp-header-left {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .cp-heading-eyebrow {
          font-size: 0.7rem;
          font-weight: 500;
          letter-spacing: 3px;
          text-transform: uppercase;
          color: #9A7D3A;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .cp-heading-eyebrow::before {
          content: '';
          display: inline-block;
          width: 28px;
          height: 1px;
          background: linear-gradient(90deg, transparent, #9A7D3A);
        }

        .cp-heading {
          font-family: 'Cormorant Garamond', serif;
          font-size: clamp(2rem, 4.5vw, 3rem);
          font-weight: 700;
          font-style: italic;
          background: linear-gradient(135deg, #D4AF37 0%, #FFD700 45%, #C5A46D 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          filter: drop-shadow(0 0 24px rgba(212,175,55,0.3));
          line-height: 1.05;
          margin: 0;
          letter-spacing: -0.5px;
        }

        .cp-subtitle {
          font-size: 0.8rem;
          color: #6B6B75;
          font-weight: 400;
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
          letter-spacing: 0.2px;
        }

        .cp-subtitle-dot {
          width: 3px;
          height: 3px;
          border-radius: 50%;
          background: #4A4A52;
          display: inline-block;
        }

        .cp-turn-badge {
          background: rgba(212,175,55,0.1);
          border: 1px solid rgba(212,175,55,0.25);
          color: #C9A84C;
          font-size: 0.68rem;
          font-weight: 600;
          padding: 3px 12px;
          border-radius: 20px;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }

        .cp-btn-newchat {
          font-family: 'DM Sans', sans-serif;
          font-size: 0.78rem;
          font-weight: 500;
          color: #7A7A82;
          background: transparent;
          border: 1px solid rgba(255,255,255,0.07);
          padding: 9px 18px;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.25s ease;
          letter-spacing: 0.3px;
          position: relative;
          overflow: hidden;
        }

        .cp-btn-newchat::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(212,175,55,0.06), transparent);
          opacity: 0;
          transition: opacity 0.25s ease;
        }

        .cp-btn-newchat:hover {
          color: #C9A84C;
          border-color: rgba(212,175,55,0.4);
          box-shadow: 0 0 20px rgba(212,175,55,0.1), inset 0 0 20px rgba(212,175,55,0.03);
        }

        .cp-btn-newchat:hover::before { opacity: 1; }

        /* ── SIGN-IN BANNER ── */
        .cp-signin-banner {
          background: rgba(212,175,55,0.04);
          border: 1px solid rgba(212,175,55,0.15);
          border-left: 3px solid rgba(212,175,55,0.5);
          color: #9A7D3A;
          border-radius: 12px;
          padding: 12px 18px;
          font-size: 0.82rem;
          display: flex;
          align-items: center;
          gap: 10px;
          letter-spacing: 0.1px;
        }

        /* ── CHAT CONTAINER ── */
        .cp-chat-container {
          background: rgba(12, 10, 4, 0.96);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(212,175,55,0.18);
          border-top: 1px solid rgba(212,175,55,0.28);
          border-radius: 20px;
          padding: 24px;
          box-shadow:
            0 1px 0 rgba(212,175,55,0.15) inset,
            0 -1px 0 rgba(0,0,0,0.5) inset,
            0 20px 60px rgba(0,0,0,0.8),
            0 4px 24px rgba(0,0,0,0.6);
          position: relative;
          overflow: hidden;
        }

        .cp-chat-container::before {
          content: '';
          position: absolute;
          top: 0; right: 0;
          width: 160px; height: 160px;
          background: radial-gradient(circle at top right, rgba(212,175,55,0.06), transparent 70%);
          pointer-events: none;
        }

        .cp-chat-container::after {
          content: '';
          position: absolute;
          bottom: 0; left: 0;
          width: 100px; height: 100px;
          background: radial-gradient(circle at bottom left, rgba(212,175,55,0.04), transparent 70%);
          pointer-events: none;
        }

        .cp-query-input-wrap {
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid rgba(212,175,55,0.1);
          position: relative;
        }

        .cp-query-input-wrap::before {
          content: '';
          position: absolute;
          top: -1px; left: 50%;
          transform: translateX(-50%);
          width: 60px; height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.6), transparent);
        }

        /* ── FIR CARD ── */
        .cp-fir-card {
          background: rgba(12, 10, 4, 0.96);
          border: 1px solid rgba(212,175,55,0.2);
          border-radius: 16px;
          padding: 20px 26px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          box-shadow:
            0 4px 32px rgba(0,0,0,0.6),
            0 1px 0 rgba(212,175,55,0.15) inset;
          flex-wrap: wrap;
          position: relative;
          overflow: hidden;
        }

        .cp-fir-card::before {
          content: '';
          position: absolute;
          left: 0; top: 0; bottom: 0;
          width: 3px;
          background: linear-gradient(180deg, transparent, #D4AF37, transparent);
        }

        .cp-fir-card-left p:first-child {
          font-family: 'Cormorant Garamond', serif;
          font-size: 1.05rem;
          font-weight: 600;
          color: #E5E5E5;
          margin: 0 0 4px;
          letter-spacing: 0.2px;
        }

        .cp-fir-card-left p:last-child {
          font-size: 0.77rem;
          color: #555560;
          margin: 0;
          letter-spacing: 0.1px;
        }

        .cp-btn-fir {
          font-family: 'DM Sans', sans-serif;
          display: flex;
          align-items: center;
          gap: 8px;
          background: linear-gradient(135deg, #B8960C 0%, #D4AF37 50%, #FFD700 100%);
          color: #0B0B0B;
          font-size: 0.75rem;
          font-weight: 700;
          padding: 11px 22px;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.22s ease;
          white-space: nowrap;
          letter-spacing: 0.4px;
          text-transform: uppercase;
          box-shadow: 0 4px 16px rgba(212,175,55,0.3);
          position: relative;
          overflow: hidden;
        }

        .cp-btn-fir::before {
          content: '';
          position: absolute;
          top: 0; left: -100%;
          width: 100%; height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
          transition: left 0.4s ease;
        }

        .cp-btn-fir:hover {
          transform: translateY(-2px) scale(1.02);
          box-shadow: 0 8px 28px rgba(212,175,55,0.45);
          filter: brightness(1.08);
        }

        .cp-btn-fir:hover::before { left: 100%; }

        /* ── LAW PANEL ── */
        .cp-law-panel {
          background: rgba(12, 10, 4, 0.96);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(212,175,55,0.15);
          border-top: 1px solid rgba(212,175,55,0.25);
          border-radius: 20px;
          padding: 28px;
          box-shadow:
            0 1px 0 rgba(212,175,55,0.12) inset,
            0 20px 60px rgba(0,0,0,0.6);
          position: relative;
          overflow: hidden;
        }

        .cp-law-panel::before {
          content: '';
          position: absolute;
          bottom: -40px; right: -40px;
          width: 200px; height: 200px;
          background: radial-gradient(circle, rgba(212,175,55,0.05) 0%, transparent 70%);
          pointer-events: none;
        }

        .cp-law-heading {
          font-family: 'Cormorant Garamond', serif;
          font-size: 1.3rem;
          font-weight: 600;
          color: #C9A84C;
          margin: 0 0 20px;
          padding-bottom: 16px;
          border-bottom: 1px solid rgba(212,175,55,0.12);
          letter-spacing: 0.3px;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .cp-law-heading::after {
          content: '';
          flex: 1;
          height: 1px;
          background: linear-gradient(90deg, rgba(212,175,55,0.2), transparent);
          margin-left: 8px;
        }

        @media (max-width: 640px) {
          .cp-root { padding: 24px 16px 60px; gap: 20px; }
          .cp-chat-container { padding: 18px 16px; }
          .cp-law-panel { padding: 20px 16px; }
          .cp-fir-card { padding: 16px 18px; }
          .cp-heading { font-size: 1.8rem; }
        }
      `}</style>

      <div className="cp-page-shell">
        <div className="cp-root">

          {/* Header */}
          <div className="cp-header">
            <div className="cp-header-left">
              <span className="cp-heading-eyebrow">Indian Law Intelligence</span>
              <h2 className="cp-heading">AI Legal Assistant</h2>
              <p className="cp-subtitle">
                <span>Groq Llama 3.3</span>
                <span className="cp-subtitle-dot" />
                <span>BNS · BNSS · IPC · CrPC</span>
                {turnCount > 1 && (
                  <span className="cp-turn-badge">{turnCount} turns</span>
                )}
              </p>
            </div>
            {hasUserMessages && (
              <button onClick={clearChat} className="cp-btn-newchat">
                + New Chat
              </button>
            )}
          </div>

          {/* Sign-in banner */}
          {!isAuthenticated && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="cp-signin-banner"
            >
              💡 Sign in to save your conversation history across devices
            </motion.div>
          )}

          {/* Chat Window */}
          <div className="cp-chat-container">
            <AIResponseWindow messages={messages} loading={loading} />
            <div className="cp-query-input-wrap">
              <QueryInput onSend={handleSend} disabled={loading} />
            </div>
          </div>

          {/* Draft FIR Action Card */}
          <AnimatePresence>
            {hasUserMessages && !loading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="cp-fir-card"
              >
                <div className="cp-fir-card-left">
                  <p>Ready to take action?</p>
                  <p>Use this conversation to auto-fill your FIR draft</p>
                </div>
                <button onClick={handleDraftFIR} className="cp-btn-fir">
                  <FileText size={13} />
                  Draft FIR
                  <ChevronRight size={13} />
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
                className="cp-law-panel"
              >
                <h3 className="cp-law-heading">📚 Relevant Legal Sections</h3>
                <LawReferenceViewer laws={latestLaws} />
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>
    </PageTransition>
  );
};

export default ChatPage;
