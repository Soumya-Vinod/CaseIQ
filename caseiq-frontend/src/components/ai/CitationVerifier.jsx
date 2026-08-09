import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { X, BookOpen, CheckCircle2, XCircle } from 'lucide-react';
import { legalAPI } from '../../services/api';

const CitationVerifier = ({ citation, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    legalAPI.verifyCitation(citation.act, citation.section)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch(() => { if (!cancelled) setData({ verified: false, message: 'Not found in database.' }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [citation]);

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
        backdropFilter: 'blur(8px)', zIndex: 200,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      }}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9 }}
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'rgba(14,12,6,0.98)', border: '1px solid rgba(212,175,55,0.25)',
          borderRadius: '20px', maxWidth: '560px', width: '100%',
          maxHeight: '80vh', overflowY: 'auto',
        }}
      >
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '18px 22px', borderBottom: '1px solid rgba(212,175,55,0.12)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={16} style={{ color: '#D4AF37' }} />
            <span style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: '1.1rem', fontWeight: 700, fontStyle: 'italic', color: '#D4AF37' }}>
              {citation.act} §{citation.section}
            </span>
          </div>
          <button onClick={onClose} style={{ padding: '6px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)', background: 'transparent', cursor: 'pointer', color: '#8A8A92', display: 'flex' }}>
            <X size={14} />
          </button>
        </div>
        <div style={{ padding: '22px' }}>
          {loading ? (
            <p style={{ color: '#8A8A92', fontSize: '0.82rem' }}>Verifying...</p>
          ) : data?.verified ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <CheckCircle2 size={14} style={{ color: '#4CAF50' }} />
                <span style={{ fontSize: '0.78rem', color: '#4CAF50', fontWeight: 600 }}>Verified</span>
              </div>
              <h3 style={{ fontSize: '0.95rem', color: '#E8E8E0', fontWeight: 600, marginBottom: '12px' }}>{data.section_title}</h3>
              <p style={{ fontSize: '0.82rem', lineHeight: 1.7, color: '#C8C8C0' }}>{data.section_text}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <XCircle size={16} style={{ color: '#F44336' }} />
              <p style={{ fontSize: '0.82rem', color: '#E8C8C8' }}>{data?.message || 'Not verified.'}</p>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CitationVerifier;