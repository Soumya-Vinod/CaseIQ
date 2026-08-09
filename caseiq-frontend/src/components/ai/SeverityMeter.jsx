import { AlertCircle, AlertTriangle, Shield, Zap } from 'lucide-react';

const CONFIG = {
  low: {
    color: '#4CAF50',
    bg: 'rgba(76,175,80,0.1)',
    border: 'rgba(76,175,80,0.3)',
    icon: Shield,
    label: 'Low Severity',
    desc: 'Minor issue, standard procedures apply',
    fill: 25,
  },
  medium: {
    color: '#FFC107',
    bg: 'rgba(255,193,7,0.08)',
    border: 'rgba(255,193,7,0.3)',
    icon: AlertCircle,
    label: 'Medium Severity',
    desc: 'Requires prompt action',
    fill: 50,
  },
  high: {
    color: '#FF9800',
    bg: 'rgba(255,152,0,0.08)',
    border: 'rgba(255,152,0,0.3)',
    icon: AlertTriangle,
    label: 'High Severity',
    desc: 'Serious matter — act immediately',
    fill: 75,
  },
  critical: {
    color: '#F44336',
    bg: 'rgba(244,67,54,0.08)',
    border: 'rgba(244,67,54,0.3)',
    icon: Zap,
    label: 'Critical',
    desc: 'Urgent — take action without delay',
    fill: 100,
  },
};

const SeverityMeter = ({ severity = 'medium', reason }) => {
  const c = CONFIG[severity] || CONFIG.medium;
  const Icon = c.icon;

  return (
    <div style={{
      background: c.bg,
      border: `1px solid ${c.border}`,
      borderRadius: '14px',
      padding: '16px 18px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
        <div style={{
          width: '34px',
          height: '34px',
          borderRadius: '10px',
          background: c.bg,
          border: `1px solid ${c.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={16} style={{ color: c.color }} />
        </div>
        <div style={{ flex: 1 }}>
          <p style={{
            fontSize: '0.82rem',
            fontWeight: 700,
            color: c.color,
            letterSpacing: '0.3px',
          }}>
            {c.label}
          </p>
          <p style={{ fontSize: '0.72rem', color: '#8A8A92', marginTop: '2px' }}>
            {c.desc}
          </p>
        </div>
      </div>

      {/* Meter bar */}
      <div style={{
        height: '4px',
        background: 'rgba(255,255,255,0.04)',
        borderRadius: '2px',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${c.fill}%`,
          background: `linear-gradient(90deg, ${c.color}99, ${c.color})`,
          borderRadius: '2px',
          transition: 'width 0.8s ease',
          boxShadow: `0 0 12px ${c.color}40`,
        }} />
      </div>

      {reason && (
        <p style={{
          fontSize: '0.72rem',
          color: '#6B6B75',
          marginTop: '10px',
          lineHeight: 1.5,
          fontStyle: 'italic',
        }}>
          {reason}
        </p>
      )}
    </div>
  );
};

export default SeverityMeter;