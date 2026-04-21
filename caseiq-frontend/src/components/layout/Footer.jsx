const Footer = () => {
  return (
    <footer style={{
      background: 'rgba(10,10,10,0.95)',
      borderTop: '1px solid rgba(212,175,55,0.12)',
      textAlign: 'center',
      padding: '14px 24px',
      fontFamily: 'system-ui, sans-serif',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Top shimmer line */}
      <div style={{
        position: 'absolute',
        top: 0, left: '20%', right: '20%',
        height: '1px',
        background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent)',
      }} />

      <p style={{ fontSize: '12px', color: '#52525B', letterSpacing: '0.3px' }}>
        © 2026{' '}
        <span style={{
          background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          fontWeight: '600',
        }}>
          CaseIQ
        </span>
        {' '}— AI-Powered Legal Knowledge System
      </p>
    </footer>
  );
};

export default Footer;
