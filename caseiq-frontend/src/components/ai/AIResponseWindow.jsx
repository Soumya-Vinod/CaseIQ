import { useEffect, useRef } from 'react';
import { useSettings } from '../../context/SettingsContext';
import ReactMarkdown from 'react-markdown';

const AIResponseWindow = ({ messages = [], loading }) => {
  const { darkMode } = useSettings();
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div className={`h-[520px] overflow-y-auto rounded-2xl p-6 transition-colors duration-300 border ${
      darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white/80 border-slate-200'
    }`}>

      {/* Empty State */}
      {messages.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
          <div className="text-5xl">⚖️</div>
          <h3 className="text-lg font-semibold text-slate-600">Welcome to CaseIQ AI Assistant</h3>
          <p className="text-sm text-slate-400 max-w-md">
            Ask any legal question related to FIR filing, BNS sections, rights after arrest, or criminal law procedures.
          </p>
        </div>
      )}

      <div className="space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>

            {/* AI Avatar */}
            {msg.sender === 'ai' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center text-xs font-bold text-[#443627] shrink-0 mt-1 mr-2 shadow">
                ⚖
              </div>
            )}

            <div className={`max-w-[80%] rounded-2xl px-5 py-4 text-sm shadow-sm ${
              msg.sender === 'user'
                ? 'bg-[#443627] text-white rounded-tr-sm'
                : darkMode
                ? 'bg-slate-700 text-slate-200 rounded-tl-sm'
                : 'bg-[#F8FAFC] border border-[#D5DCF9] text-slate-800 rounded-tl-sm'
            }`}>

              {msg.sender === 'user' ? (
                <p className="leading-relaxed">{msg.text}</p>
              ) : (
                <div className={`prose prose-sm max-w-none ${darkMode ? 'prose-invert' : ''}`}
                  style={{
                    '--tw-prose-body': darkMode ? '#e2e8f0' : '#374151',
                    '--tw-prose-headings': darkMode ? '#f1f5f9' : '#443627',
                    '--tw-prose-bullets': '#8EDCE6',
                  }}>
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => <h1 className="text-base font-bold text-[#443627] dark:text-slate-100 mt-3 mb-1 first:mt-0">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-sm font-bold text-[#443627] dark:text-slate-100 mt-3 mb-1 first:mt-0">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-sm font-semibold text-[#443627] dark:text-slate-200 mt-2 mb-1">{children}</h3>,
                      p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                      ul: ({ children }) => <ul className="space-y-1 my-2 pl-1">{children}</ul>,
                      ol: ({ children }) => <ol className="space-y-1 my-2 pl-4 list-decimal">{children}</ol>,
                      li: ({ children }) => (
                        <li className="flex items-start gap-2 text-sm leading-relaxed">
                          <span className="text-[#8EDCE6] mt-0.5 shrink-0">•</span>
                          <span>{children}</span>
                        </li>
                      ),
                      strong: ({ children }) => <strong className="font-semibold text-[#443627] dark:text-slate-100">{children}</strong>,
                      hr: () => <hr className="my-3 border-[#D5DCF9]" />,
                      code: ({ children }) => <code className="bg-[#D5DCF9]/50 px-1.5 py-0.5 rounded text-xs font-mono text-[#443627]">{children}</code>,
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              )}

              {/* Confidence Score */}
              {msg.confidence && msg.sender === 'ai' && (
                <div className="mt-3 pt-3 border-t border-[#D5DCF9]">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Confidence</span>
                    <div className="flex-1 bg-slate-200 rounded-full h-1.5">
                      <div
                        className="bg-gradient-to-r from-[#8EDCE6] to-[#443627] h-1.5 rounded-full transition-all"
                        style={{ width: `${Math.round(msg.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-[#443627]">
                      {Math.round(msg.confidence * 100)}%
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* User Avatar */}
            {msg.sender === 'user' && (
              <div className="w-8 h-8 rounded-full bg-[#443627] flex items-center justify-center text-xs font-bold text-white shrink-0 mt-1 ml-2 shadow">
                U
              </div>
            )}
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="flex justify-start items-end gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center text-xs font-bold text-[#443627] shrink-0 shadow">
              ⚖
            </div>
            <div className={`px-5 py-4 rounded-2xl rounded-tl-sm border ${
              darkMode ? 'bg-slate-700 border-slate-600' : 'bg-[#F8FAFC] border-[#D5DCF9]'
            }`}>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-[#8EDCE6] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-[#A7B0CA] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-[#D5DCF9] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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