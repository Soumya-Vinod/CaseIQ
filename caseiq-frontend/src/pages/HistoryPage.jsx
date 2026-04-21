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

  const formatDate = (iso) =>
    new Date(iso).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });

  const statusMeta = (status) => {
    if (status === 'processed') return { label: 'Processed', cls: 'hist-badge--green' };
    if (status === 'local')     return { label: 'Guest',     cls: 'hist-badge--blue' };
    return                             { label: status,      cls: 'hist-badge--gray' };
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,500&family=DM+Sans:wght@300;400;500;600&display=swap');

        :root {
          --gold-bright:   #FFD700;
          --gold-main:     #D4AF37;
          --gold-mid:      #C9A84C;
          --gold-muted:    #9A7D3A;
          --black-0:       #0B0B0B;
          --surface:       rgba(18,18,18,0.95);
          --border-gold:   rgba(212,175,55,0.17);
          --border-gold-h: rgba(212,175,55,0.42);
          --text-primary:  #E8E8E8;
          --text-muted:    #6B6B75;
          --serif:         'Cormorant Garamond', Georgia, serif;
          --sans:          'DM Sans', system-ui, sans-serif;
          --ease-gold:     cubic-bezier(0.4, 0, 0.2, 1);
        }

        html, body, #root { background: var(--black-0) !important; }

        .hist-shell {
          min-height: 100vh;
          background: var(--black-0);
          background-image:
            radial-gradient(ellipse 80% 45% at 50% -8%, rgba(212,175,55,0.11) 0%, transparent 60%),
            radial-gradient(ellipse 40% 28% at 8% 85%, rgba(212,175,55,0.04) 0%, transparent 55%);
          font-family: var(--sans);
          position: relative;
        }

        .hist-shell::before {
          content: '';
          position: fixed;
          inset: 0;
          background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
          pointer-events: none;
          z-index: 0;
        }

        .hist-root {
          max-width: 860px;
          margin: 0 auto;
          padding: 52px 28px 88px;
          display: flex;
          flex-direction: column;
          gap: 32px;
          position: relative;
          z-index: 1;
        }

        /* ── HEADER ── */
        .hist-header {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 16px;
        }

        .hist-eyebrow {
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 3.5px;
          text-transform: uppercase;
          color: var(--gold-muted);
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 10px;
        }

        .hist-eyebrow::before {
          content: '';
          display: block;
          width: 32px;
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--gold-muted));
        }

        .hist-title {
          font-family: var(--serif);
          font-size: clamp(2rem, 4.5vw, 3rem);
          font-weight: 700;
          font-style: italic;
          background: linear-gradient(135deg, var(--gold-main) 0%, var(--gold-bright) 50%, var(--gold-mid) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          filter: drop-shadow(0 0 28px rgba(212,175,55,0.25));
          line-height: 1.05;
          margin: 0;
        }

        /* ── DIVIDER ── */
        .hist-divider {
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--border-gold), rgba(212,175,55,0.35), var(--border-gold), transparent);
        }

        /* ── CLEAR BUTTON ── */
        .hist-btn-clear {
          font-family: var(--sans);
          font-size: 0.75rem;
          font-weight: 600;
          letter-spacing: 0.5px;
          text-transform: uppercase;
          color: #E07060;
          background: rgba(200,60,40,0.07);
          border: 1px solid rgba(200,60,40,0.2);
          padding: 9px 18px;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.22s var(--ease-gold);
          display: inline-flex;
          align-items: center;
          gap: 7px;
        }

        .hist-btn-clear:hover {
          background: rgba(200,60,40,0.13);
          border-color: rgba(200,60,40,0.4);
          box-shadow: 0 4px 16px rgba(200,60,40,0.15);
        }

        /* ── GUEST NOTICE ── */
        .hist-guest-notice {
          background: rgba(212,175,55,0.04);
          border: 1px solid rgba(212,175,55,0.15);
          border-left: 3px solid rgba(212,175,55,0.5);
          border-radius: 12px;
          padding: 14px 18px;
          font-size: 0.82rem;
          color: var(--gold-muted);
          display: flex;
          align-items: center;
          gap: 10px;
        }

        /* ── LOADING ── */
        .hist-loading {
          display: flex;
          justify-content: center;
          padding: 60px 20px;
        }

        .hist-spinner {
          width: 40px; height: 40px;
          border-radius: 50%;
          border: 2px solid rgba(212,175,55,0.12);
          border-top-color: var(--gold-main);
          animation: hist-spin 0.9s linear infinite;
        }

        @keyframes hist-spin { to { transform: rotate(360deg); } }

        /* ── EMPTY STATE ── */
        .hist-empty {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-radius: 20px;
          padding: 64px 40px;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
        }

        .hist-empty-icon {
          font-size: 2.5rem;
          filter: grayscale(0.5);
          opacity: 0.5;
        }

        .hist-empty-title {
          font-family: var(--serif);
          font-size: 1.3rem;
          font-weight: 600;
          color: #3A3A44;
        }

        .hist-empty-sub {
          font-size: 0.82rem;
          color: var(--text-muted);
          max-width: 280px;
          line-height: 1.6;
        }

        /* ── TIMELINE ── */
        .hist-timeline {
          display: flex;
          flex-direction: column;
          gap: 0;
          position: relative;
        }

        /* Vertical gold line */
        .hist-timeline::before {
          content: '';
          position: absolute;
          left: 20px;
          top: 28px;
          bottom: 28px;
          width: 1px;
          background: linear-gradient(180deg, transparent, rgba(212,175,55,0.3) 15%, rgba(212,175,55,0.3) 85%, transparent);
        }

        .hist-item {
          display: flex;
          gap: 20px;
          padding: 14px 0;
          align-items: flex-start;
          position: relative;
        }

        /* Timeline dot */
        .hist-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--black-0);
          border: 2px solid rgba(212,175,55,0.4);
          margin-top: 18px;
          flex-shrink: 0;
          margin-left: 16px;
          transition: border-color 0.22s ease, box-shadow 0.22s ease;
          z-index: 1;
        }

        .hist-item:hover .hist-dot {
          border-color: var(--gold-mid);
          box-shadow: 0 0 10px rgba(212,175,55,0.4);
          background: rgba(212,175,55,0.1);
        }

        .hist-card {
          flex: 1;
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-radius: 16px;
          padding: 18px 20px;
          transition: all 0.25s var(--ease-gold);
          position: relative;
          overflow: hidden;
        }

        .hist-card::before {
          content: '';
          position: absolute;
          top: 0; left: 10%; right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.3), transparent);
          opacity: 0;
          transition: opacity 0.25s ease;
        }

        .hist-item:hover .hist-card {
          border-color: var(--border-gold-h);
          box-shadow: 0 8px 28px rgba(0,0,0,0.5), 0 0 18px rgba(212,175,55,0.08);
          transform: translateX(3px);
        }

        .hist-item:hover .hist-card::before { opacity: 1; }

        .hist-query {
          font-size: 0.88rem;
          color: var(--text-primary);
          font-weight: 500;
          line-height: 1.55;
          margin-bottom: 12px;
        }

        .hist-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 8px;
        }

        .hist-date {
          font-size: 0.72rem;
          color: var(--text-muted);
          letter-spacing: 0.3px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .hist-date::before {
          content: '';
          display: inline-block;
          width: 4px; height: 4px;
          border-radius: 50%;
          background: rgba(212,175,55,0.3);
        }

        /* Status badges */
        .hist-badge {
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 1px;
          text-transform: uppercase;
          padding: 3px 10px;
          border-radius: 20px;
          border: 1px solid;
        }

        .hist-badge--green {
          background: rgba(40,160,80,0.1);
          border-color: rgba(40,160,80,0.3);
          color: #50C878;
        }

        .hist-badge--blue {
          background: rgba(60,120,220,0.1);
          border-color: rgba(60,120,220,0.3);
          color: #7090E8;
        }

        .hist-badge--gray {
          background: rgba(100,100,110,0.1);
          border-color: rgba(100,100,110,0.3);
          color: #888890;
        }

        /* ── COUNT CHIP ── */
        .hist-count-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(212,175,55,0.07);
          border: 1px solid rgba(212,175,55,0.2);
          color: var(--gold-muted);
          font-size: 0.72rem;
          font-weight: 600;
          letter-spacing: 0.5px;
          padding: 4px 12px;
          border-radius: 20px;
          margin-top: 4px;
          display: block;
          width: fit-content;
        }

        @media (max-width: 640px) {
          .hist-root { padding: 28px 16px 60px; gap: 24px; }
          .hist-timeline::before { left: 14px; }
          .hist-dot { margin-left: 10px; }
        }
      `}</style>

      <div className="hist-shell">
        <div className="hist-root">

          {/* Header */}
          <div className="hist-header">
            <div>
              <p className="hist-eyebrow">Your Activity</p>
              <h2 className="hist-title">Query History</h2>
              {chatHistory.length > 0 && (
                <span className="hist-count-chip">{chatHistory.length} record{chatHistory.length !== 1 ? 's' : ''}</span>
              )}
            </div>
            {!isAuthenticated && chatHistory.length > 0 && (
              <button onClick={clearLocalHistory} className="hist-btn-clear">
                🗑 Clear History
              </button>
            )}
          </div>

          <div className="hist-divider" />

          {/* Guest notice */}
          {!isAuthenticated && (
            <div className="hist-guest-notice">
              💡 Sign in to access your full query history across all devices.
            </div>
          )}

          {/* Loading */}
          {loading ? (
            <div className="hist-loading">
              <div className="hist-spinner" />
            </div>
          ) : chatHistory.length === 0 ? (
            <div className="hist-empty">
              <span className="hist-empty-icon">⚖️</span>
              <p className="hist-empty-title">No queries yet</p>
              <p className="hist-empty-sub">Ask your first legal question in the AI Assistant to see your history here.</p>
            </div>
          ) : (
            <div className="hist-timeline">
              {chatHistory.map((item, index) => {
                const { label, cls } = statusMeta(item.status);
                return (
                  <div key={item.id ?? index} className="hist-item">
                    <div className="hist-dot" />
                    <div className="hist-card">
                      <p className="hist-query">{item.original_query}</p>
                      <div className="hist-meta">
                        <span className="hist-date">{formatDate(item.created_at)}</span>
                        <span className={`hist-badge ${cls}`}>{label}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

        </div>
      </div>
    </>
  );
};

export default HistoryPage;
