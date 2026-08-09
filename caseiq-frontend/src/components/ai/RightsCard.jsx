import { motion } from 'framer-motion';
import { Shield, Phone, AlertTriangle, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';

const RightsCard = ({ data, loading }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!data) return;
    const text = [
      `MY LEGAL RIGHTS — ${data.situation_title}`,
      '',
      ...(data.rights || []).map((r, i) => `${i + 1}. ${r.right}\n   ${r.explanation}`),
      '',
      `⚠️ ${data.important_warning || ''}`,
    ].join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Copied');
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div style={{ background: 'rgba(14,12,6,0.96)', border: '1px solid rgba(212,175,55,0.2)', borderRadius: '20px', padding: '28px' }}>
        <p style={{ color: '#C9A84C', fontFamily: "'Cormorant Garamond', serif", fontSize: '1.1rem', fontStyle: 'italic' }}>Building Rights Card...</p>
      </div>
    );
  }
  if (!data || !data.rights) return null;

  return (
    <div style={{ borderRadius: '20px', overflow: 'hidden', border: '1px solid rgba(212,175,55,0.2)' }}>
      <div style={{ background: 'linear-gradient(135deg, #0F0D04, #1A1508)', padding: '22px 26px', position: 'relative' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Shield size={20} style={{ color: '#D4AF37' }} />
            </div>
            <div>
              <p style={{ fontSize: '0.6rem', color: '#6B5520', fontWeight: 600, letterSpacing: '3px', textTransform: 'uppercase', marginBottom: '3px' }}>CaseIQ Rights Card</p>
              <h3 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: '1.2rem', fontWeight: 700, color: '#D4AF37', fontStyle: 'italic' }}>{data.situation_title}</h3>
            </div>
          </div>
          <button onClick={handleCopy} style={{ padding: '7px 10px', borderRadius: '8px', border: '1px solid rgba(212,175,55,0.2)', background: 'transparent', cursor: 'pointer', color: '#9A7D3A', display: 'flex' }}>
            {copied ? <Check size={13} /> : <Copy size={13} />}
          </button>
        </div>
        {data.important_warning && (
          <div style={{ marginTop: '14px', background: 'rgba(212,175,55,0.06)', border: '1px solid rgba(212,175,55,0.15)', borderRadius: '10px', padding: '10px 14px', display: 'flex', gap: '8px' }}>
            <AlertTriangle size={13} style={{ color: '#9A7D3A', flexShrink: 0, marginTop: '1px' }} />
            <p style={{ fontSize: '0.76rem', color: '#8A7040', lineHeight: 1.5 }}>{data.important_warning}</p>
          </div>
        )}
      </div>
      <div style={{ background: 'rgba(10,9,3,0.98)', padding: '20px 24px', borderTop: 'none' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px', marginBottom: '20px' }}>
          {data.rights.map((right, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
              style={{ padding: '14px', borderRadius: '12px', border: '1px solid rgba(212,175,55,0.1)', background: 'rgba(212,175,55,0.02)' }}>
              <div style={{ display: 'flex', gap: '10px', marginBottom: '6px' }}>
                <span style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.64rem', fontWeight: 700, color: '#C9A84C', flexShrink: 0 }}>{i + 1}</span>
                <h5 style={{ fontSize: '0.82rem', fontWeight: 600, color: '#C8C8C0' }}>{right.right}</h5>
              </div>
              <p style={{ fontSize: '0.74rem', color: '#555560', lineHeight: 1.6, paddingLeft: '30px' }}>{right.explanation}</p>
              {right.law_reference && (
                <span style={{ display: 'inline-block', marginLeft: '30px', marginTop: '6px', fontSize: '0.65rem', color: '#9A7D3A', background: 'rgba(212,175,55,0.06)', padding: '1px 8px', borderRadius: '6px' }}>📚 {right.law_reference}</span>
              )}
              {right.what_to_say && (
                <div style={{ marginLeft: '30px', marginTop: '6px', padding: '6px 10px', borderLeft: '2px solid rgba(212,175,55,0.3)', background: 'rgba(212,175,55,0.03)' }}>
                  <p style={{ fontSize: '0.7rem', color: '#6B5520', fontStyle: 'italic' }}>💬 "{right.what_to_say}"</p>
                </div>
              )}
            </motion.div>
          ))}
        </div>
        {data.emergency_contacts?.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {data.emergency_contacts.map((c, i) => (
              <a key={i} href={`tel:${c.number}`} style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(76,175,80,0.06)', border: '1px solid rgba(76,175,80,0.2)', color: '#4A8A4A', padding: '8px 14px', borderRadius: '10px', fontSize: '0.76rem', fontWeight: 500, textDecoration: 'none', fontFamily: 'inherit' }}>
                <Phone size={12} />{c.name}: {c.number}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RightsCard;