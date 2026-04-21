import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const NotFoundPage = () => {
  const navigate = useNavigate();
  return (
    <div style={{
      minHeight: '70vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '500px', height: '500px',
        background: 'radial-gradient(circle, rgba(212,175,55,0.07) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          textAlign: 'center',
          maxWidth: '420px',
          padding: '20px',
          position: 'relative',
        }}
      >
        {/* 404 */}
        <div style={{
          fontSize: '120px',
          fontWeight: '900',
          fontFamily: "'Georgia', 'Times New Roman', serif",
          background: 'linear-gradient(135deg, rgba(212,175,55,0.15), rgba(212,175,55,0.05))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          lineHeight: '1',
          letterSpacing: '-4px',
          marginBottom: '8px',
          textShadow: 'none',
          filter: 'drop-shadow(0 0 40px rgba(212,175,55,0.2))',
        }}>404</div>

        {/* Icon with glow */}
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          style={{ fontSize: '56px', marginBottom: '24px', display: 'block', filter: 'drop-shadow(0 4px 16px rgba(212,175,55,0.3))' }}
        >⚖️</motion.div>

        <h1 style={{
          fontSize: '26px',
          fontWeight: '800',
          fontFamily: "'Georgia', 'Times New Roman', serif",
          color: '#E5E5E5',
          marginBottom: '12px',
          letterSpacing: '-0.3px',
        }}>Page Not Found</h1>

        <p style={{
          color: '#A1A1AA',
          fontFamily: 'system-ui, sans-serif',
          fontSize: '15px',
          lineHeight: '1.6',
          marginBottom: '36px',
        }}>
          The page you are looking for does not exist or has been moved.
        </p>

        {/* Decorative divider */}
        <div style={{
          width: '60px', height: '1px',
          background: 'linear-gradient(90deg, transparent, #D4AF37, transparent)',
          margin: '0 auto 36px',
        }} />

        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => navigate('/')}
          style={{
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            color: '#0B0B0B',
            padding: '14px 44px',
            borderRadius: '12px',
            fontWeight: '700',
            fontSize: '15px',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 6px 28px rgba(212,175,55,0.45)',
            fontFamily: 'system-ui, sans-serif',
            letterSpacing: '0.3px',
            transition: 'box-shadow 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.boxShadow = '0 10px 40px rgba(212,175,55,0.65)'}
          onMouseLeave={e => e.currentTarget.style.boxShadow = '0 6px 28px rgba(212,175,55,0.45)'}
        >
          Back to Home
        </motion.button>

        {/* Subtle decorative text */}
        <p style={{
          marginTop: '28px',
          fontSize: '12px',
          color: 'rgba(212,175,55,0.3)',
          fontFamily: "'Georgia', 'Times New Roman', serif",
          letterSpacing: '2px',
          textTransform: 'uppercase',
        }}>
          CaseIQ · Legal Platform
        </p>
      </motion.div>
    </div>
  );
};

export default NotFoundPage;
