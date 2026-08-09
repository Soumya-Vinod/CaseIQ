import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Send } from 'lucide-react';
import { legalAPI } from '../../services/api';
import toast from 'react-hot-toast';

const PRESETS = [
  "What if I don't file the FIR?",
  "What if the accused denies everything?",
  "What if I delay reporting by 30 days?",
  "What if I want to settle out of court?",
];

const ScenarioSimulator = ({ situation }) => {
  const [scenario, setScenario] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const runSim = async (text) => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await legalAPI.simulateScenario(situation, text);
      setResult(res.data.simulation);
    } catch {
      toast.error('Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: 'rgba(14,12,6,0.96)', border: '1px solid rgba(212,175,55,0.2)', borderRadius: '20px', padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
        <Sparkles size={18} style={{ color: '#D4AF37' }} />
        <h3 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: '1.15rem', fontWeight: 700, fontStyle: 'italic', color: '#D4AF37' }}>
          What-If Simulator
        </h3>
      </div>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
        <input
          type="text" value={scenario} onChange={(e) => setScenario(e.target.value)}
          placeholder='e.g. "What if I lose the receipt?"'
          onKeyDown={(e) => e.key === 'Enter' && runSim(scenario)}
          style={{ flex: 1, padding: '10px 14px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(212,175,55,0.2)', borderRadius: '10px', color: '#E8E8E0', fontFamily: 'inherit', fontSize: '0.85rem', outline: 'none' }}
        />
        <button onClick={() => runSim(scenario)} disabled={loading || !scenario.trim()}
          style={{ padding: '10px 16px', borderRadius: '10px', border: 'none', background: 'linear-gradient(135deg, #B8960C, #D4AF37)', color: '#0B0B0B', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <Send size={14} />
        </button>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
        {PRESETS.map((p, i) => (
          <button key={i} onClick={() => { setScenario(p); runSim(p); }}
            style={{ fontSize: '0.74rem', padding: '6px 12px', borderRadius: '20px', border: '1px solid rgba(212,175,55,0.15)', background: 'transparent', color: '#9A7D3A', cursor: 'pointer', fontFamily: 'inherit' }}>
            {p}
          </button>
        ))}
      </div>
      {loading && <p style={{ color: '#8A8A92', fontSize: '0.78rem' }}>Simulating...</p>}
      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(212,175,55,0.12)', borderRadius: '12px' }}>
          <h4 style={{ fontSize: '0.9rem', color: '#E8E8E0', fontWeight: 600, marginBottom: '10px' }}>{result.scenario_title}</h4>
          <p style={{ fontSize: '0.82rem', color: '#C8C8C0', lineHeight: 1.6, marginBottom: '10px' }}>{result.legal_outcome}</p>
          {result.what_to_do && (
            <div style={{ padding: '10px 14px', background: 'rgba(76,175,80,0.06)', border: '1px solid rgba(76,175,80,0.15)', borderRadius: '10px' }}>
              <p style={{ fontSize: '0.78rem', color: '#D0E8D0' }}>{result.what_to_do}</p>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
};

export default ScenarioSimulator;