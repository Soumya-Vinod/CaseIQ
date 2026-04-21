import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { awarenessAPI } from '../services/api';
import { SkeletonCard } from '../components/ui/Skeleton';
import { ExternalLink, Tag, TrendingUp, Search } from 'lucide-react';

const NewsPage = () => {
  const [search, setSearch] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['legal-news'],
    queryFn: () => awarenessAPI.getNews({ page_size: 20 }),
    select: (res) => res.data.results || [],
  });

  const filtered = (data || []).filter((item) =>
    item.title.toLowerCase().includes(search.toLowerCase()) ||
    item.summary.toLowerCase().includes(search.toLowerCase())
  );

  const featured = filtered.filter((item) => item.is_featured);
  const regular = filtered.filter((item) => !item.is_featured);

  return (
   <div style={{ background: '#0B0B0B', minHeight: '100vh' }} className="max-w-6xl mx-auto space-y-10 pb-16">

      {/* Header */}
      <div className="space-y-5">
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px', height: '42px', borderRadius: '12px',
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(212,175,55,0.35)', flexShrink: 0,
          }}>
            <TrendingUp size={20} color="#0B0B0B" />
          </div>
          <h1 style={{
            fontSize: '34px', fontWeight: '800',
            fontFamily: "'Georgia', 'Times New Roman', serif",
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.5px',
          }}>Legal News</h1>
        </div>
        <p style={{ color: '#A1A1AA', fontFamily: 'system-ui, sans-serif', fontSize: '15px' }}>
          Stay updated with the latest Indian legal developments, court judgments, and law changes.
        </p>

        {/* Search */}
        <div style={{ position: 'relative', maxWidth: '480px' }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#A1A1AA' }} />
          <input
            type="text"
            placeholder="Search legal news..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              paddingLeft: '42px',
              paddingRight: '16px',
              paddingTop: '13px',
              paddingBottom: '13px',
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
            onFocus={e => { e.target.style.borderColor = '#D4AF37'; e.target.style.boxShadow = '0 0 0 3px rgba(212,175,55,0.15)'; }}
            onBlur={e => { e.target.style.borderColor = 'rgba(212,175,55,0.25)'; e.target.style.boxShadow = 'none'; }}
          />
        </div>
      </div>

      {isLoading && (
        <div className="grid md:grid-cols-2 gap-6">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <div style={{
          background: 'rgba(245,158,11,0.08)',
          border: '1px solid rgba(245,158,11,0.3)',
          borderRadius: '16px',
          padding: '28px',
          textAlign: 'center',
        }}>
          <p style={{ fontWeight: '600', color: '#FDE68A', fontFamily: 'system-ui, sans-serif' }}>Could not load news</p>
          <p style={{ fontSize: '13px', color: '#A1A1AA', marginTop: '6px', fontFamily: 'system-ui, sans-serif' }}>
            Make sure your NewsAPI key is configured in the backend.
          </p>
        </div>
      )}

      {!isLoading && !error && filtered.length === 0 && (
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(212,175,55,0.2)',
          borderRadius: '16px',
          padding: '56px',
          textAlign: 'center',
          backdropFilter: 'blur(12px)',
        }}>
          <p style={{ fontSize: '40px', marginBottom: '14px' }}>📰</p>
          <p style={{ color: '#E5E5E5', fontWeight: '600', fontFamily: 'system-ui, sans-serif' }}>No news articles found</p>
          <p style={{ color: '#A1A1AA', fontSize: '13px', marginTop: '6px', fontFamily: 'system-ui, sans-serif' }}>
            Ask your admin to fetch news using the backend API.
          </p>
        </div>
      )}

      {/* Featured */}
      {featured.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{
            fontSize: '18px', fontWeight: '700',
            color: '#E5E5E5',
            fontFamily: "'Georgia', 'Times New Roman', serif",
            display: 'flex', alignItems: 'center', gap: '10px',
          }}>
            <span style={{
              width: '8px', height: '8px', borderRadius: '50%',
              background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
              boxShadow: '0 0 8px rgba(212,175,55,0.6)',
              display: 'inline-block',
            }} />
            Featured
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {featured.map((item) => <NewsCard key={item.id} item={item} featured />)}
          </div>
        </div>
      )}

      {/* All News */}
      {regular.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{
            fontSize: '18px', fontWeight: '700',
            color: '#E5E5E5',
            fontFamily: "'Georgia', 'Times New Roman', serif",
          }}>All Articles</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {regular.map((item) => <NewsCard key={item.id} item={item} />)}
          </div>
        </div>
      )}
    </div>
  );
};

const NewsCard = ({ item, featured }) => (
  <div
    style={{
      borderRadius: '16px',
      padding: '24px',
      transition: 'all 0.25s ease',
      cursor: 'default',
      background: featured
        ? 'linear-gradient(135deg, rgba(212,175,55,0.1) 0%, rgba(197,164,109,0.07) 100%)'
        : 'rgba(255,255,255,0.03)',
      border: featured
        ? '1px solid rgba(212,175,55,0.4)'
        : '1px solid rgba(212,175,55,0.15)',
      backdropFilter: 'blur(12px)',
      boxShadow: featured ? '0 8px 30px rgba(212,175,55,0.1)' : '0 2px 16px rgba(0,0,0,0.3)',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.transform = 'translateY(-4px)';
      e.currentTarget.style.boxShadow = featured
        ? '0 16px 48px rgba(212,175,55,0.2)'
        : '0 12px 36px rgba(212,175,55,0.1)';
      e.currentTarget.style.borderColor = 'rgba(212,175,55,0.5)';
    }}
    onMouseLeave={e => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = featured ? '0 8px 30px rgba(212,175,55,0.1)' : '0 2px 16px rgba(0,0,0,0.3)';
      e.currentTarget.style.borderColor = featured ? 'rgba(212,175,55,0.4)' : 'rgba(212,175,55,0.15)';
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
      <span style={{
        fontSize: '11px',
        background: 'rgba(212,175,55,0.15)',
        color: '#D4AF37',
        padding: '4px 10px',
        borderRadius: '20px',
        fontWeight: '600',
        fontFamily: 'system-ui, sans-serif',
        border: '1px solid rgba(212,175,55,0.25)',
      }}>
        {item.source}
      </span>
      <span style={{ fontSize: '12px', color: '#71717A', fontFamily: 'system-ui, sans-serif' }}>
        {new Date(item.published_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
      </span>
    </div>

    <h3 style={{
      fontWeight: '700',
      color: '#E5E5E5',
      fontSize: '15px',
      marginBottom: '10px',
      lineHeight: '1.4',
      fontFamily: 'system-ui, sans-serif',
      display: '-webkit-box',
      WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical',
      overflow: 'hidden',
    }}>{item.title}</h3>
    <p style={{
      fontSize: '13px', color: '#A1A1AA', lineHeight: '1.6',
      fontFamily: 'system-ui, sans-serif',
      display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
    }}>{item.summary}</p>

    {item.tags?.length > 0 && (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '14px' }}>
        {item.tags.slice(0, 3).map((tag, i) => (
          <span key={i} style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            fontSize: '11px',
            background: 'rgba(255,255,255,0.05)',
            color: '#C5A46D',
            padding: '4px 10px',
            borderRadius: '20px',
            border: '1px solid rgba(197,164,109,0.2)',
            fontFamily: 'system-ui, sans-serif',
          }}>
            <Tag size={9} /> {tag}
          </span>
        ))}
      </div>
    )}

    <a href={item.source_url} target="_blank" rel="noopener noreferrer"
      style={{
        display: 'flex', alignItems: 'center', gap: '6px',
        fontSize: '12px', color: '#D4AF37', fontWeight: '600',
        marginTop: '16px', textDecoration: 'none',
        fontFamily: 'system-ui, sans-serif',
        transition: 'gap 0.2s',
      }}
      onMouseEnter={e => { e.currentTarget.style.textDecoration = 'underline'; }}
      onMouseLeave={e => { e.currentTarget.style.textDecoration = 'none'; }}
    >
      Read full article <ExternalLink size={12} />
    </a>
  </div>
);

export default NewsPage;
