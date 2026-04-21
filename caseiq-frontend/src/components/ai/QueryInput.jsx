import { useState, useCallback } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';
import { useSettings } from '../../context/SettingsContext';
import useSpeechInput from '../../hooks/useSpeechInput';

const QueryInput = ({ onSend, disabled }) => {
  const [query, setQuery] = useState('');
  const { language } = useSettings();

  const langMap = { English: 'en', Hindi: 'hi', Marathi: 'mr', Tamil: 'ta' };

  const handleResult = useCallback((transcript) => {
    setQuery(transcript);
  }, []);

  const { listening, supported, startListening, stopListening } = useSpeechInput(handleResult);

  const handleSubmit = () => {
    if (!query.trim() || disabled) return;
    onSend(query);
    setQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleVoice = () => {
    if (listening) stopListening();
    else startListening(langMap[language] || 'en');
  };

  return (
    <>
      <style>{`
        .qi-wrap { display: flex; flex-direction: column; gap: 10px; }

        .qi-row { display: flex; gap: 10px; align-items: flex-end; }

        /* ── TEXTAREA ── */
        .qi-textarea-wrap { flex: 1; position: relative; }

        .qi-textarea {
          width: 100%;
          border-radius: 14px;
          padding: 13px 48px 13px 16px;
          border: 1px solid rgba(212,175,55,0.2);
          background: rgba(10, 9, 4, 0.85);
          color: #E0D8BC;
          font-family: 'DM Sans', sans-serif;
          font-size: 0.855rem;
          line-height: 1.6;
          resize: none;
          outline: none;
          transition: border-color 0.22s ease, box-shadow 0.22s ease, background 0.22s ease;
          box-shadow: inset 0 2px 8px rgba(0,0,0,0.4), 0 1px 0 rgba(212,175,55,0.06) inset;
          scrollbar-width: thin;
          scrollbar-color: rgba(212,175,55,0.2) transparent;
        }

        .qi-textarea::placeholder {
          color: #3E3E48;
          font-size: 0.83rem;
        }

        .qi-textarea:focus {
          border-color: rgba(212,175,55,0.45);
          background: rgba(14, 12, 5, 0.95);
          box-shadow:
            inset 0 2px 8px rgba(0,0,0,0.5),
            0 0 0 3px rgba(212,175,55,0.07),
            0 0 20px rgba(212,175,55,0.08);
        }

        .qi-textarea:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }

        /* Listening state */
        .qi-textarea--listening {
          border-color: rgba(220,60,60,0.5) !important;
          background: rgba(30, 8, 8, 0.85) !important;
          color: #E8A090 !important;
          box-shadow:
            inset 0 2px 8px rgba(0,0,0,0.5),
            0 0 0 3px rgba(220,60,60,0.08) !important;
        }

        .qi-textarea--listening::placeholder { color: rgba(220,100,80,0.5) !important; }

        /* Listening dots inside textarea */
        .qi-listen-dots {
          position: absolute;
          right: 14px;
          top: 14px;
          display: flex;
          gap: 3px;
          align-items: center;
        }

        .qi-listen-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: rgba(220,80,60,0.9);
        }

        .qi-listen-dot:nth-child(1) { animation: qi-bounce 1.1s ease-in-out infinite 0ms; }
        .qi-listen-dot:nth-child(2) { animation: qi-bounce 1.1s ease-in-out infinite 140ms; }
        .qi-listen-dot:nth-child(3) { animation: qi-bounce 1.1s ease-in-out infinite 280ms; }

        @keyframes qi-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-5px); opacity: 1; }
        }

        /* ── BUTTONS ── */
        .qi-btns { display: flex; flex-direction: column; gap: 8px; }

        .qi-btn {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.22s ease;
          flex-shrink: 0;
          position: relative;
          overflow: hidden;
        }

        .qi-btn:disabled { opacity: 0.35; cursor: not-allowed; }

        /* Mic button — normal */
        .qi-btn--mic {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          color: #6B6B75;
        }

        .qi-btn--mic:hover:not(:disabled) {
          border-color: rgba(212,175,55,0.35);
          color: #C9A84C;
          background: rgba(212,175,55,0.07);
          box-shadow: 0 0 16px rgba(212,175,55,0.12);
        }

        /* Mic button — listening */
        .qi-btn--listening {
          background: rgba(200,50,40,0.15);
          border: 1px solid rgba(220,80,60,0.4);
          color: #E07060;
          animation: qi-pulse-border 1.4s ease-in-out infinite;
        }

        @keyframes qi-pulse-border {
          0%, 100% { box-shadow: 0 0 0 0 rgba(220,80,60,0.3); }
          50% { box-shadow: 0 0 0 6px rgba(220,80,60,0); }
        }

        /* Send button */
        .qi-btn--send {
          background: linear-gradient(135deg, #B8960C 0%, #D4AF37 55%, #FFD700 100%);
          color: #0B0B0B;
          box-shadow: 0 4px 14px rgba(212,175,55,0.28);
        }

        .qi-btn--send::before {
          content: '';
          position: absolute;
          top: 0; left: -100%;
          width: 100%; height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
          transition: left 0.38s ease;
        }

        .qi-btn--send:hover:not(:disabled) {
          transform: translateY(-2px) scale(1.05);
          box-shadow: 0 8px 24px rgba(212,175,55,0.42);
          filter: brightness(1.08);
        }

        .qi-btn--send:hover:not(:disabled)::before { left: 100%; }

        .qi-btn--send:disabled {
          background: rgba(212,175,55,0.12);
          color: rgba(212,175,55,0.25);
          box-shadow: none;
        }

        /* ── FOOTER ── */
        .qi-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0 2px;
        }

        .qi-footer-left {
          font-size: 0.71rem;
          color: #3A3A44;
          display: flex;
          align-items: center;
          gap: 6px;
          letter-spacing: 0.2px;
        }

        .qi-footer-left--active { color: rgba(220,80,60,0.7); }

        .qi-footer-right {
          font-size: 0.71rem;
          color: #3A3A44;
          letter-spacing: 0.2px;
        }

        /* Char counter */
        .qi-char-count {
          font-size: 0.68rem;
          color: #3A3A44;
          transition: color 0.2s ease;
        }

        .qi-char-count--warn { color: rgba(212,175,55,0.6); }

        @media (max-width: 480px) {
          .qi-btn { width: 40px; height: 40px; border-radius: 10px; }
          .qi-textarea { font-size: 0.82rem; padding: 11px 44px 11px 14px; }
        }
      `}</style>

      <div className="qi-wrap">
        <div className="qi-row">

          {/* Textarea */}
          <div className="qi-textarea-wrap">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={
                listening
                  ? '🎤 Listening… speak now'
                  : 'Type your legal question… (Enter to send, Shift+Enter for new line)'
              }
              rows={2}
              className={`qi-textarea${listening ? ' qi-textarea--listening' : ''}`}
            />
            {listening && (
              <div className="qi-listen-dots">
                <div className="qi-listen-dot" />
                <div className="qi-listen-dot" />
                <div className="qi-listen-dot" />
              </div>
            )}
          </div>

          {/* Buttons */}
          <div className="qi-btns">
            {supported && (
              <button
                onClick={toggleVoice}
                disabled={disabled}
                title={listening ? 'Stop listening' : `Speak in ${language}`}
                className={`qi-btn ${listening ? 'qi-btn--listening' : 'qi-btn--mic'}`}
              >
                {listening ? <MicOff size={16} /> : <Mic size={16} />}
              </button>
            )}

            <button
              onClick={handleSubmit}
              disabled={disabled || !query.trim()}
              className="qi-btn qi-btn--send"
              title="Send (Enter)"
            >
              <Send size={16} />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="qi-footer">
          <span className={`qi-footer-left${listening ? ' qi-footer-left--active' : ''}`}>
            {supported
              ? listening
                ? '🔴 Recording…'
                : `🎤 Voice input available in ${language}`
              : 'Voice input not supported'}
          </span>
          <span className="qi-footer-right">Enter to send · Shift+Enter for new line</span>
        </div>
      </div>
    </>
  );
};

export default QueryInput;
