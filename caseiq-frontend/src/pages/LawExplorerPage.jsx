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
  BNS:  'bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40',
  BNSS: 'bg-[#FFD700]/15 text-[#FFD700] border border-[#FFD700]/30',
  BSA:  'bg-[#C5A46D]/20 text-[#C5A46D] border border-[#C5A46D]/40',
  IPC:  'bg-[#D4AF37]/10 text-[#C5A46D] border border-[#C5A46D]/30',
  CrPC: 'bg-white/5 text-[#E5E5E5] border border-white/20',
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
    <div style={{ background: 'transparent' }} className="max-w-6xl mx-auto space-y-8 pb-16">

      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #D4AF37, #FFD700)', boxShadow: '0 0 20px rgba(212,175,55,0.35)' }}>
            <BookOpen size={20} color="#0B0B0B" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight"
            style={{ fontFamily: "'Georgia', 'Times New Roman', serif", background: 'linear-gradient(135deg, #D4AF37, #FFD700)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Law Explorer
          </h1>
        </div>
        <p style={{ color: '#A1A1AA', fontFamily: 'system-ui, sans-serif' }}>
          Browse all {totalCount > 0 ? totalCount.toLocaleString() : '1,641'} sections from BNS, BNSS, BSA, IPC and CrPC.
        </p>
      </div>

      {/* Filters */}
      <div style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(212,175,55,0.2)',
        borderRadius: '16px',
        padding: '20px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(212,175,55,0.1)'
      }} className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search style={{ color: '#A1A1AA', position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} size={16} />
            <input
              type="text"
              placeholder="Search sections by title, number, or keyword..."
              value={search}
              onChange={handleSearch}
              style={{
                width: '100%',
                paddingLeft: '40px',
                paddingRight: '16px',
                paddingTop: '12px',
                paddingBottom: '12px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(212,175,55,0.25)',
                borderRadius: '12px',
                color: '#E5E5E5',
                outline: 'none',
                fontFamily: 'system-ui, sans-serif',
                fontSize: '14px',
                transition: 'border-color 0.2s, box-shadow 0.2s',
                boxSizing: 'border-box',
              }}
              onFocus={e => {
                e.target.style.borderColor = '#D4AF37';
                e.target.style.boxShadow = '0 0 0 3px rgba(212,175,55,0.15), inset 0 1px 4px rgba(0,0,0,0.3)';
              }}
              onBlur={e => {
                e.target.style.borderColor = 'rgba(212,175,55,0.25)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>
        </div>

        {/* Act Filter Pills */}
        <div className="flex flex-wrap gap-2">
          {ACTS.map((act) => (
            <button
              key={act.value}
              onClick={() => handleActChange(act.value)}
              style={selectedAct === act.value ? {
                background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                color: '#0B0B0B',
                border: 'none',
                padding: '8px 18px',
                borderRadius: '10px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                boxShadow: '0 4px 15px rgba(212,175,55,0.4)',
                transition: 'all 0.2s ease',
                fontFamily: 'system-ui, sans-serif',
              } : {
                background: 'rgba(255,255,255,0.04)',
                color: '#A1A1AA',
                border: '1px solid rgba(212,175,55,0.2)',
                padding: '8px 18px',
                borderRadius: '10px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                fontFamily: 'system-ui, sans-serif',
              }}
              onMouseEnter={e => {
                if (selectedAct !== act.value) {
                  e.target.style.borderColor = 'rgba(212,175,55,0.5)';
                  e.target.style.color = '#D4AF37';
                  e.target.style.background = 'rgba(212,175,55,0.08)';
                }
              }}
              onMouseLeave={e => {
                if (selectedAct !== act.value) {
                  e.target.style.borderColor = 'rgba(212,175,55,0.2)';
                  e.target.style.color = '#A1A1AA';
                  e.target.style.background = 'rgba(255,255,255,0.04)';
                }
              }}
            >
              {act.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      {!isLoading && (
        <p style={{ color: '#A1A1AA', fontSize: '13px', fontFamily: 'system-ui, sans-serif' }}>
          Showing <span style={{ color: '#D4AF37' }}>{sections.length}</span> of <span style={{ color: '#D4AF37' }}>{totalCount}</span> sections
          {search && <span> matching "<span style={{ color: '#FFD700' }}>{search}</span>"</span>}
          {selectedAct && <span> in <span style={{ color: '#FFD700' }}>{selectedAct}</span></span>}
        </p>
      )}

      {/* Sections List */}
      {isLoading ? (
        <SkeletonList count={8} />
      ) : sections.length === 0 ? (
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(212,175,55,0.2)',
          borderRadius: '16px',
          padding: '48px',
          textAlign: 'center',
          backdropFilter: 'blur(12px)',
        }}>
          <p style={{ fontSize: '36px', marginBottom: '12px' }}>🔍</p>
          <p style={{ color: '#E5E5E5', fontWeight: '600', fontFamily: 'system-ui, sans-serif' }}>No sections found</p>
          <p style={{ color: '#A1A1AA', fontSize: '13px', marginTop: '6px', fontFamily: 'system-ui, sans-serif' }}>Try a different search term or act filter.</p>
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
            style={{
              padding: '10px 20px',
              borderRadius: '10px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(212,175,55,0.25)',
              color: '#D4AF37',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
              opacity: page === 1 ? 0.4 : 1,
              transition: 'all 0.2s',
              fontFamily: 'system-ui, sans-serif',
              fontSize: '14px',
            }}
          >
            ← Previous
          </button>
          <span style={{
            padding: '10px 20px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            color: '#0B0B0B',
            fontWeight: '600',
            fontSize: '14px',
            fontFamily: 'system-ui, sans-serif',
          }}>
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            style={{
              padding: '10px 20px',
              borderRadius: '10px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(212,175,55,0.25)',
              color: '#D4AF37',
              cursor: page === totalPages ? 'not-allowed' : 'pointer',
              opacity: page === totalPages ? 0.4 : 1,
              transition: 'all 0.2s',
              fontFamily: 'system-ui, sans-serif',
              fontSize: '14px',
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
};

const SectionCard = ({ section, expanded, onToggle }) => {
  const actColorClass = ACT_COLORS[section.act] || 'bg-white/5 text-[#E5E5E5] border border-white/20';

  return (
    <div style={{
      background: expanded ? 'rgba(212,175,55,0.06)' : 'rgba(255,255,255,0.03)',
      border: expanded ? '1px solid rgba(212,175,55,0.45)' : '1px solid rgba(212,175,55,0.15)',
      borderRadius: '14px',
      overflow: 'hidden',
      transition: 'all 0.25s ease',
      boxShadow: expanded ? '0 8px 30px rgba(212,175,55,0.12)' : '0 2px 12px rgba(0,0,0,0.3)',
    }}
      onMouseEnter={e => {
        if (!expanded) {
          e.currentTarget.style.border = '1px solid rgba(212,175,55,0.4)';
          e.currentTarget.style.boxShadow = '0 6px 24px rgba(212,175,55,0.1)';
          e.currentTarget.style.transform = 'translateY(-1px)';
        }
      }}
      onMouseLeave={e => {
        if (!expanded) {
          e.currentTarget.style.border = '1px solid rgba(212,175,55,0.15)';
          e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.3)';
          e.currentTarget.style.transform = 'translateY(0)';
        }
      }}
    >
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '18px 20px',
          textAlign: 'left',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
          <span className={`text-xs font-bold px-2 py-1 rounded-lg shrink-0 ${actColorClass}`}
            style={{ fontFamily: 'system-ui, sans-serif', fontSize: '11px' }}>
            {section.act}
          </span>
          <span style={{ color: '#D4AF37', fontWeight: '600', whiteSpace: 'nowrap', fontFamily: 'system-ui, sans-serif', fontSize: '14px' }}>
            § {section.section_number}
          </span>
          <span style={{ color: '#E5E5E5', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'system-ui, sans-serif' }}>
            {section.section_title}
          </span>
        </div>
        {expanded
          ? <ChevronUp size={16} style={{ color: '#D4AF37', flexShrink: 0 }} />
          : <ChevronDown size={16} style={{ color: '#A1A1AA', flexShrink: 0 }} />
        }
      </button>

      {expanded && (
        <div style={{
          padding: '0 20px 20px 20px',
          borderTop: '1px solid rgba(212,175,55,0.2)',
          paddingTop: '16px',
        }} className="space-y-3">
          <p style={{ color: '#E5E5E5', fontSize: '14px', lineHeight: '1.7', whiteSpace: 'pre-wrap', fontFamily: 'system-ui, sans-serif' }}>
            {section.section_text}
          </p>
          {section.keywords?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', paddingTop: '8px' }}>
              {section.keywords.map((kw, i) => (
                <span key={i} style={{
                  fontSize: '12px',
                  background: 'rgba(212,175,55,0.1)',
                  color: '#D4AF37',
                  padding: '4px 10px',
                  borderRadius: '20px',
                  border: '1px solid rgba(212,175,55,0.25)',
                  fontFamily: 'system-ui, sans-serif',
                }}>
                  {kw}
                </span>
              ))}
            </div>
          )}
          {section.category && (
            <p style={{ fontSize: '12px', color: '#A1A1AA', fontFamily: 'system-ui, sans-serif' }}>
              Category: <span style={{ color: '#C5A46D' }}>{section.category}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default LawExplorerPage;
