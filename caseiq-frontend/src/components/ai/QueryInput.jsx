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
    if (listening) {
      stopListening();
    } else {
      startListening(langMap[language] || 'en');
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={listening ? '🎤 Listening... speak now' : 'Type your legal question... (Enter to send, Shift+Enter for new line)'}
            rows={2}
            className={`w-full rounded-xl px-4 py-3 pr-12 border focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] transition resize-none text-sm disabled:opacity-50 ${
              listening
                ? 'border-red-400 bg-red-50 text-red-700'
                : 'border-[#A7B0CA] bg-white text-[#443627]'
            }`}
          />
          {listening && (
            <div className="absolute right-3 top-3 flex gap-1">
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          {supported && (
            <button
              onClick={toggleVoice}
              disabled={disabled}
              title={listening ? 'Stop listening' : `Speak in ${language}`}
              className={`p-3 rounded-xl transition disabled:opacity-50 ${
                listening
                  ? 'bg-red-500 text-white hover:bg-red-600 shadow-lg'
                  : 'bg-white border border-[#A7B0CA] text-[#443627] hover:bg-[#D5DCF9]'
              }`}
            >
              {listening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
          )}

          <button
            onClick={handleSubmit}
            disabled={disabled || !query.trim()}
            className="p-3 rounded-xl bg-[#443627] text-white hover:bg-[#725E54] transition disabled:opacity-40 shadow-md"
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      <div className="flex justify-between items-center px-1">
        <p className="text-xs text-slate-400">
          {supported
            ? `🎤 Voice input available in ${language}`
            : 'Voice input not supported in this browser'}
        </p>
        <p className="text-xs text-slate-400">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
};

export default QueryInput;