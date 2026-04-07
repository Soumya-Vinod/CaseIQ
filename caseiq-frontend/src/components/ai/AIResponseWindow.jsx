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
      className="p-1.5 rounded-lg hover:bg-slate-100 transition text-slate-400 hover:text-slate-600"
      title="Copy response"
    >
      {copied
        ? <Check size={13} className="text-green-500" />
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
    <div className={`h-[560px] overflow-y-auto rounded-2xl p-5 transition-colors duration-300 border ${
      darkMode
        ? 'bg-slate-800/80 border-slate-700'
        : 'bg-white/90 border-slate-200'
    }`}>

      {/* Empty State */}
      {messages.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center shadow-lg text-2xl">
            ⚖️
          </div>
          <h3 className={`text-lg font-semibold ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
            CaseIQ Legal Assistant
          </h3>
          <p className={`text-sm max-w-sm leading-relaxed ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Ask any question about Indian criminal law, your rights, FIR filing, or BNS/BNSS sections. I will explain clearly with exact laws and steps.
          </p>
        </div>
      )}

      <div className="space-y-6">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {/* AI Avatar */}
            {msg.sender === 'ai' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center text-sm shrink-0 mt-1 shadow-md">
                ⚖
              </div>
            )}

            <div className={`max-w-[85%] flex flex-col gap-1 ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            }`}>
              <div className={`rounded-2xl px-4 py-3.5 text-sm shadow-sm ${
                msg.sender === 'user'
                  ? 'bg-[#443627] text-white rounded-tr-sm'
                  : darkMode
                  ? 'bg-slate-700/80 text-slate-200 rounded-tl-sm border border-slate-600/50'
                  : 'bg-[#F8FAFC] text-slate-800 rounded-tl-sm border border-[#D5DCF9]'
              }`}>

                {msg.sender === 'user' ? (
                  <p className="leading-relaxed">{msg.text}</p>
                ) : (
                  <div className={`prose prose-sm max-w-none ${darkMode ? 'prose-invert' : ''}`}>
                    <ReactMarkdown
                      components={{
                        h1: ({ children }) => (
                          <h1 className={`text-sm font-bold mt-4 mb-2 first:mt-0 ${
                            darkMode ? 'text-slate-100' : 'text-[#443627]'
                          }`}>
                            {children}
                          </h1>
                        ),
                        h2: ({ children }) => (
                          <h2 className={`text-sm font-bold mt-4 mb-2 first:mt-0 ${
                            darkMode ? 'text-slate-100' : 'text-[#443627]'
                          }`}>
                            {children}
                          </h2>
                        ),
                        h3: ({ children }) => (
                          <h3 className={`text-sm font-semibold mt-3 mb-1 ${
                            darkMode ? 'text-slate-200' : 'text-[#443627]'
                          }`}>
                            {children}
                          </h3>
                        ),
                        p: ({ children }) => (
                          <p className="mb-2 last:mb-0 leading-relaxed text-sm">
                            {children}
                          </p>
                        ),
                        ul: ({ children }) => (
                          <ul className="space-y-2 my-2">{children}</ul>
                        ),
                        ol: ({ children }) => (
                          <ol className="space-y-2 my-2 pl-2 list-none">{children}</ol>
                        ),
                        li: ({ children }) => (
                          <li className="flex items-start gap-2 text-sm leading-relaxed list-none">
                            <span className="text-[#8EDCE6] shrink-0 mt-0.5 font-bold text-base leading-none">
                              •
                            </span>
                            <span className="flex-1">{children}</span>
                          </li>
                        ),
                        strong: ({ children }) => (
                          <strong className={`font-semibold ${
                            darkMode ? 'text-[#8EDCE6]' : 'text-[#443627]'
                          }`}>
                            {children}
                          </strong>
                        ),
                        em: ({ children }) => (
                          <em className="not-italic text-xs text-slate-400 italic">
                            {children}
                          </em>
                        ),
                        hr: () => (
                          <div className={`my-3 border-t ${
                            darkMode ? 'border-slate-600/50' : 'border-[#D5DCF9]'
                          }`} />
                        ),
                        code: ({ children }) => (
                          <code className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                            darkMode
                              ? 'bg-slate-600 text-[#8EDCE6]'
                              : 'bg-[#D5DCF9]/60 text-[#443627]'
                          }`}>
                            {children}
                          </code>
                        ),
                        blockquote: ({ children }) => (
                          <blockquote className={`border-l-4 border-[#8EDCE6] pl-3 my-2 text-xs ${
                            darkMode ? 'text-slate-400' : 'text-slate-500'
                          }`}>
                            {children}
                          </blockquote>
                        ),
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  </div>
                )}

                {/* Confidence Score */}
                {msg.confidence && msg.sender === 'ai' && (
                  <div className={`mt-3 pt-3 border-t ${
                    darkMode ? 'border-slate-600' : 'border-[#D5DCF9]'
                  }`}>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">Confidence</span>
                      <div className={`flex-1 rounded-full h-1.5 ${
                        darkMode ? 'bg-slate-600' : 'bg-slate-200'
                      }`}>
                        <div
                          className="bg-gradient-to-r from-[#8EDCE6] to-[#443627] h-1.5 rounded-full transition-all duration-700"
                          style={{ width: `${Math.round(msg.confidence * 100)}%` }}
                        />
                      </div>
                      <span className={`text-xs font-semibold ${
                        darkMode ? 'text-slate-300' : 'text-[#443627]'
                      }`}>
                        {Math.round(msg.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions row for AI messages */}
              {msg.sender === 'ai' && (
                <div className="flex items-center gap-1 px-1">
                  <CopyButton text={msg.text} />
                  <span className="text-xs text-slate-400">
                    {new Date().toLocaleTimeString('en-IN', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              )}
            </div>

            {/* User Avatar */}
            {msg.sender === 'user' && (
              <div className="w-8 h-8 rounded-full bg-[#443627] flex items-center justify-center text-xs font-bold text-white shrink-0 mt-1 shadow-md">
                {userInitial}
              </div>
            )}
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center text-sm shrink-0 shadow-md">
              ⚖
            </div>
            <div className={`rounded-2xl rounded-tl-sm px-5 py-4 border shadow-sm ${
              darkMode
                ? 'bg-slate-700/80 border-slate-600/50'
                : 'bg-[#F8FAFC] border-[#D5DCF9]'
            }`}>
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 bg-[#8EDCE6] rounded-full animate-bounce"
                  style={{ animationDelay: '0ms' }}
                />
                <div
                  className="w-2 h-2 bg-[#A7B0CA] rounded-full animate-bounce"
                  style={{ animationDelay: '150ms' }}
                />
                <div
                  className="w-2 h-2 bg-[#D5DCF9] rounded-full animate-bounce"
                  style={{ animationDelay: '300ms' }}
                />
                <span className="text-xs text-slate-400 ml-1">
                  Analysing your query...
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
