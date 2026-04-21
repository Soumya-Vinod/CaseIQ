const shimmerStyle = {
  background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(212,175,55,0.08) 50%, rgba(255,255,255,0.04) 100%)',
  backgroundSize: '200% 100%',
  animation: 'goldShimmer 1.6s ease-in-out infinite',
  borderRadius: '6px',
};

if (typeof document !== 'undefined' && !document.getElementById('skeleton-keyframes')) {
  const style = document.createElement('style');
  style.id = 'skeleton-keyframes';
  style.textContent = `
    @keyframes goldShimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `;
  document.head.appendChild(style);
}

export const SkeletonLine = ({ width = '100%', height = '14px' }) => (
  <div style={{ ...shimmerStyle, width, height }} />
);

export const SkeletonCard = () => (
  <div style={{
    background: 'rgba(255,255,255,0.025)',
    border: '1px solid rgba(212,175,55,0.1)',
    borderRadius: '14px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  }}>
    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
      <div style={{ ...shimmerStyle, width: '60px', height: '22px', borderRadius: '8px' }} />
      <div style={{ ...shimmerStyle, width: '110px', height: '22px', borderRadius: '8px' }} />
    </div>
    <div style={{ ...shimmerStyle, width: '100%', height: '13px' }} />
    <div style={{ ...shimmerStyle, width: '72%', height: '13px' }} />
  </div>
);

export const SkeletonList = ({ count = 6 }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
    {Array.from({ length: count }).map((_, i) => (
      <SkeletonCard key={i} />
    ))}
  </div>
);

export default SkeletonCard;
