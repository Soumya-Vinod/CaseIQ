import { useEffect, useRef, useState } from 'react';
import { useSettings } from '../../context/SettingsContext';
import { useAuth } from '../../context/AuthContext';
import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';
import toast from 'react-hot-toast';

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-lg transition"
      style={{
        background: 'transparent',
        color: '#6B6B75',
        border: 'none',
        cursor: 'pointer',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = 'rgba(212,175,55,0.1)';
        e.currentTarget.style.color = '#D4AF37';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'transparent';
        e.currentTarget.style.color = '#6B6B75';
      }}
      title="Copy response"
    >
      {copied
        ? <Check size={13} style={{ color: '#D4AF37' }} />
        : <Copy size={13} />
      }
    </button>
  );
};

const AIResponseWindow = ({ messages = [], loading }) => {
  const { darkMode } = useSettings();
  const { user } = useAuth();
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const userInitial = (user?.full_name || user?.email || 'U')[0].toUpperCase();

  return (
    <div
      style={{
        height: '560px',
        overflowY: 'auto',
        borderRadius: '16px',
        padding: '20px',
        background: 'transparent',
        border: 'none',
        scrollbarWidth: 'thin',
        scrollbarColor: 'rgba(212,175,55,0.2) transparent',
      }}
    >
      <style>{`
        .airw-scroll::-webkit-scrollbar { width: 4px; }
        .airw-scroll::-webkit-scrollbar-track { background: transparent; }
        .airw-scroll::-webkit-scrollbar-thumb { background: rgba(212,175,55,0.2); border-radius: 4px; }
        .airw-scroll::-webkit-scrollbar-thumb:hover { background: rgba(212,175,55,0.4); }

        .airw-ai-bubble {
          background: rgba(22, 19, 8, 0.95);
          color: #D8CFA8;
          border: 1px solid rgba(212,175,55,0.18);
          border-radius: 0 16px 16px 16px;
          padding: 14px 16px;
          font-size: 0.855rem;
          line-height: 1.7;
          box-shadow: 0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(212,175,55,0.08);
          position: relative;
        }

        .airw-user-bubble {
          background: rgba(68, 54, 39, 0.9);
          color: #F0E8D0;
          border: 1px solid rgba(212,175,55,0.25);
          border-radius: 16px 0 16px 16px;
          padding: 12px 16px;
          font-size: 0.855rem;
          line-height: 1.65;
          box-shadow: 0 4px 16px rgba(0,0,0,0.35);
        }

        .airw-loading-bubble {
          background: rgba(22, 19, 8, 0.95);
          border: 1px solid rgba(212,175,55,0.15);
          border-radius: 0 16px 16px 16px;
          padding: 14px 18px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }

        /* Markdown styles inside AI bubble */
        .airw-md h1, .airw-md h2 {
          font-size: 0.9rem;
          font-weight: 700;
          color: #D4AF37;
          margin: 16px 0 8px;
          font-family: 'Cormorant Garamond', serif;
          letter-spacing: 0.3px;
        }
        .airw-md h1:first-child, .airw-md h2:first-child { margin-top: 0; }

        .airw-md h3 {
          font-size: 0.84rem;
          font-weight: 600;
          color: #C9A84C;
          margin: 12px 0 6px;
        }
        .airw-md h3:first-child { margin-top: 0; }

        .airw-md p {
          margin: 0 0 10px;
          color: #D8CFA8;
        }
        .airw-md p:last-child { margin-bottom: 0; }

        .airw-md ul, .airw-md ol {
          margin: 8px 0;
          padding: 0;
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .airw-md li {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          color: #CCC4A0;
          font-size: 0.84rem;
          line-height: 1.6;
        }

        .airw-md li::before {
          content: '◆';
          color: rgba(212,175,55,0.5);
          font-size: 0.5rem;
          margin-top: 6px;
          flex-shrink: 0;
        }

        .airw-md strong {
          font-weight: 600;
          color: #D4AF37;
        }

        .airw-md em {
          font-style: italic;
          color: #8A8A94;
          font-size: 0.8rem;
        }

        .airw-md hr {
          border: none;
          border-top: 1px solid rgba(212,175,55,0.12);
          margin: 14px 0;
        }

        .airw-md code {
          background: rgba(212,175,55,0.08);
          color: #D4AF37;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.78rem;
          font-family: 'JetBrains Mono', monospace;
          border: 1px solid rgba(212,175,55,0.15);
        }

        .airw-md blockquote {
          border-left: 3px solid rgba(212,175,55,0.4);
          padding-left: 12px;
          margin: 10px 0;
          color: #8A8A94;
          font-size: 0.8rem;
          font-style: italic;
        }

        .airw-dot-1 { animation: airwBounce 1.2s ease-in-out infinite; animation-delay: 0ms; }
        .airw-dot-2 { animation: airwBounce 1.2s ease-in-out infinite; animation-delay: 150ms; }
        .airw-dot-3 { animation: airwBounce 1.2s ease-in-out infinite; animation-delay: 300ms; }

        @keyframes airwBounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-6px); opacity: 1; }
        }

        .airw-confidence-bar {
          background: rgba(212,175,55,0.12);
          border-radius: 99px;
          height: 4px;
          flex: 1;
          overflow: hidden;
        }
        .airw-confidence-fill {
          height: 100%;
          border-radius: 99px;
          background: linear-gradient(90deg, rgba(212,175,55,0.6), #D4AF37);
          transition: width 0.7s ease;
        }

        .airw-avatar-ai {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: linear-gradient(135deg, rgba(212,175,55,0.3), rgba(212,175,55,0.1));
          border: 1px solid rgba(212,175,55,0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          flex-shrink: 0;
          margin-top: 4px;
          box-shadow: 0 0 12px rgba(212,175,55,0.15);
        }

        .airw-avatar-user {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(68, 54, 39, 0.9);
          border: 1px solid rgba(212,175,55,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 11px;
          font-weight: 700;
          color: #D4AF37;
          flex-shrink: 0;
          margin-top: 4px;
          box-shadow: 0 0 10px rgba(212,175,55,0.1);
        }

        .airw-empty-icon {
          width: 56px;
          height: 56px;
          border-radius: 16px;
          background: rgba(212,175,55,0.08);
          border: 1px solid rgba(212,175,55,0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          margin-bottom: 16px;
          box-shadow: 0 0 24px rgba(212,175,55,0.1);
        }

        .airw-timestamp {
          font-size: 0.7rem;
          color: #4A4A52;
          margin-left: 4px;
        }
      `}</style>

      {/* Empty State */}
      {messages.length === 0 && !loading && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          textAlign: 'center',
          gap: '8px',
        }}>
          <div className="airw-empty-icon">⚖️</div>
          <h3 style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: '1.2rem',
            fontWeight: 600,
            color: '#C9A84C',
            margin: '0 0 6px',
          }}>
            CaseIQ Legal Assistant
          </h3>
          <p style={{
            fontSize: '0.82rem',
            color: '#5A5A62',
            maxWidth: '340px',
            lineHeight: 1.65,
            margin: 0,
          }}>
            Ask any question about Indian criminal law, your rights, FIR filing, or BNS/BNSS sections.
          </p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              display: 'flex',
              gap: '10px',
              justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {/* AI Avatar */}
            {msg.sender === 'ai' && (
              <div className="airw-avatar-ai">⚖</div>
            )}

            <div style={{
              maxWidth: '85%',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            }}>
              {/* Bubble */}
              {msg.sender === 'user' ? (
                <div className="airw-user-bubble">
                  <p style={{ margin: 0, lineHeight: 1.65 }}>{msg.text}</p>
                </div>
              ) : (
                <div className="airw-ai-bubble">
                  <div className="airw-md">
                    <ReactMarkdown
                      components={{
                        h1: ({ children }) => <h1>{children}</h1>,
                        h2: ({ children }) => <h2>{children}</h2>,
                        h3: ({ children }) => <h3>{children}</h3>,
                        p: ({ children }) => <p>{children}</p>,
                        ul: ({ children }) => <ul>{children}</ul>,
                        ol: ({ children }) => <ol>{children}</ol>,
                        li: ({ children }) => <li><span>{children}</span></li>,
                        strong: ({ children }) => <strong>{children}</strong>,
                        em: ({ children }) => <em>{children}</em>,
                        hr: () => <hr />,
                        code: ({ children }) => <code>{children}</code>,
                        blockquote: ({ children }) => <blockquote>{children}</blockquote>,
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  </div>

                  {/* Confidence Score */}
                  {msg.confidence && (
                    <div style={{
                      marginTop: '12px',
                      paddingTop: '12px',
                      borderTop: '1px solid rgba(212,175,55,0.12)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.72rem', color: '#5A5A62', whiteSpace: 'nowrap' }}>
                          Confidence
                        </span>
                        <div className="airw-confidence-bar">
                          <div
                            className="airw-confidence-fill"
                            style={{ width: `${Math.round(msg.confidence * 100)}%` }}
                          />
                        </div>
                        <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#C9A84C', whiteSpace: 'nowrap' }}>
                          {Math.round(msg.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Actions row for AI */}
              {msg.sender === 'ai' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', paddingLeft: '4px' }}>
                  <CopyButton text={msg.text} />
                  <span className="airw-timestamp">
                    {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              )}
            </div>

            {/* User Avatar */}
            {msg.sender === 'user' && (
              <div className="airw-avatar-user">{userInitial}</div>
            )}
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-start' }}>
            <div className="airw-avatar-ai">⚖</div>
            <div className="airw-loading-bubble">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div className="airw-dot-1" style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: 'rgba(212,175,55,0.8)',
                }} />
                <div className="airw-dot-2" style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: 'rgba(212,175,55,0.5)',
                }} />
                <div className="airw-dot-3" style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: 'rgba(212,175,55,0.3)',
                }} />
                <span style={{ fontSize: '0.75rem', color: '#5A5A62', marginLeft: '4px' }}>
                  Analysing your query…
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default AIResponseWindow;
