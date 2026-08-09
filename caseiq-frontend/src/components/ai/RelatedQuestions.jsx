import { motion } from 'framer-motion';
import { ArrowRight, MessageCircleQuestion } from 'lucide-react';

const RelatedQuestions = ({ questions = [], onSelect, disabled }) => {
  if (!questions || questions.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <MessageCircleQuestion size={12} style={{ color: '#9A7D3A' }} />
        <p style={{
          fontSize: '0.66rem',
          fontWeight: 600,
          color: '#9A7D3A',
          letterSpacing: '2px',
          textTransform: 'uppercase',
        }}>
          Follow-up Questions
        </p>
      </div>
      {questions.map((q, i) => (
        <motion.button
          key={i}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 + i * 0.08 }}
          onClick={() => !disabled && onSelect(q)}
          disabled={disabled}
          style={{
            textAlign: 'left',
            fontSize: '0.8rem',
            padding: '10px 14px',
            borderRadius: '10px',
            border: '1px solid rgba(212,175,55,0.12)',
            background: 'rgba(14,12,6,0.8)',
            color: '#8A8A92',
            cursor: disabled ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            transition: 'all 0.2s ease',
            fontFamily: "'DM Sans', sans-serif",
          }}
          onMouseEnter={(e) => {
            if (!disabled) {
              e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
              e.currentTarget.style.color = '#C9A84C';
              e.currentTarget.style.background = 'rgba(212,175,55,0.05)';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'rgba(212,175,55,0.12)';
            e.currentTarget.style.color = '#8A8A92';
            e.currentTarget.style.background = 'rgba(14,12,6,0.8)';
          }}
        >
          <span>{q}</span>
          <ArrowRight size={12} style={{ flexShrink: 0, opacity: 0.5 }} />
        </motion.button>
      ))}
    </motion.div>
  );
};

export default RelatedQuestions;