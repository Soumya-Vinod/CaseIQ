import { motion } from 'framer-motion';
import { Clock, Check, ArrowRight } from 'lucide-react';

const LegalTimeline = ({ data, loading }) => {
  if (loading) {
    return (
      <div style={{ background: 'rgba(14,12,6,0.96)', border: '1px solid rgba(212,175,55,0.2)', borderRadius: '20px', padding: '28px' }}>
        <p style={{ color: '#C9A84C', fontFamily: "'Cormorant Garamond', serif", fontSize: '1.1rem', fontStyle: 'italic' }}>Building Timeline...</p>
      </div>
    );
  }
  if (!data || data.length === 0) return null;

  return (
    <div style={{ background: 'rgba(14,12,6,0.96)', border: '1px solid rgba(212,175,55,0.2)', borderRadius: '20px', padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <Clock size={18} style={{ color: '#D4AF37' }} />
        <h3 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: '1.2rem', fontWeight: 700, fontStyle: 'italic', color: '#D4AF37' }}>Legal Timeline</h3>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {data.map((event, i) => {
          const isCurrent = event.status === 'current';
          const isCompleted = event.status === 'completed';
          return (
            <div key={i} style={{ position: 'relative', display: 'flex', gap: '14px' }}>
              {i < data.length - 1 && (
                <div style={{ position: 'absolute', left: '17px', top: '36px', width: '2px', height: 'calc(100% - 8px)', background: isCompleted ? 'rgba(212,175,55,0.3)' : 'rgba(255,255,255,0.04)' }} />
              )}
              <div style={{ flexShrink: 0, zIndex: 1 }}>
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.08 }}
                  style={{
                    width: '36px', height: '36px', borderRadius: '50%',
                    border: `2px solid ${isCurrent ? '#D4AF37' : isCompleted ? 'rgba(212,175,55,0.4)' : 'rgba(255,255,255,0.08)'}`,
                    background: isCurrent ? 'rgba(212,175,55,0.15)' : 'rgba(255,255,255,0.02)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                  {isCompleted ? <Check size={14} style={{ color: '#9A7D3A' }} />
                    : isCurrent ? <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#D4AF37' }} />
                    : <ArrowRight size={12} style={{ color: '#3A3A40' }} />}
                </motion.div>
              </div>
              <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                style={{
                  flex: 1, background: isCurrent ? 'rgba(212,175,55,0.06)' : 'rgba(255,255,255,0.015)',
                  border: `1px solid ${isCurrent ? 'rgba(212,175,55,0.2)' : 'rgba(255,255,255,0.04)'}`,
                  borderRadius: '12px', padding: '12px 16px', marginBottom: '8px',
                }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
                  <div>
                    <span style={{ fontSize: '0.6rem', color: '#3A3A40', fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', display: 'block', marginBottom: '2px' }}>{event.phase}</span>
                    <h4 style={{ fontSize: '0.86rem', fontWeight: 600, color: isCurrent ? '#D4AF37' : '#B8B8B0' }}>{event.event}</h4>
                  </div>
                  <span style={{ fontSize: '0.66rem', color: isCurrent ? '#C9A84C' : '#3A3A40', flexShrink: 0, padding: '2px 8px', borderRadius: '10px', background: isCurrent ? 'rgba(212,175,55,0.1)' : 'transparent' }}>{event.time_frame}</span>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#6B6B75', lineHeight: 1.6 }}>{event.description}</p>
                {event.law_reference && (
                  <span style={{ display: 'inline-block', marginTop: '6px', fontSize: '0.66rem', color: '#9A7D3A', background: 'rgba(212,175,55,0.06)', border: '1px solid rgba(212,175,55,0.15)', padding: '2px 8px', borderRadius: '10px' }}>
                    📚 {event.law_reference}
                  </span>
                )}
              </motion.div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LegalTimeline;