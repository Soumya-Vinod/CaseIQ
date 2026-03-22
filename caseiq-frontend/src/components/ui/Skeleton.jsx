const Skeleton = ({ className = '' }) => (
  <div className={`animate-pulse bg-slate-200 rounded-xl ${className}`} />
);

export const SkeletonCard = () => (
  <div className="bg-white rounded-2xl p-6 shadow border border-[#D5DCF9] space-y-3">
    <Skeleton className="h-4 w-1/3" />
    <Skeleton className="h-3 w-full" />
    <Skeleton className="h-3 w-4/5" />
    <Skeleton className="h-3 w-2/3" />
  </div>
);

export const SkeletonList = ({ count = 5 }) => (
  <div className="space-y-4">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="bg-white rounded-2xl p-5 shadow border border-[#D5DCF9] space-y-3">
        <div className="flex gap-3">
          <Skeleton className="h-6 w-16" />
          <Skeleton className="h-6 w-24" />
        </div>
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    ))}
  </div>
);

export default Skeleton;