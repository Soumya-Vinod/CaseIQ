import { useEffect, useState } from 'react';
import { awarenessAPI } from '../services/api';

const EducationPage = () => {
  const [apiContent, setApiContent] = useState([]);

  useEffect(() => {
    awarenessAPI.getEducation()
      .then((res) => setApiContent(res.data.results || []))
      .catch(() => {});
  }, []);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,500;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

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

        .ed-shell {
          min-height: 100vh;
          background: var(--black-0);
          background-image:
            radial-gradient(ellipse 80% 45% at 50% -8%, rgba(212,175,55,0.12) 0%, transparent 60%),
            radial-gradient(ellipse 45% 30% at 95% 90%, rgba(212,175,55,0.05) 0%, transparent 55%);
          position: relative;
          font-family: var(--sans);
        }

        .ed-shell::before {
          content: '';
          position: fixed;
          inset: 0;
          background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
          pointer-events: none;
          z-index: 0;
        }

        .ed-root {
          max-width: 1100px;
          margin: 0 auto;
          padding: 52px 28px 88px;
          display: flex;
          flex-direction: column;
          gap: 52px;
          position: relative;
          z-index: 1;
        }

        /* ── HERO ── */
        .ed-hero {
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 14px;
        }

        .ed-eyebrow {
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 3.5px;
          text-transform: uppercase;
          color: var(--gold-muted);
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .ed-eyebrow::before, .ed-eyebrow::after {
          content: '';
          display: block;
          width: 36px;
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--gold-muted));
        }

        .ed-eyebrow::after {
          background: linear-gradient(90deg, var(--gold-muted), transparent);
        }

        .ed-title {
          font-family: var(--serif);
          font-size: clamp(2.2rem, 5vw, 3.5rem);
          font-weight: 700;
          font-style: italic;
          background: linear-gradient(135deg, var(--gold-main) 0%, var(--gold-bright) 50%, var(--gold-mid) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          filter: drop-shadow(0 0 28px rgba(212,175,55,0.28));
          line-height: 1.1;
          margin: 0;
        }

        .ed-subtitle {
          font-size: 0.9rem;
          color: var(--text-muted);
          max-width: 520px;
          line-height: 1.65;
          font-weight: 400;
        }

        /* ── DIVIDER ── */
        .ed-divider {
          height: 1px;
          background: linear-gradient(90deg, transparent, var(--border-gold), rgba(212,175,55,0.35), var(--border-gold), transparent);
          margin: -20px 0;
        }

        /* ── LATEST GUIDES ── */
        .ed-guides-label {
          font-size: 0.68rem;
          font-weight: 600;
          letter-spacing: 3px;
          text-transform: uppercase;
          color: var(--gold-muted);
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .ed-guides-label::after {
          content: '';
          flex: 1;
          height: 1px;
          background: linear-gradient(90deg, var(--border-gold), transparent);
        }

        .ed-guides-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }

        @media (max-width: 640px) { .ed-guides-grid { grid-template-columns: 1fr; } }

        .ed-guide-card {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-radius: 16px;
          padding: 22px 20px;
          transition: all 0.25s var(--ease-gold);
          position: relative;
          overflow: hidden;
        }

        .ed-guide-card::before {
          content: '';
          position: absolute;
          top: 0; left: 10%; right: 10%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.35), transparent);
        }

        .ed-guide-card:hover {
          transform: translateY(-3px);
          border-color: var(--border-gold-h);
          box-shadow: 0 12px 36px rgba(0,0,0,0.55), 0 0 20px rgba(212,175,55,0.1);
        }

        .ed-guide-tag {
          font-size: 0.67rem;
          font-weight: 600;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          background: rgba(212,175,55,0.1);
          border: 1px solid rgba(212,175,55,0.25);
          color: var(--gold-mid);
          padding: 3px 10px;
          border-radius: 20px;
          display: inline-block;
          margin-bottom: 12px;
        }

        .ed-guide-title {
          font-family: var(--serif);
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--text-primary);
          margin: 0 0 8px;
          line-height: 1.3;
        }

        .ed-guide-summary {
          font-size: 0.8rem;
          color: var(--text-muted);
          line-height: 1.6;
        }

        /* ── SECTION GRID ── */
        .ed-section-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 18px;
        }

        @media (max-width: 700px) { .ed-section-grid { grid-template-columns: 1fr; } }

        /* Section cards */
        .ed-card {
          background: var(--surface);
          border: 1px solid var(--border-gold);
          border-radius: 20px;
          padding: 28px 24px;
          position: relative;
          overflow: hidden;
          transition: all 0.28s var(--ease-gold);
          color: var(--text-primary);
        }

        .ed-card::before {
          content: '';
          position: absolute;
          top: 0; left: 8%; right: 8%;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent);
        }

        /* left accent bar */
        .ed-card::after {
          content: '';
          position: absolute;
          left: 0; top: 20%; bottom: 20%;
          width: 2px;
          background: linear-gradient(180deg, transparent, rgba(212,175,55,0.5), transparent);
          border-radius: 0 2px 2px 0;
          opacity: 0;
          transition: opacity 0.25s ease;
        }

        .ed-card:hover {
          transform: translateY(-4px);
          border-color: var(--border-gold-h);
          box-shadow: 0 16px 48px rgba(0,0,0,0.6), 0 0 28px rgba(212,175,55,0.1);
        }

        .ed-card:hover::after { opacity: 1; }

        /* glow blob inside card */
        .ed-card-glow {
          position: absolute;
          top: -30px; right: -30px;
          width: 130px; height: 130px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(212,175,55,0.07) 0%, transparent 70%);
          pointer-events: none;
        }

        .ed-card-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 18px;
        }

        .ed-card-icon {
          font-size: 1.6rem;
          filter: drop-shadow(0 2px 8px rgba(212,175,55,0.35));
          flex-shrink: 0;
        }

        .ed-card-title {
          font-family: var(--serif);
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--gold-mid);
          line-height: 1.25;
          letter-spacing: 0.2px;
        }

        .ed-card-body {
          font-size: 0.82rem;
          color: #8A8A96;
          line-height: 1.7;
          position: relative;
          z-index: 1;
        }

        .ed-card-body ul, .ed-card-body ol {
          margin: 0;
          padding-left: 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .ed-card-body li {
          padding-left: 4px;
        }

        .ed-card-body li::marker {
          color: var(--gold-muted);
        }

        .ed-card-body strong {
          color: #B0B0BA;
          font-weight: 600;
        }

        /* Emergency card special accent */
        .ed-card--emergency {
          border-color: rgba(212,175,55,0.28);
          background: rgba(212,175,55,0.04);
        }

        .ed-card--emergency .ed-card-title { color: var(--gold-main); }

        @media (max-width: 640px) {
          .ed-root { padding: 28px 16px 60px; gap: 36px; }
          .ed-card { padding: 22px 18px; }
        }
      `}</style>

      <div className="ed-shell">
        <div className="ed-root">

          {/* Hero */}
          <div className="ed-hero">
            <p className="ed-eyebrow">Know Your Rights</p>
            <h1 className="ed-title">Legal Awareness & Education</h1>
            <p className="ed-subtitle">
              Understand your rights, procedures, and protections in clear and practical language — rooted in Indian law.
            </p>
          </div>

          <div className="ed-divider" />

          {/* API Guides */}
          {apiContent.length > 0 && (
            <div>
              <p className="ed-guides-label">📰 Latest Legal Guides</p>
              <div className="ed-guides-grid">
                {apiContent.map((item) => (
                  <div key={item.id} className="ed-guide-card">
                    <span className="ed-guide-tag">{item.content_type}</span>
                    <h3 className="ed-guide-title">{item.title}</h3>
                    <p className="ed-guide-summary">{item.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section Cards */}
          <div className="ed-section-grid">
            <EdCard icon="⚖️" title="Know Your Fundamental Rights">
              <ul>
                <li><strong>Right to Equality:</strong> Equal protection under the law.</li>
                <li><strong>Right to Freedom:</strong> Speech, expression, movement.</li>
                <li><strong>Right Against Exploitation:</strong> Protection from forced labour.</li>
                <li><strong>Right to Constitutional Remedies:</strong> Approach courts if violated.</li>
              </ul>
            </EdCard>

            <EdCard icon="🚨" title="Rights During Arrest">
              <ul>
                <li>Be informed of reason for arrest.</li>
                <li>Right to remain silent.</li>
                <li>Right to consult a lawyer.</li>
                <li>Produced before magistrate within 24 hours.</li>
              </ul>
            </EdCard>

            <EdCard icon="📄" title="FIR Filing Process">
              <ol>
                <li>Visit nearest police station.</li>
                <li>Explain the incident clearly.</li>
                <li>Ensure FIR is read before signing.</li>
                <li>Request your free FIR copy.</li>
              </ol>
            </EdCard>

            <EdCard icon="📍" title="What is Zero FIR?">
              <p style={{ margin: 0 }}>Zero FIR allows filing a complaint at <strong>any police station</strong> regardless of jurisdiction — the station then transfers it to the appropriate authority.</p>
            </EdCard>

            <EdCard icon="🔓" title="Bail Basics">
              <ul>
                <li><strong>Bailable Offences:</strong> Bail is a legal right.</li>
                <li><strong>Non-Bailable:</strong> Court decides at its discretion.</li>
                <li>Anticipatory bail can be sought before arrest.</li>
              </ul>
            </EdCard>

            <EdCard icon="🛡️" title="Protection for Women & Children">
              <ul>
                <li>Female officer mandatory for arrest of women.</li>
                <li>POCSO Act for child protection.</li>
                <li>Legal protection against domestic violence.</li>
              </ul>
            </EdCard>

            <EdCard icon="📚" title="Key Concepts in BNS / BNSS">
              <ul>
                <li>Cognizable vs Non-Cognizable offences</li>
                <li>Compoundable vs Non-Compoundable</li>
                <li>Investigation & Charge Sheet process</li>
                <li>Trial & Appeal structure</li>
              </ul>
            </EdCard>

            <EdCard icon="📞" title="Emergency Contacts" emergency>
              <ul>
                <li><strong>Police:</strong> 100</li>
                <li><strong>Women Helpline:</strong> 181</li>
                <li><strong>Child Helpline:</strong> 1098</li>
                <li><strong>National Emergency:</strong> 112</li>
              </ul>
            </EdCard>
          </div>

        </div>
      </div>
    </>
  );
};

const EdCard = ({ icon, title, children, emergency }) => (
  <div className={`ed-card${emergency ? ' ed-card--emergency' : ''}`}>
    <div className="ed-card-glow" />
    <div className="ed-card-header">
      <span className="ed-card-icon">{icon}</span>
      <h2 className="ed-card-title">{title}</h2>
    </div>
    <div className="ed-card-body">{children}</div>
  </div>
);

export default EducationPage;
