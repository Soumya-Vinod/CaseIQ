import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';
import toast from 'react-hot-toast';

const safeText = (val) => {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);
  try { return JSON.stringify(val); } catch { return ''; }
};

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success('Copied');
        setTimeout(() => setCopied(false), 1800);
      }}
      style={{
        padding: '4px 7px',
        borderRadius: '6px',
        border: '1px solid rgba(212,175,55,0.12)',
        background: 'transparent',
        cursor: 'pointer',
        color: '#3A3A40',
        display: 'flex',
        alignItems: 'center',
        transition: 'all 0.2s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = '#9A7D3A';
        e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = '#3A3A40';
        e.currentTarget.style.borderColor = 'rgba(212,175,55,0.12)';
      }}
    >
      {copied ? <Check size={11} style={{ color: '#4CAF50' }} /> : <Copy size={11} />}
    </button>
  );
};

const MD = {
  p: ({ children }) => <p style={{ fontSize: '0.86rem', lineHeight: 1.7, color: '#D8D8D0', marginBottom: '8px' }}>{children}</p>,
  strong: ({ children }) => <strong style={{ fontWeight: 600, color: '#E8E0C8' }}>{children}</strong>,
  em: ({ children }) => <em style={{ fontStyle: 'italic', color: '#8A8A92' }}>{children}</em>,
  code: ({ children }) => (
    <code style={{
      background: 'rgba(212,175,55,0.1)',
      color: '#D4AF37',
      padding: '2px 6px',
      borderRadius: '4px',
      fontSize: '0.78rem',
      fontFamily: 'monospace',
    }}>{children}</code>
  ),
  ul: ({ children }) => <ul style={{ listStyle: 'none', margin: '6px 0', padding: 0 }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ listStyle: 'none', margin: '6px 0', padding: 0 }}>{children}</ol>,
  li: ({ children }) => (
    <li style={{
      display: 'flex',
      gap: '8px',
      fontSize: '0.86rem',
      lineHeight: 1.65,
      color: '#D8D8D0',
      marginBottom: '5px',
    }}>
      <span style={{ color: '#D4AF37', flexShrink: 0 }}>•</span>
      <span>{children}</span>
    </li>
  ),
};

const AIResponseWindow = ({ messages = [], loading }) => {
  const { user } = useAuth();
  const bottomRef = useRef(null);
  const userInitial = (user?.full_name || user?.email || 'U')[0].toUpperCase();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div style={{
      minHeight: '420px',
      maxHeight: 'calc(100vh - 360px)',
      overflowY: 'auto',
      padding: '4px',
    }}>
      {messages.length === 0 && !loading && (
        <EmptyState />
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {messages.map((msg, index) => {
          const text = safeText(msg.text);
          if (!text && msg.sender !== 'ai') return null;

          return (
            <div
              key={index}
              style={{
                display: 'flex',
                gap: '10px',
                justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                alignItems: 'flex-start',
              }}
            >
              {msg.sender === 'ai' && (
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #B8960C, #D4AF37)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.78rem',
                  flexShrink: 0,
                  marginTop: '2px',
                  boxShadow: '0 0 12px rgba(212,175,55,0.2)',
                }}>⚖</div>
              )}

              <div style={{
                maxWidth: '84%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                gap: '4px',
              }}>
                <div style={{
                  padding: msg.sender === 'user' ? '10px 16px' : '14px 18px',
                  borderRadius: msg.sender === 'user' ? '16px 16px 4px 16px' : '4px 16px 16px 16px',
                  background: msg.sender === 'user'
                    ? 'linear-gradient(135deg, #B8960C, #D4AF37)'
                    : msg.isBlocked
                    ? 'rgba(244,67,54,0.1)'
                    : 'rgba(18,15,6,0.96)',
                  border: msg.sender === 'user'
                    ? 'none'
                    : msg.isBlocked
                    ? '1px solid rgba(244,67,54,0.25)'
                    : '1px solid rgba(212,175,55,0.15)',
                  boxShadow: msg.sender === 'user'
                    ? '0 4px 14px rgba(212,175,55,0.22)'
                    : '0 4px 18px rgba(0,0,0,0.35)',
                }}>
                  {msg.sender === 'user' ? (
                    <p style={{
                      fontSize: '0.85rem',
                      color: '#0B0B0B',
                      fontWeight: 600,
                      lineHeight: 1.5,
                    }}>
                      {text}
                    </p>
                  ) : (
                    <ReactMarkdown components={MD}>
                      {text}
                    </ReactMarkdown>
                  )}
                </div>

                {msg.sender === 'ai' && !msg.isBlocked && text && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', paddingLeft: '4px' }}>
                    <CopyButton text={text} />
                    {msg.isFollowup && (
                      <span style={{
                        fontSize: '0.62rem',
                        color: '#9A7D3A',
                        background: 'rgba(212,175,55,0.06)',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        letterSpacing: '0.3px',
                      }}>
                        FOLLOW-UP
                      </span>
                    )}
                    <span style={{ fontSize: '0.66rem', color: '#3A3A40' }}>
                      {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
              </div>

              {msg.sender === 'user' && (
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'rgba(212,175,55,0.12)',
                  border: '1px solid rgba(212,175,55,0.25)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: '#C9A84C',
                  flexShrink: 0,
                  marginTop: '2px',
                }}>
                  {userInitial}
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #B8960C, #D4AF37)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.78rem',
              flexShrink: 0,
            }}>⚖</div>
            <div style={{
              padding: '14px 18px',
              borderRadius: '4px 16px 16px 16px',
              background: 'rgba(18,15,6,0.96)',
              border: '1px solid rgba(212,175,55,0.15)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {[0, 150, 300].map((d) => (
                  <div key={d} style={{
                    width: '5px',
                    height: '5px',
                    borderRadius: '50%',
                    background: '#D4AF37',
                    animation: 'bounce 1.2s ease-in-out infinite',
                    animationDelay: `${d}ms`,
                  }} />
                ))}
                <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0.6);opacity:0.4}40%{transform:scale(1);opacity:1}}`}</style>
                <span style={{ fontSize: '0.72rem', color: '#555560', marginLeft: '6px' }}>
                  Analyzing your query...
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

const EmptyState = () => (
  <div style={{
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '380px',
    gap: '16px',
    textAlign: 'center',
    padding: '32px 20px',
  }}>
    <div style={{
      width: '60px',
      height: '60px',
      borderRadius: '16px',
      background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(212,175,55,0.05))',
      border: '1px solid rgba(212,175,55,0.25)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1.7rem',
      boxShadow: '0 0 40px rgba(212,175,55,0.1)',
    }}>⚖️</div>
    <div>
      <p className="serif-heading" style={{ fontSize: '1.3rem', marginBottom: '6px' }}>
        CaseIQ Legal Assistant
      </p>
      <p style={{ fontSize: '0.82rem', color: '#555560', maxWidth: '340px', lineHeight: 1.6 }}>
        Ask any question about Indian law. Get clear answers, applicable sections, and actionable steps.
      </p>
    </div>
  </div>
);

export default AIResponseWindow;