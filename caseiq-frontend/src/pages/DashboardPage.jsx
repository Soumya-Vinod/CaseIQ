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

  const displayName = user?.full_name || user?.email?.split('@')[0] || 'Counselor';

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,500;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

        /* ── SHARED TOKEN LAYER ── */
        :root {
          --gold-bright:   #FFD700;
          --gold-main:     #D4AF37;
          --gold-mid:      #C9A84C;
          --gold-muted:    #9A7D3A;
          --gold-deep:     #7A5E1A;
          --black-0:       #0B0B0B;
          --black-1:       #111111;
          --black-2:       #171717;
          --black-3:       #1E1E1E;
          --black-4:       #252525;
          --surface:       rgba(20,20,20,0.92);
          --surface-light: rgba(30,30,30,0.85);
          --border-gold:   rgba(212,175,55,0.18);
          --border-gold-h: rgba(212,175,55,0.4);
          --text-primary:  #E8E8E8;
          --text-muted:    #6B6B75;
          --text-faint:    #3A3A42;
          --serif:         'Cormorant Garamond', Georgia, serif;
          --sans:          'DM Sans', system-ui, sans-serif;
          --ease-gold:     cubic-bezier(0.4, 0, 0.2, 1);
        }

        html, body, #root {
          background: var(--black-0) !important;
        }

        /* ── PAGE SHELL ── */
        .db-shell {
          min-height: 100vh;
          background: var(--black-0);
          background-image:
            radial-gradient(ellipse 90% 55% at 50% -5%, rgba(212,175,55,0.13) 0%, transparent 62%),
            radial-gradient(ellipse 50% 35% at 90% 85%, rgba(212,175,55,0.06) 0%, transparent 55%),
            radial-gradient(ellipse 40% 28% at 5% 60%, rgba(212,175,55,0.04) 0%, transparent 50%);
          position: relative;
          font-family: var(--sans);
        }

        .db-shell::before {
          content: '';
          position: fixed;
          inset: 0;
          background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
          pointer-events: none;
          z-index: 0;
        }

        .db-root {
          max-width: 1080px;
          margin: 0 auto;
          padding: 48px 28px 80px;
          display: flex;
          flex-direction: column;
          gap: 36px;
          position: relative;
          z-index: 1;
        }

        /* ── HEADER ── */
        .db-header {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 16px;
        }

        .db-eyebrow {
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

        .db-eyebrow::before {
          content: '';
          display: block;
          width: 32px;
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--gold-muted));
        }

        .db-title {
          font-family: var(--serif);
          font-size: clamp(2.2rem, 5vw, 3.2rem);
          font-weight: 700;
          font-style: italic;
          background: linear-gradient(135deg, var(--gold-main) 0%, var(--gold-bright) 50%, var(--gold-mid) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          filter: drop-shadow(0 0 30px rgba(212,175,55,0.25));
          line-height: 1.05;
          margin: 0;
          letter-spacing: -0.5px;
        }

        .db-welcome {
          font-size: 0.85rem;
          color: var(--text-muted);
          font-weight: 400;
          letter-spacing: 0.2px;
          padding-bottom: 4px;
        }

        .db-welcome strong {
          color: var(--gold-mid);
          font-weight: 500;
        }

        /* ── DIVIDER ── */
        .db-divider {
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--border-gold), rgba(212,175,55,0.35), var(--border-gold), transparent);
        }

        /* ── STAT CARDS ── */
        .db-stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 20px;
        }

        @media (max-width: 600px) { .db-stats-grid { grid-template-columns: 1fr; } }

        .db-stat-card {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-top: 1px solid rgba(212,175,55,0.35);
          border-radius: 20px;
          padding: 32px 28px;
          position: relative;
          overflow: hidden;
          transition: transform 0.28s var(--ease-gold), box-shadow 0.28s var(--ease-gold), border-color 0.28s ease;
          cursor: default;
        }

        .db-stat-card:hover {
          transform: translateY(-4px);
          border-color: var(--border-gold-h);
          box-shadow: 0 16px 48px rgba(0,0,0,0.6), 0 0 32px rgba(212,175,55,0.12);
        }

        /* Glow blob */
        .db-stat-card::before {
          content: '';
          position: absolute;
          top: -40px; right: -40px;
          width: 160px; height: 160px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(212,175,55,0.1) 0%, transparent 70%);
          pointer-events: none;
          transition: opacity 0.3s ease;
        }

        /* Top inset shimmer line */
        .db-stat-card::after {
          content: '';
          position: absolute;
          top: 0; left: 10%; right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.5), transparent);
        }

        .db-stat-icon {
          font-size: 1.5rem;
          margin-bottom: 16px;
          display: block;
          filter: drop-shadow(0 2px 8px rgba(212,175,55,0.3));
        }

        .db-stat-label {
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 3px;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 12px;
        }

        .db-stat-value {
          font-family: var(--serif);
          font-size: clamp(3rem, 6vw, 4.5rem);
          font-weight: 700;
          background: linear-gradient(135deg, var(--gold-main), var(--gold-bright));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          line-height: 1;
          filter: drop-shadow(0 0 20px rgba(212,175,55,0.2));
        }

        .db-stat-desc {
          font-size: 0.77rem;
          color: var(--text-muted);
          margin-top: 8px;
          letter-spacing: 0.2px;
        }

        /* Loading shimmer */
        .db-stat-shimmer {
          display: inline-block;
          width: 80px;
          height: 56px;
          background: linear-gradient(90deg, var(--black-3), var(--black-4), var(--black-3));
          background-size: 200% 100%;
          animation: shimmer 1.6s ease-in-out infinite;
          border-radius: 8px;
        }

        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }

        /* ── PANELS GRID ── */
        .db-panels-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 20px;
        }

        @media (max-width: 700px) { .db-panels-grid { grid-template-columns: 1fr; } }

        .db-panel {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-top: 1px solid rgba(212,175,55,0.3);
          border-radius: 20px;
          padding: 24px;
          position: relative;
          overflow: hidden;
          transition: border-color 0.25s ease, box-shadow 0.25s ease;
        }

        .db-panel:hover {
          border-color: var(--border-gold-h);
          box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(212,175,55,0.08);
        }

        .db-panel::after {
          content: '';
          position: absolute;
          top: 0; left: 10%; right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent);
        }

        .db-panel-title {
          font-family: var(--serif);
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--gold-mid);
          margin: 0 0 20px;
          padding-bottom: 14px;
          border-bottom: 1px solid rgba(212,175,55,0.1);
          display: flex;
          align-items: center;
          gap: 8px;
          letter-spacing: 0.2px;
        }

        /* ── ACTIVITY ROW (guest notice) ── */
        .db-guest-notice {
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
          letter-spacing: 0.1px;
        }

        @media (max-width: 640px) {
          .db-root { padding: 28px 16px 60px; gap: 24px; }
          .db-stat-card { padding: 24px 20px; }
        }
      `}</style>

      <div className="db-shell">
        <div className="db-root">

          {/* Header */}
          <div className="db-header">
            <div>
              <p className="db-eyebrow">Command Centre</p>
              <h2 className="db-title">Dashboard</h2>
            </div>
            <p className="db-welcome">
              {isAuthenticated
                ? <>Welcome back, <strong>{displayName}</strong></>
                : 'Track your legal queries and FIR activity.'}
            </p>
          </div>

          <div className="db-divider" />

          {/* Guest notice */}
          {!isAuthenticated && (
            <div className="db-guest-notice">
              💡 Sign in to sync your history across all devices and unlock full analytics.
            </div>
          )}

          {/* Stats */}
          <div className="db-stats-grid">
            <div className="db-stat-card">
              <span className="db-stat-icon">⚖️</span>
              <p className="db-stat-label">Total Queries</p>
              {loading
                ? <span className="db-stat-shimmer" />
                : <p className="db-stat-value">{chatCount}</p>
              }
              <p className="db-stat-desc">Legal questions asked</p>
            </div>

            <div className="db-stat-card">
              <span className="db-stat-icon">📋</span>
              <p className="db-stat-label">FIR Drafts</p>
              {loading
                ? <span className="db-stat-shimmer" />
                : <p className="db-stat-value">{firCount}</p>
              }
              <p className="db-stat-desc">FIR documents generated</p>
            </div>
          </div>

          {/* Panels */}
          <div className="db-panels-grid">
            <div className="db-panel">
              <h3 className="db-panel-title">🕐 Recent Searches</h3>
              <RecentSearches />
            </div>
            <div className="db-panel">
              <h3 className="db-panel-title">📜 Query History</h3>
              <HistoryPanel />
            </div>
          </div>

        </div>
      </div>
    </>
  );
};

export default DashboardPage;
