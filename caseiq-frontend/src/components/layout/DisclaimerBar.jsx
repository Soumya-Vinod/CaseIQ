const DisclaimerBar = () => {
  return (
    <div style={{
      background: 'rgba(212,175,55,0.07)',
      borderTop: '1px solid rgba(212,175,55,0.18)',
      color: '#C5A46D',
      fontSize: '12px',
      textAlign: 'center',
      padding: '8px 24px',
      fontFamily: 'system-ui, sans-serif',
      letterSpacing: '0.2px',
      backdropFilter: 'blur(12px)',
    }}>
      ⚖️ &nbsp;CaseIQ provides verified legal knowledge only. It does not offer legal advice.
    </div>
  );
};

export default DisclaimerBar;
