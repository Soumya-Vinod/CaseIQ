import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import AIResponseWindow from '../components/ai/AIResponseWindow';
import QueryInput from '../components/ai/QueryInput';
import StructuredLegalCard from '../components/ai/StructuredLegalCard';
import LegalTimeline from '../components/ai/LegalTimeline';
import RightsCard from '../components/ai/RightsCard';
import CitationVerifier from '../components/ai/CitationVerifier';
import ScenarioSimulator from '../components/ai/ScenarioSimulator';
import RelatedQuestions from '../components/ai/RelatedQuestions';
import PageTransition from '../components/ui/PageTransition';
import { legalAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';
import toast from 'react-hot-toast';
import {
  FileText, ChevronRight, Clock, Shield, AlertTriangle,
  Sparkles, Share2, PanelRightOpen, PanelRightClose,
} from 'lucide-react';

const STORAGE_KEY = 'caseiq_chat_v3';

function getOrCreateSessionId() {
  let sid = sessionStorage.getItem('caseiq_session_id');
  if (!sid) {
    sid = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    sessionStorage.setItem('caseiq_session_id', sid);
  }
  return sid;
}

const SUGGESTED = [
  { label: '🚨 Rights during arrest', q: 'What are my rights when I am arrested by police in India?' },
  { label: '📄 File a complaint', q: 'What is the procedure to file a complaint at a police station?' },
  { label: '💼 Unpaid salary', q: 'My employer has not paid salary for 3 months. What legal action can I take?' },
  { label: '📱 Cybercrime', q: 'I was cheated online and lost money. How do I report cybercrime in India?' },
];

const welcomeMessage = () => ({
  sender: 'ai',
  text: '👋 Welcome to CaseIQ.\n\nI can explain Indian law, help you understand your rights, and guide you through complaints. Ask me anything.',
});

// ── Collapsible Panel Wrapper ──────────────────────────────────────────────
const CollapsiblePanel = ({ title, icon: Icon, collapsed, onToggle, children }) => (
  <div style={{
    background: 'rgba(14,12,6,0.96)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: '20px',
    overflow: 'hidden',
  }}>
    <button
      onClick={onToggle}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 20px',
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        borderBottom: collapsed ? 'none' : '1px solid rgba(212,175,55,0.1)',
        transition: 'background 0.2s ease',
        fontFamily: 'inherit',
      }}
      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(212,175,55,0.04)'}
      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Icon size={14} style={{ color: '#D4AF37' }} />
        <span style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: '1rem',
          fontWeight: 700,
          fontStyle: 'italic',
          color: '#D4AF37',
        }}>
          {title}
        </span>
      </div>
      <motion.div
        animate={{ rotate: collapsed ? 0 : 180 }}
        transition={{ duration: 0.2 }}
        style={{ color: '#9A7D3A', display: 'flex' }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="18 15 12 9 6 15" />
        </svg>
      </motion.div>
    </button>

    <AnimatePresence initial={false}>
      {!collapsed && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          style={{ overflow: 'hidden' }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  </div>
);

// ── Tool Button ────────────────────────────────────────────────────────────
const ToolButton = ({ icon: Icon, label, active, loading, onClick }) => (
  <button
    onClick={onClick}
    disabled={loading}
    style={{
      display: 'flex', alignItems: 'center', gap: '8px',
      padding: '10px 18px', borderRadius: '10px',
      border: active ? '1px solid rgba(212,175,55,0.4)' : '1px solid rgba(212,175,55,0.15)',
      background: active ? 'rgba(212,175,55,0.12)' : 'rgba(14,12,6,0.8)',
      color: active ? '#D4AF37' : '#8A8A92',
      fontSize: '0.78rem', fontWeight: 500,
      cursor: loading ? 'not-allowed' : 'pointer',
      fontFamily: 'inherit', transition: 'all 0.2s ease',
      opacity: loading ? 0.6 : 1,
    }}
    onMouseEnter={(e) => {
      if (!active && !loading) {
        e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
        e.currentTarget.style.color = '#C9A84C';
      }
    }}
    onMouseLeave={(e) => {
      if (!active && !loading) {
        e.currentTarget.style.borderColor = 'rgba(212,175,55,0.15)';
        e.currentTarget.style.color = '#8A8A92';
      }
    }}
  >
    <Icon size={13} />
    {loading ? 'Loading...' : label}
  </button>
);

// ── Main Page ──────────────────────────────────────────────────────────────
const ChatPage = () => {
  const { isAuthenticated } = useAuth();
  const { language } = useSettings();
  const navigate = useNavigate();

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(getOrCreateSessionId);

  const [latestStructured, setLatestStructured] = useState(null);
  const [latestQuery, setLatestQuery] = useState('');
  const [relatedQuestions, setRelatedQuestions] = useState([]);

  // Side panel
  const [panelOpen, setPanelOpen] = useState(false);

  // Tool state — data persists, only cleared on New Chat
  const [activeTool, setActiveTool] = useState(null);
  const [toolLoading, setToolLoading] = useState(false);
  const [timelineData, setTimelineData] = useState(null);
  const [rightsData, setRightsData] = useState(null);
  const [simulatorQuery, setSimulatorQuery] = useState('');

  // Collapse state per tool
  const [toolsCollapsed, setToolsCollapsed] = useState({
    timeline: false,
    rights: false,
    simulator: false,
  });

  const [verifyingCitation, setVerifyingCitation] = useState(null);
  const [blockedWarning, setBlockedWarning] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);

  const langMap = { English: 'en', Hindi: 'hi', Marathi: 'mr', Tamil: 'ta' };

  // Load saved messages
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          if (parsed.some((m) => m.sender === 'user')) setShowSuggestions(false);
          return;
        }
      } catch {}
    }
    setMessages([welcomeMessage()]);
  }, []);

  // Save messages
  useEffect(() => {
    if (messages.length > 0) localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const handleSend = useCallback(async (text) => {
    if (!text || !text.trim()) return;

    setShowSuggestions(false);
    setBlockedWarning('');
    setLatestQuery(text);
    setLatestStructured(null);
    setRelatedQuestions([]);
    // NOTE: timelineData, rightsData, activeTool NOT cleared — they persist and stay collapsible

    setMessages((prev) => [...prev, { sender: 'user', text: text.trim() }]);
    setLoading(true);

    try {
      const res = await legalAPI.submitQuery(text, langMap[language] || 'en', sessionId);
      const data = res.data || {};

      let summary = data.conversational_summary;
      if (typeof summary !== 'string') {
        summary = summary ? JSON.stringify(summary) : 'Please try again.';
      }
      if (!summary.trim()) summary = 'I received your question. Please try rephrasing.';

      setMessages((prev) => [...prev, {
        sender: 'ai',
        text: summary,
        confidence: data.confidence_score,
        isFollowup: data.is_followup,
      }]);

      if (data.structured_data && Object.keys(data.structured_data).length > 0) {
        setLatestStructured(data.structured_data);
        if (!data.is_followup) setPanelOpen(true);
      }

      if (Array.isArray(data.related_questions) && data.related_questions.length > 0) {
        setRelatedQuestions(data.related_questions);
      }

    } catch (err) {
      if (err.response?.status === 403 && err.response?.data?.blocked) {
        setBlockedWarning(err.response.data.message);
        setMessages((prev) => [...prev, {
          sender: 'ai',
          text: '🚫 This query has been blocked. CaseIQ helps citizens understand their legal rights — not facilitate harmful activity.',
          isBlocked: true,
        }]);
      } else {
        const errorMsg = err.response?.data?.error || 'Failed to process query. Please try again.';
        toast.error(errorMsg);
        setMessages((prev) => [...prev, { sender: 'ai', text: `❌ ${errorMsg}` }]);
      }
    } finally {
      setLoading(false);
    }
  }, [language, sessionId]);

  // Handle pending query from other pages
  useEffect(() => {
    const pending = localStorage.getItem('caseiq_pending_query');
    if (pending) { handleSend(pending); localStorage.removeItem('caseiq_pending_query'); }
  }, [handleSend]);

  const clearChat = () => {
    const newSid = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    sessionStorage.setItem('caseiq_session_id', newSid);
    localStorage.removeItem(STORAGE_KEY);
    setMessages([welcomeMessage()]);
    setLatestStructured(null);
    setLatestQuery('');
    setRelatedQuestions([]);
    setTimelineData(null);
    setRightsData(null);
    setActiveTool(null);
    setSimulatorQuery('');
    setBlockedWarning('');
    setShowSuggestions(true);
    setPanelOpen(false);
    setToolsCollapsed({ timeline: false, rights: false, simulator: false });
  };

  const openTimeline = async () => {
    if (!latestQuery) return toast.error('Ask a question first');
    setActiveTool('timeline');
    // Un-collapse if already loaded
    setToolsCollapsed((p) => ({ ...p, timeline: false }));
    if (timelineData) return; // already have data, just un-collapse
    setToolLoading(true);
    try {
      const res = await legalAPI.generateTimeline(latestQuery);
      setTimelineData(res.data.timeline);
    } catch {
      toast.error('Failed to build timeline');
      setActiveTool(null);
    } finally {
      setToolLoading(false);
    }
  };

  const openRights = async () => {
    if (!latestQuery) return toast.error('Ask a question first');
    setActiveTool('rights');
    setToolsCollapsed((p) => ({ ...p, rights: false }));
    if (rightsData) return;
    setToolLoading(true);
    try {
      const res = await legalAPI.generateRightsCard(latestQuery);
      setRightsData(res.data.rights_card);
    } catch {
      toast.error('Failed to build rights card');
      setActiveTool(null);
    } finally {
      setToolLoading(false);
    }
  };

  const openSimulator = () => {
    if (!latestQuery) return toast.error('Ask a question first');
    setSimulatorQuery(latestQuery);
    setActiveTool('simulator');
    setToolsCollapsed((p) => ({ ...p, simulator: false }));
  };

  const handleShare = async () => {
    const text = messages
      .map((m) => `${m.sender === 'user' ? 'You' : 'CaseIQ'}: ${m.text}`)
      .join('\n\n');
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Conversation copied');
    } catch {
      toast.error('Could not copy');
    }
  };

  const hasUserMessages = messages.some((m) => m.sender === 'user');
  const turnCount = messages.filter((m) => m.sender === 'user').length;
  const hasStructured = latestStructured && Object.keys(latestStructured).length > 0;

  return (
    <PageTransition>
      <div style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '32px 24px 80px',
        position: 'relative',
        zIndex: 1,
      }}>

        {/* ── Header ── */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '24px',
          flexWrap: 'wrap',
          gap: '16px',
        }}>
          <div>
            <p className="eyebrow" style={{ marginBottom: '8px' }}>Indian Law Intelligence</p>
            <h1 className="serif-heading" style={{ fontSize: 'clamp(1.8rem, 3.5vw, 2.4rem)', marginBottom: '6px' }}>
              AI Legal Assistant
            </h1>
            <p style={{
              fontSize: '0.78rem', color: '#555560',
              display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap',
            }}>
              <span>Groq Llama 3.3</span>
              <span style={{ width: '3px', height: '3px', borderRadius: '50%', background: '#3A3A40' }} />
              <span>BNS · BNSS · IPC · CrPC</span>
              {turnCount > 1 && (
                <span style={{
                  background: 'rgba(212,175,55,0.1)',
                  border: '1px solid rgba(212,175,55,0.25)',
                  color: '#C9A84C', fontSize: '0.66rem', fontWeight: 600,
                  padding: '2px 10px', borderRadius: '20px',
                }}>
                  {turnCount} turns
                </span>
              )}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {hasStructured && (
              <button
                onClick={() => setPanelOpen(!panelOpen)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  padding: '8px 16px', borderRadius: '10px',
                  border: panelOpen ? '1px solid rgba(212,175,55,0.4)' : '1px solid rgba(212,175,55,0.2)',
                  background: panelOpen ? 'rgba(212,175,55,0.12)' : 'rgba(212,175,55,0.05)',
                  color: panelOpen ? '#FFD700' : '#D4AF37',
                  fontSize: '0.74rem', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'all 0.2s ease',
                }}
              >
                {panelOpen ? <PanelRightClose size={13} /> : <PanelRightOpen size={13} />}
                {panelOpen ? 'Hide Breakdown' : 'Show Breakdown'}
              </button>
            )}
            {hasUserMessages && (
              <>
                <button onClick={handleShare} className="btn-ghost" style={{ padding: '8px 14px', fontSize: '0.74rem' }}>
                  <Share2 size={12} /> Share
                </button>
                <button onClick={clearChat} className="btn-ghost" style={{ padding: '8px 14px', fontSize: '0.74rem' }}>
                  + New Chat
                </button>
              </>
            )}
          </div>
        </div>

        {/* ── Sign-in Banner ── */}
        {!isAuthenticated && (
          <div style={{
            background: 'rgba(212,175,55,0.04)',
            border: '1px solid rgba(212,175,55,0.15)',
            borderLeft: '3px solid rgba(212,175,55,0.5)',
            color: '#9A7D3A', borderRadius: '12px',
            padding: '12px 18px', fontSize: '0.8rem', marginBottom: '20px',
          }}>
            💡 Sign in to save your conversation history across devices
          </div>
        )}

        {/* ── Blocked Warning ── */}
        <AnimatePresence>
          {blockedWarning && (
            <motion.div
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              style={{
                background: 'rgba(244,67,54,0.08)',
                border: '1px solid rgba(244,67,54,0.2)',
                borderRadius: '12px', padding: '14px 18px',
                display: 'flex', gap: '12px', alignItems: 'flex-start', marginBottom: '20px',
              }}
            >
              <AlertTriangle size={16} style={{ color: '#F44336', flexShrink: 0, marginTop: '1px' }} />
              <div>
                <p style={{ color: '#F44336', fontSize: '0.82rem', fontWeight: 600, marginBottom: '3px' }}>Query Blocked</p>
                <p style={{ color: '#C8A0A0', fontSize: '0.78rem', lineHeight: 1.5 }}>{blockedWarning}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Suggested Queries ── */}
        <AnimatePresence>
          {showSuggestions && !hasUserMessages && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              style={{ marginBottom: '20px' }}
            >
              <p style={{ fontSize: '0.7rem', color: '#555560', marginBottom: '10px' }}>
                Try these to get started:
              </p>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '10px',
              }}>
                {SUGGESTED.map((sq, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(sq.q)}
                    disabled={loading}
                    style={{
                      textAlign: 'left', fontSize: '0.78rem',
                      padding: '12px 14px', borderRadius: '12px',
                      border: '1px solid rgba(212,175,55,0.12)',
                      background: 'rgba(14,12,6,0.7)', color: '#8A8A92',
                      cursor: 'pointer', transition: 'all 0.2s ease',
                      fontFamily: 'inherit', lineHeight: 1.4,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
                      e.currentTarget.style.color = '#C9A84C';
                      e.currentTarget.style.background = 'rgba(212,175,55,0.06)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(212,175,55,0.12)';
                      e.currentTarget.style.color = '#8A8A92';
                      e.currentTarget.style.background = 'rgba(14,12,6,0.7)';
                    }}
                  >
                    {sq.label}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Split Layout: Chat + Structured Card ── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: panelOpen && hasStructured ? '1fr 1fr' : '1fr',
          gap: '20px',
          marginBottom: '20px',
          alignItems: 'start',
        }}>
          {/* Chat */}
          <div className="gold-card" style={{ padding: '24px', minWidth: 0 }}>
            <AIResponseWindow messages={messages} loading={loading} />
            <div style={{
              marginTop: '20px', paddingTop: '20px',
              borderTop: '1px solid rgba(212,175,55,0.1)',
              position: 'relative',
            }}>
              <div style={{
                position: 'absolute', top: '-1px', left: '50%',
                transform: 'translateX(-50%)',
                width: '60px', height: '1px',
                background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.6), transparent)',
              }} />
              <QueryInput onSend={handleSend} disabled={loading} />
            </div>
          </div>

          {/* Structured Card */}
          <AnimatePresence mode="wait">
            {panelOpen && hasStructured && (
              <motion.div
                key="panel"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 30 }}
                transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                style={{ minWidth: 0 }}
              >
                <StructuredLegalCard
                  data={latestStructured}
                  onVerifyCitation={(act, section) => setVerifyingCitation({ act, section })}
                  onClose={() => setPanelOpen(false)}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Tool Buttons ── */}
        {hasUserMessages && !loading && latestQuery && (
          <motion.div
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}
          >
            <ToolButton
              icon={Clock}
              label="Legal Timeline"
              active={activeTool === 'timeline'}
              loading={toolLoading && activeTool === 'timeline'}
              onClick={openTimeline}
            />
            <ToolButton
              icon={Shield}
              label="My Rights Card"
              active={activeTool === 'rights'}
              loading={toolLoading && activeTool === 'rights'}
              onClick={openRights}
            />
            <ToolButton
              icon={Sparkles}
              label="What-If Simulator"
              active={activeTool === 'simulator'}
              loading={false}
              onClick={openSimulator}
            />
          </motion.div>
        )}

        {/* ── Tool Panels — collapsible, persist across queries ── */}
        {timelineData && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ marginBottom: '16px' }}
          >
            <CollapsiblePanel
              title="Legal Timeline"
              icon={Clock}
              collapsed={toolsCollapsed.timeline}
              onToggle={() => setToolsCollapsed((p) => ({ ...p, timeline: !p.timeline }))}
            >
              <div style={{ padding: '4px' }}>
                <LegalTimeline data={timelineData} loading={false} />
              </div>
            </CollapsiblePanel>
          </motion.div>
        )}

        {rightsData && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ marginBottom: '16px' }}
          >
            <CollapsiblePanel
              title="My Rights Card"
              icon={Shield}
              collapsed={toolsCollapsed.rights}
              onToggle={() => setToolsCollapsed((p) => ({ ...p, rights: !p.rights }))}
            >
              <div style={{ padding: '4px' }}>
                <RightsCard data={rightsData} loading={false} />
              </div>
            </CollapsiblePanel>
          </motion.div>
        )}

        {activeTool === 'simulator' && simulatorQuery && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ marginBottom: '16px' }}
          >
            <CollapsiblePanel
              title="What-If Simulator"
              icon={Sparkles}
              collapsed={toolsCollapsed.simulator}
              onToggle={() => setToolsCollapsed((p) => ({ ...p, simulator: !p.simulator }))}
            >
              <div style={{ padding: '4px' }}>
                <ScenarioSimulator situation={simulatorQuery} />
              </div>
            </CollapsiblePanel>
          </motion.div>
        )}

        {/* ── Related Questions ── */}
        <AnimatePresence>
          {relatedQuestions.length > 0 && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              style={{ marginBottom: '20px' }}
            >
              <RelatedQuestions
                questions={relatedQuestions}
                onSelect={handleSend}
                disabled={loading}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Draft Complaint CTA ── */}
        {hasUserMessages && !loading && (
          <div style={{
            background: 'rgba(14,12,6,0.96)',
            border: '1px solid rgba(212,175,55,0.2)',
            borderRadius: '16px',
            padding: '20px 26px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '20px',
            flexWrap: 'wrap',
            position: 'relative',
            overflow: 'hidden',
          }}>
            <div style={{
              position: 'absolute', left: 0, top: 0, bottom: 0,
              width: '3px',
              background: 'linear-gradient(180deg, transparent, #D4AF37, transparent)',
            }} />
            <div>
              <p style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: '1.05rem', fontWeight: 600, color: '#E5E5E5', marginBottom: '4px',
              }}>
                Ready to take action?
              </p>
              <p style={{ fontSize: '0.76rem', color: '#555560' }}>
                Use this conversation to auto-fill your complaint draft
              </p>
            </div>
            <button
              onClick={() => {
                const q = messages.filter((m) => m.sender === 'user').map((m) => m.text).join(' ');
                localStorage.setItem('caseiq_prefill_complaint', JSON.stringify({
                  description: q.slice(0, 500),
                  from_chat: true,
                  session_id: sessionId,
                }));
                navigate('/fir-draft');
              }}
              className="btn-gold"
            >
              <FileText size={13} />
              Draft Complaint
              <ChevronRight size={13} />
            </button>
          </div>
        )}
      </div>

      {/* ── Citation Verifier Modal ── */}
      <AnimatePresence>
        {verifyingCitation && (
          <CitationVerifier
            citation={verifyingCitation}
            onClose={() => setVerifyingCitation(null)}
          />
        )}
      </AnimatePresence>
    </PageTransition>
  );
};

export default ChatPage;
