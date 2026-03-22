import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { legalAPI } from '../services/api';
import { SkeletonList } from '../components/ui/Skeleton';
import { Search, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

const ACTS = [
  { value: '', label: 'All Acts' },
  { value: 'BNS', label: 'BNS 2023' },
  { value: 'BNSS', label: 'BNSS 2023' },
  { value: 'BSA', label: 'BSA 2023' },
  { value: 'IPC', label: 'IPC 1860' },
  { value: 'CrPC', label: 'CrPC 1973' },
];

const ACT_COLORS = {
  BNS: 'bg-[#D5DCF9] text-[#443627]',
  BNSS: 'bg-[#8EDCE6] text-[#443627]',
  BSA: 'bg-[#A7B0CA] text-white',
  IPC: 'bg-[#725E54] text-white',
  CrPC: 'bg-[#443627] text-white',
};

const LawExplorerPage = () => {
  const [search, setSearch] = useState('');
  const [selectedAct, setSelectedAct] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['law-sections', selectedAct, search, page],
    queryFn: () => legalAPI.getSections({
      act: selectedAct || undefined,
      search: search || undefined,
      page,
      page_size: 20,
    }),
    select: (res) => res.data,
    keepPreviousData: true,
  });

  const sections = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / 20);

  const handleSearch = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const handleActChange = (act) => {
    setSelectedAct(act);
    setPage(1);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">

      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <BookOpen className="text-[#443627]" size={28} />
          <h1 className="text-4xl font-bold text-[#443627]">Law Explorer</h1>
        </div>
        <p className="text-[#725E54]">
          Browse all {totalCount > 0 ? totalCount.toLocaleString() : '1,641'} sections from BNS, BNSS, BSA, IPC and CrPC.
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl p-5 shadow border border-[#D5DCF9] space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Search sections by title, number, or keyword..."
              value={search}
              onChange={handleSearch}
              className="w-full pl-9 pr-4 py-3 rounded-xl border border-[#A7B0CA] focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] bg-[#F8FAFC]"
            />
          </div>
        </div>

        {/* Act Filter Pills */}
        <div className="flex flex-wrap gap-2">
          {ACTS.map((act) => (
            <button
              key={act.value}
              onClick={() => handleActChange(act.value)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                selectedAct === act.value
                  ? 'bg-[#443627] text-white shadow-md'
                  : 'bg-slate-100 text-slate-600 hover:bg-[#D5DCF9] hover:text-[#443627]'
              }`}
            >
              {act.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      {!isLoading && (
        <p className="text-sm text-[#725E54]">
          Showing {sections.length} of {totalCount} sections
          {search && ` matching "${search}"`}
          {selectedAct && ` in ${selectedAct}`}
        </p>
      )}

      {/* Sections List */}
      {isLoading ? (
        <SkeletonList count={8} />
      ) : sections.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center border border-[#D5DCF9] shadow">
          <p className="text-4xl mb-3">🔍</p>
          <p className="text-[#443627] font-semibold">No sections found</p>
          <p className="text-[#725E54] text-sm mt-1">Try a different search term or act filter.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sections.map((section) => (
            <SectionCard
              key={section.id}
              section={section}
              expanded={expandedId === section.id}
              onToggle={() => setExpandedId(expandedId === section.id ? null : section.id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-3 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-xl bg-white border border-[#D5DCF9] text-[#443627] disabled:opacity-40 hover:bg-[#D5DCF9] transition"
          >
            ← Previous
          </button>
          <span className="px-4 py-2 rounded-xl bg-[#443627] text-white text-sm">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 rounded-xl bg-white border border-[#D5DCF9] text-[#443627] disabled:opacity-40 hover:bg-[#D5DCF9] transition"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

const SectionCard = ({ section, expanded, onToggle }) => (
  <div className="bg-white rounded-2xl shadow border border-[#D5DCF9] overflow-hidden hover:shadow-md transition">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-5 text-left"
    >
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <span className={`text-xs font-bold px-2 py-1 rounded-lg shrink-0 ${ACT_COLORS[section.act] || 'bg-slate-100 text-slate-600'}`}>
          {section.act}
        </span>
        <span className="font-semibold text-[#443627] shrink-0">§ {section.section_number}</span>
        <span className="text-[#725E54] text-sm truncate">{section.section_title}</span>
      </div>
      {expanded
        ? <ChevronUp size={16} className="text-[#725E54] shrink-0" />
        : <ChevronDown size={16} className="text-[#725E54] shrink-0" />
      }
    </button>

    {expanded && (
      <div className="px-5 pb-5 border-t border-[#D5DCF9] pt-4 space-y-3">
        <p className="text-sm text-[#443627] leading-relaxed whitespace-pre-wrap">
          {section.section_text}
        </p>
        {section.keywords?.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {section.keywords.map((kw, i) => (
              <span key={i} className="text-xs bg-[#D5DCF9] text-[#443627] px-2 py-1 rounded-full">
                {kw}
              </span>
            ))}
          </div>
        )}
        {section.category && (
          <p className="text-xs text-[#725E54]">Category: {section.category}</p>
        )}
      </div>
    )}
  </div>
);

export default LawExplorerPage;