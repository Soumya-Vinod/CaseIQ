import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { awarenessAPI } from '../services/api';
import { SkeletonCard } from '../components/ui/Skeleton';
import { ExternalLink, Tag, TrendingUp } from 'lucide-react';

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
    <div className="max-w-6xl mx-auto space-y-10 pb-16">

      {/* Header */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <TrendingUp className="text-[#443627]" size={28} />
          <h1 className="text-4xl font-bold text-[#443627]">Legal News</h1>
        </div>
        <p className="text-[#725E54]">
          Stay updated with the latest Indian legal developments, court judgments, and law changes.
        </p>

        {/* Search */}
        <input
          type="text"
          placeholder="Search legal news..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-lg rounded-xl border border-[#A7B0CA] p-3 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] bg-white"
        />
      </div>

      {isLoading && (
        <div className="grid md:grid-cols-2 gap-6">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl p-6 text-center">
          <p className="font-semibold">Could not load news</p>
          <p className="text-sm mt-1">Make sure your NewsAPI key is configured in the backend.</p>
        </div>
      )}

      {!isLoading && !error && filtered.length === 0 && (
        <div className="bg-white rounded-2xl p-10 text-center border border-[#D5DCF9] shadow">
          <p className="text-4xl mb-3">📰</p>
          <p className="text-[#443627] font-semibold">No news articles found</p>
          <p className="text-[#725E54] text-sm mt-1">
            Ask your admin to fetch news using the backend API.
          </p>
        </div>
      )}

      {/* Featured */}
      {featured.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-[#443627] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#8EDCE6] inline-block" />
            Featured
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {featured.map((item) => <NewsCard key={item.id} item={item} featured />)}
          </div>
        </div>
      )}

      {/* All News */}
      {regular.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-[#443627]">All Articles</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {regular.map((item) => <NewsCard key={item.id} item={item} />)}
          </div>
        </div>
      )}
    </div>
  );
};

const NewsCard = ({ item, featured }) => (
  <div className={`rounded-2xl p-6 shadow border transition hover:shadow-lg hover:-translate-y-1 duration-300 ${
    featured
      ? 'bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6] border-[#A7B0CA]'
      : 'bg-white border-[#D5DCF9]'
  }`}>
    <div className="flex justify-between items-start mb-3">
      <span className="text-xs bg-white/60 text-[#443627] px-2 py-1 rounded-full font-medium">
        {item.source}
      </span>
      <span className="text-xs text-[#725E54]">
        {new Date(item.published_at).toLocaleDateString('en-IN', {
          day: 'numeric', month: 'short', year: 'numeric'
        })}
      </span>
    </div>

    <h3 className="font-semibold text-[#443627] text-base mb-2 leading-snug">{item.title}</h3>
    <p className="text-sm text-[#725E54] line-clamp-3">{item.summary}</p>

    {item.tags?.length > 0 && (
      <div className="flex flex-wrap gap-2 mt-3">
        {item.tags.slice(0, 3).map((tag, i) => (
          <span key={i} className="flex items-center gap-1 text-xs bg-white/50 text-[#443627] px-2 py-1 rounded-full">
            <Tag size={10} /> {tag}
          </span>
        ))}
      </div>
    )}

    <a href={item.source_url} target="_blank" rel="noopener noreferrer"
      className="flex items-center gap-1 text-xs text-[#443627] font-medium mt-4 hover:underline">
      Read full article <ExternalLink size={12} />
    </a>
  </div>
);

export default NewsPage;