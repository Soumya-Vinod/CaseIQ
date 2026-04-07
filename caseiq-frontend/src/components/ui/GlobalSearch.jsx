import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, BookOpen, Newspaper, GraduationCap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { legalAPI, awarenessAPI, knowledgeAPI } from '../../services/api';

const GlobalSearch = () => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ laws: [], news: [], education: [] });
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Keyboard shortcut — press / to open
  useEffect(() => {
    const handler = (e) => {
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults({ laws: [], news: [], education: [] });
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const [lawsRes, newsRes, eduRes] = await Promise.allSettled([
          legalAPI.getSections({ search: query, page_size: 3 }),
          awarenessAPI.getNews({ search: query, page_size: 3 }),
          awarenessAPI.getEducation({ search: query, page_size: 3 }),
        ]);

        setResults({
          laws: lawsRes.status === 'fulfilled' ? lawsRes.value.data.results || [] : [],
          news: newsRes.status === 'fulfilled' ? newsRes.value.data.results || [] : [],
          education: eduRes.status === 'fulfilled' ? eduRes.value.data.results || [] : [],
        });
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [query]);

  const hasResults = results.laws.length + results.news.length + results.education.length > 0;

  const handleLawClick = (section) => {
    navigate(`/laws?search=${encodeURIComponent(section.section_title || '')}`);
    setOpen(false);
    setQuery('');
  };

  const handleAskAI = () => {
    if (!query.trim()) return;
    localStorage.setItem('caseiq_pending_query', query);
    navigate('/chat');
    setOpen(false);
    setQuery('');
  };

  return (
    <>
      {/* Search Trigger Button */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl border border-[#A7B0CA]/40 text-slate-500 hover:border-[#8EDCE6] hover:text-[#443627] transition text-sm bg-white/50 backdrop-blur-sm"
      >
        <Search size={14} />
        <span className="hidden sm:block text-xs">Search laws, news...</span>
        <kbd className="hidden sm:block text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono">/</kbd>
      </button>

      {/* Modal */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
            />

            {/* Search Panel */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              transition={{ duration: 0.2 }}
              className="fixed top-20 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 px-4"
            >
              <div className="bg-white rounded-2xl shadow-2xl border border-[#D5DCF9] overflow-hidden">

                {/* Input */}
                <div className="flex items-center gap-3 p-4 border-b border-[#D5DCF9]">
                  <Search size={18} className="text-[#725E54] shrink-0" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAskAI()}
                    placeholder="Search laws, news, rights... or press Enter to ask AI"
                    className="flex-1 outline-none text-[#443627] placeholder-slate-400 text-sm"
                  />
                  {query && (
                    <button onClick={() => setQuery('')}>
                      <X size={16} className="text-slate-400 hover:text-slate-600" />
                    </button>
                  )}
                  <kbd className="text-xs bg-slate-100 px-2 py-1 rounded font-mono text-slate-400">Esc</kbd>
                </div>

                {/* Results */}
                <div className="max-h-96 overflow-y-auto">

                  {loading && (
                    <div className="p-6 text-center text-sm text-slate-400">Searching...</div>
                  )}

                  {!loading && query.length >= 2 && !hasResults && (
                    <div className="p-6 text-center space-y-3">
                      <p className="text-sm text-slate-400">No results found for "{query}"</p>
                      <button
                        onClick={handleAskAI}
                        className="bg-[#443627] text-white px-5 py-2 rounded-xl text-sm hover:bg-[#725E54] transition"
                      >
                        Ask AI about "{query}" →
                      </button>
                    </div>
                  )}

                  {!loading && hasResults && (
                    <div className="divide-y divide-[#F0F2F8]">

                      {/* Laws */}
                      {results.laws.length > 0 && (
                        <div className="p-3">
                          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 mb-2 flex items-center gap-1">
                            <BookOpen size={10} /> Legal Sections
                          </p>
                          {results.laws.map((law) => (
                            <button
                              key={law.id}
                              onClick={() => handleLawClick(law)}
                              className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#D5DCF9]/40 transition"
                            >
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold bg-[#D5DCF9] text-[#443627] px-2 py-0.5 rounded-lg">{law.act}</span>
                                <span className="text-xs text-[#725E54]">§{law.section_number}</span>
                                <span className="text-sm text-[#443627] truncate">{law.section_title}</span>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}

                      {/* News */}
                      {results.news.length > 0 && (
                        <div className="p-3">
                          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 mb-2 flex items-center gap-1">
                            <Newspaper size={10} /> Legal News
                          </p>
                          {results.news.map((item) => (
                            <button
                              key={item.id}
                              onClick={() => { navigate('/news'); setOpen(false); setQuery(''); }}
                              className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#D5DCF9]/40 transition"
                            >
                              <p className="text-sm text-[#443627] truncate">{item.title}</p>
                              <p className="text-xs text-slate-400">{item.source}</p>
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Education */}
                      {results.education.length > 0 && (
                        <div className="p-3">
                          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 mb-2 flex items-center gap-1">
                            <GraduationCap size={10} /> Education
                          </p>
                          {results.education.map((item) => (
                            <button
                              key={item.id}
                              onClick={() => { navigate('/education'); setOpen(false); setQuery(''); }}
                              className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#D5DCF9]/40 transition"
                            >
                              <p className="text-sm text-[#443627] truncate">{item.title}</p>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Quick Actions */}
                  {!query && (
                    <div className="p-4 space-y-2">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Quick Actions</p>
                      {[
                        { label: '🚨 Rights when arrested', query: 'What are my rights when arrested by police?' },
                        { label: '📄 How to file FIR', query: 'How to file an FIR at police station?' },
                        { label: '💻 Report cybercrime', query: 'How to report cybercrime in India?' },
                        { label: '⚖️ Get bail', query: 'How to apply for bail in India?' },
                      ].map((item, i) => (
                        <button
                          key={i}
                          onClick={() => setQuery(item.query)}
                          className="w-full text-left px-3 py-2 rounded-xl hover:bg-[#D5DCF9]/40 transition text-sm text-[#443627]"
                        >
                          {item.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer */}
                {query && (
                  <div className="px-4 py-3 border-t border-[#D5DCF9] bg-[#F8FAFC]">
                    <button
                      onClick={handleAskAI}
                      className="w-full text-sm text-[#443627] font-medium hover:text-[#725E54] transition flex items-center justify-center gap-2"
                    >
                      Press Enter to ask AI about "{query.slice(0, 40)}{query.length > 40 ? '...' : ''}" →
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};

export default GlobalSearch;