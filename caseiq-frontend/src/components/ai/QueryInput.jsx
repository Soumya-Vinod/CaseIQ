import { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

const SUGGESTIONS = [
  'What are my rights when arrested by police?',
  'How to file a complaint at police station?',
  'What is the punishment for theft under BNS?',
  'Can police enter my house without a warrant?',
  'What is anticipatory bail and how to get it?',
  'What is Zero FIR and when can I use it?',
  'My employer is not paying salary. What can I do?',
  'What are my rights as a domestic violence victim?',
  'How to report cybercrime in India?',
  'What is the difference between cognizable and non-cognizable offence?',
  'What happens after a complaint is filed?',
  'What is the punishment for cheating and fraud?',
  'Can I record a conversation as evidence?',
  'What is defamation under BNS?',
  'How to get bail for a non-bailable offence?',
  'Rights of women during arrest in India',
  'How to file a consumer complaint online?',
  'Can police arrest without a complaint?',
];

const QueryInput = ({ onSend, disabled }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSugg, setShowSugg] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [isListening, setIsListening] = useState(false);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setSuggestions([]);
      setShowSugg(false);
      return;
    }
    const filtered = SUGGESTIONS.filter((s) =>
      s.toLowerCase().includes(query.toLowerCase())
    ).slice(0, 4);
    setSuggestions(filtered);
    setShowSugg(filtered.length > 0);
    setSelectedIdx(-1);
  }, [query]);

  const toggleVoice = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) return;
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.lang = 'en-IN';
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e) => {
      setQuery(e.results[0][0].transcript);
      setIsListening(false);
    };
    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);
    recognitionRef.current = rec;
    rec.start();
    setIsListening(true);
  };

  const handleSubmit = () => {
    if (!query.trim() || disabled) return;
    onSend(query.trim());
    setQuery('');
    setSuggestions([]);
    setShowSugg(false);
    setSelectedIdx(-1);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (selectedIdx >= 0 && suggestions[selectedIdx]) {
        setQuery(suggestions[selectedIdx]);
        setShowSugg(false);
        setSelectedIdx(-1);
      } else {
        handleSubmit();
      }
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((p) => Math.min(p + 1, suggestions.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((p) => Math.max(p - 1, -1));
    }
    if (e.key === 'Escape') {
      setShowSugg(false);
      setSelectedIdx(-1);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      {showSugg && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: 0,
          right: 0,
          marginBottom: '8px',
          background: 'rgba(14,12,6,0.98)',
          border: '1px solid rgba(212,175,55,0.2)',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: '0 -8px 32px rgba(0,0,0,0.6)',
          zIndex: 50,
        }}>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onMouseDown={() => {
                setQuery(s);
                setShowSugg(false);
                inputRef.current?.focus();
              }}
              style={{
                width: '100%',
                textAlign: 'left',
                padding: '10px 16px',
                border: 'none',
                borderTop: i > 0 ? '1px solid rgba(212,175,55,0.08)' : 'none',
                background: i === selectedIdx ? 'rgba(212,175,55,0.1)' : 'transparent',
                cursor: 'pointer',
                fontSize: '0.82rem',
                color: i === selectedIdx ? '#C9A84C' : '#6B6B75',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                transition: 'all 0.15s ease',
                fontFamily: 'inherit',
              }}
            >
              <span style={{ color: '#D4AF37', fontSize: '0.72rem', flexShrink: 0 }}>⚖</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s}
              </span>
            </button>
          ))}
        </div>
      )}

      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: '8px',
        padding: '8px',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(212,175,55,0.15)',
        borderRadius: '14px',
        transition: 'all 0.2s ease',
      }}
        onFocusCapture={(e) => {
          e.currentTarget.style.borderColor = 'rgba(212,175,55,0.4)';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(212,175,55,0.08)';
        }}
        onBlurCapture={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) {
            e.currentTarget.style.borderColor = 'rgba(212,175,55,0.15)';
            e.currentTarget.style.boxShadow = 'none';
            setTimeout(() => setShowSugg(false), 150);
          }
        }}
      >
        <textarea
          ref={inputRef}
          rows={1}
          placeholder="Ask any legal question... (Enter to send)"
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 2 && setShowSugg(suggestions.length > 0)}
          style={{
            flex: 1,
            resize: 'none',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            fontSize: '0.85rem',
            color: '#D8D8D0',
            lineHeight: 1.6,
            minHeight: '36px',
            maxHeight: '120px',
            padding: '6px 8px',
            fontFamily: "'DM Sans', sans-serif",
          }}
        />

        <button
          onClick={toggleVoice}
          aria-label="Voice input"
          style={{
            padding: '8px',
            borderRadius: '8px',
            border: '1px solid rgba(212,175,55,0.12)',
            background: isListening ? 'rgba(255,100,100,0.1)' : 'transparent',
            cursor: 'pointer',
            color: isListening ? '#ff6b6b' : '#555560',
            display: 'flex',
            alignItems: 'center',
            flexShrink: 0,
            transition: 'all 0.2s ease',
            animation: isListening ? 'pulse 1.5s ease-in-out infinite' : 'none',
          }}
        >
          {isListening ? <MicOff size={14} /> : <Mic size={14} />}
        </button>

        <button
          onClick={handleSubmit}
          disabled={disabled || !query.trim()}
          aria-label="Send"
          style={{
            padding: '8px 16px',
            borderRadius: '8px',
            border: 'none',
            background: query.trim() && !disabled
              ? 'linear-gradient(135deg, #B8960C, #D4AF37)'
              : 'rgba(212,175,55,0.08)',
            cursor: query.trim() && !disabled ? 'pointer' : 'not-allowed',
            color: query.trim() && !disabled ? '#0B0B0B' : '#3A3A40',
            display: 'flex',
            alignItems: 'center',
            flexShrink: 0,
            transition: 'all 0.2s ease',
            boxShadow: query.trim() && !disabled ? '0 4px 12px rgba(212,175,55,0.25)' : 'none',
          }}
        >
          <Send size={14} />
        </button>
      </div>
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.6}}`}</style>
    </div>
  );
};

export default QueryInput;