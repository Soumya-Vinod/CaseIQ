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
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

        :root {
          --black-deep: #0B0B0B;
          --black-mid: #111111;
          --black-card: #161616;
          --black-elevated: #1C1C1C;
          --gold-primary: #B8960C;
          --gold-bright: #C9A84C;
          --gold-soft: #A67C2E;
          --gold-muted: #8B7535;
          --text-heading: #F5E9C8;
          --text-body: #E5E5E5;
          --text-muted: #A1A1AA;
          --border-gold: rgba(212, 175, 55, 0.25);
          --glow-gold: rgba(212, 175, 55, 0.15);
          --glow-gold-strong: rgba(212, 175, 55, 0.3);
        }

        .hp-root {
          font-family: 'DM Sans', sans-serif;
          background: var(--black-deep);
          min-height: 100vh;
        }

        /* ── HERO ── */
        .hp-hero {
          text-align: center;
          padding: 72px 24px 48px;
          position: relative;
        }
        .hp-hero-glow {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -60%);
          width: 600px;
          height: 300px;
          background: radial-gradient(ellipse at center, rgba(212,175,55,0.18) 0%, transparent 70%);
          pointer-events: none;
          filter: blur(20px);
        }
        .hp-hero h1 {
          font-family: 'Cormorant Garamond', serif;
          font-size: clamp(2.6rem, 6vw, 4.2rem);
          font-weight: 700;
          color: #B8960C;
          text-shadow:
            0 0 40px rgba(184, 150, 12, 0.45),
            0 2px 8px rgba(0,0,0,0.6);
          letter-spacing: -0.5px;
          line-height: 1.15;
          margin-bottom: 20px;
          position: relative;
        }
        .hp-hero p {
          font-size: 1.05rem;
          color: var(--text-muted);
          max-width: 520px;
          margin: 0 auto;
          line-height: 1.75;
          font-weight: 300;
        }

        /* ── DIVIDER ── */
        .hp-divider {
          width: 80px;
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
          margin: 28px auto 0;
        }

        /* ── LAYOUT WRAPPER ── */
        .hp-wrapper {
          max-width: 1100px;
          margin: 0 auto;
          padding: 0 24px 80px;
          display: flex;
          flex-direction: column;
          gap: 56px;
        }

        /* ── FEATURE CARDS ── */
        .hp-cards {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 18px;
        }
        @media (max-width: 900px) { .hp-cards { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 520px) { .hp-cards { grid-template-columns: 1fr; } }

        .hp-card {
          background: var(--black-card);
          border: 1px solid var(--border-gold);
          border-radius: 18px;
          padding: 28px 22px;
          cursor: pointer;
          transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
          position: relative;
          overflow: hidden;
        }
        .hp-card::before {
          content: '';
          position: absolute;
          inset: 0;
          background: radial-gradient(ellipse at 30% 0%, rgba(212,175,55,0.07) 0%, transparent 65%);
          pointer-events: none;
          opacity: 0;
          transition: opacity 0.3s ease;
        }
        .hp-card:hover {
          transform: translateY(-5px) scale(1.015);
          border-color: rgba(212, 175, 55, 0.55);
          box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px var(--glow-gold-strong);
        }
        .hp-card:hover::before { opacity: 1; }

        .hp-card-icon {
          font-size: 2rem;
          margin-bottom: 14px;
          display: block;
        }
        .hp-card h3 {
          font-family: 'Cormorant Garamond', serif;
          font-size: 1.15rem;
          font-weight: 600;
          color: #C9A84C;
          margin-bottom: 8px;
        }
        .hp-card p {
          font-size: 0.83rem;
          color: var(--text-muted);
          line-height: 1.6;
        }

        /* ── QUERY SECTION ── */
        .hp-query-box {
          background: linear-gradient(145deg, #161616 0%, #131313 100%);
          border: 1px solid var(--border-gold);
          border-radius: 24px;
          padding: 36px 32px;
          box-shadow: 0 4px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(212,175,55,0.08);
          position: relative;
          overflow: hidden;
        }
        .hp-query-box::before {
          content: '';
          position: absolute;
          top: -60px; right: -60px;
          width: 200px; height: 200px;
          background: radial-gradient(circle, rgba(212,175,55,0.06) 0%, transparent 70%);
          pointer-events: none;
        }

        .hp-query-box h2 {
          font-family: 'Cormorant Garamond', serif;
          font-size: 1.45rem;
          font-weight: 600;
          color: #C9A84C;
          margin-bottom: 18px;
          letter-spacing: 0.3px;
        }

        .hp-textarea {
          width: 100%;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(212,175,55,0.2);
          border-radius: 14px;
          color: var(--text-body);
          font-family: 'DM Sans', sans-serif;
          font-size: 0.95rem;
          padding: 16px 18px;
          resize: none;
          outline: none;
          transition: border-color 0.25s ease, box-shadow 0.25s ease;
          box-sizing: border-box;
          line-height: 1.7;
          backdrop-filter: blur(4px);
        }
        .hp-textarea::placeholder { color: #555; }
        .hp-textarea:focus {
          border-color: var(--gold-primary);
          box-shadow: 0 0 0 3px rgba(212,175,55,0.12), inset 0 1px 4px rgba(0,0,0,0.3);
        }

        .hp-query-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 18px;
          flex-wrap: wrap;
          gap: 12px;
        }

        .hp-btn-primary {
          background: linear-gradient(135deg, #A67C2E 0%, #C9A84C 50%, #B8960C 100%);
          color: #0B0B0B;
          font-family: 'DM Sans', sans-serif;
          font-weight: 600;
          font-size: 0.9rem;
          padding: 11px 28px;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          letter-spacing: 0.3px;
          transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
        }
        .hp-btn-primary:hover {
          transform: scale(1.04);
          box-shadow: 0 4px 20px rgba(212,175,55,0.45);
          filter: brightness(1.08);
        }

        .hp-lang-tag {
          font-size: 0.78rem;
          color: var(--text-muted);
          border: 1px solid rgba(212,175,55,0.18);
          border-radius: 20px;
          padding: 4px 12px;
          letter-spacing: 0.4px;
        }

        /* ── BOTTOM GRID ── */
        .hp-bottom {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }
        @media (max-width: 680px) { .hp-bottom { grid-template-columns: 1fr; } }

        .hp-panel {
          background: var(--black-card);
          border: 1px solid var(--border-gold);
          border-radius: 20px;
          padding: 28px 24px;
          box-shadow: 0 2px 20px rgba(0,0,0,0.35);
        }
        .hp-panel h3 {
          font-family: 'Cormorant Garamond', serif;
          font-size: 1.15rem;
          font-weight: 600;
          color: #C9A84C;
          margin-bottom: 18px;
          padding-bottom: 12px;
          border-bottom: 1px solid rgba(212,175,55,0.12);
        }

        /* Recent queries */
        .hp-recent-empty {
          font-size: 0.85rem;
          color: var(--text-muted);
          font-style: italic;
        }
        .hp-recent-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .hp-recent-item {
          padding: 12px 14px;
          border-radius: 10px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(212,175,55,0.1);
          color: var(--text-body);
          font-size: 0.87rem;
          cursor: pointer;
          transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
          line-height: 1.5;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .hp-recent-item:hover {
          background: rgba(212,175,55,0.08);
          border-color: rgba(212,175,55,0.35);
          transform: translateX(4px);
        }

        /* Quick action buttons */
        .hp-actions {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .hp-btn-action {
          width: 100%;
          padding: 12px 20px;
          border-radius: 12px;
          font-family: 'DM Sans', sans-serif;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          border: 1px solid transparent;
          transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease, border-color 0.2s ease;
          letter-spacing: 0.2px;
        }
        .hp-btn-action:hover {
          transform: scale(1.02);
          box-shadow: 0 4px 18px rgba(212,175,55,0.2);
        }
        .hp-btn-action-gold {
          background: linear-gradient(135deg, #A67C2E 0%, #C9A84C 100%);
          color: #0B0B0B;
          font-weight: 600;
        }
        .hp-btn-action-gold:hover {
          box-shadow: 0 4px 22px rgba(184,150,12,0.4);
          filter: brightness(1.06);
        }
        .hp-btn-action-outline {
          background: rgba(212,175,55,0.06);
          color: var(--text-heading);
          border-color: rgba(212,175,55,0.25);
        }
        .hp-btn-action-outline:hover {
          background: rgba(212,175,55,0.12);
          border-color: rgba(212,175,55,0.5);
        }
        .hp-btn-action-ghost {
          background: rgba(255,255,255,0.03);
          color: var(--text-muted);
          border-color: rgba(255,255,255,0.08);
        }
        .hp-btn-action-ghost:hover {
          background: rgba(255,255,255,0.06);
          border-color: rgba(212,175,55,0.2);
          color: var(--text-body);
        }
      `}</style>

      <div className="hp-root">
        {/* HERO */}
        <div className="hp-hero">
          <div className="hp-hero-glow" />
          <h1>Welcome to CaseIQ</h1>
          <p>
            A calm and intelligent legal companion helping you understand your
            rights, draft FIRs, and explore Indian criminal law.
          </p>
          <div className="hp-divider" />
        </div>

        <div className="hp-wrapper">

          {/* FEATURE CARDS */}
          <div className="hp-cards">
            <div className="hp-card" onClick={() => navigate("/chat")}>
              <span className="hp-card-icon">💬</span>
              <h3>Ask a Query</h3>
              <p>Instant legal explanations powered by AI.</p>
            </div>

            <div className="hp-card" onClick={() => navigate("/fir-draft")}>
              <span className="hp-card-icon">📄</span>
              <h3>Draft FIR</h3>
              <p>Generate structured FIR drafts easily.</p>
            </div>

            <div className="hp-card" onClick={() => navigate("/education")}>
              <span className="hp-card-icon">🛡️</span>
              <h3>Know Your Rights</h3>
              <p>Understand your constitutional protections.</p>
            </div>

            <div className="hp-card" onClick={() => navigate("/education")}>
              <span className="hp-card-icon">📚</span>
              <h3>Legal Learning</h3>
              <p>Learn BNS / BNSS concepts simply.</p>
            </div>
          </div>

          {/* QUERY SECTION */}
          <div className="hp-query-box">
            <h2>Ask Your Legal Query</h2>
            <textarea
              className="hp-textarea"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type your legal question here..."
              rows="4"
            />
            <div className="hp-query-footer">
              <button className="hp-btn-primary" onClick={handleSubmit}>
                Submit Query
              </button>
              <span className="hp-lang-tag">Language: English</span>
            </div>
          </div>

          {/* BOTTOM SECTION */}
          <div className="hp-bottom">

            {/* RECENT QUERIES */}
            <div className="hp-panel">
              <h3>Recent Queries</h3>
              {recentQueries.length === 0 ? (
                <p className="hp-recent-empty">No recent queries yet.</p>
              ) : (
                <ul className="hp-recent-list">
                  {recentQueries.map((item, index) => (
                    <li
                      key={index}
                      className="hp-recent-item"
                      onClick={() => handleRecentClick(item)}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* QUICK ACTIONS */}
            <div className="hp-panel">
              <h3>Quick Actions</h3>
              <div className="hp-actions">
                <button
                  className="hp-btn-action hp-btn-action-gold"
                  onClick={() => navigate("/fir-draft")}
                >
                  Draft a New FIR
                </button>
                <button
                  className="hp-btn-action hp-btn-action-outline"
                  onClick={() => navigate("/education")}
                >
                  Learn About Your Rights
                </button>
                <button
                  className="hp-btn-action hp-btn-action-ghost"
                  onClick={() => navigate("/education")}
                >
                  Understand BNS / BNSS Basics
                </button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  );
};

export default HomePage;
