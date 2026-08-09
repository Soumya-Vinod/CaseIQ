import { motion } from 'framer-motion';
import {
  Scale, Gavel, Clock, CheckCircle2, Shield, Phone,
  ListChecks, BookOpen, X, AlertCircle, Zap, AlertTriangle,
} from 'lucide-react';

const SEVERITY_CONFIG = {
  low: { color: '#4CAF50', label: 'Low', icon: Shield, bgGrad: 'rgba(76,175,80,0.12), rgba(76,175,80,0.04)' },
  medium: { color: '#FFC107', label: 'Medium', icon: AlertCircle, bgGrad: 'rgba(255,193,7,0.12), rgba(255,193,7,0.04)' },
  high: { color: '#FF9800', label: 'High', icon: AlertTriangle, bgGrad: 'rgba(255,152,0,0.12), rgba(255,152,0,0.04)' },
  critical: { color: '#F44336', label: 'Critical', icon: Zap, bgGrad: 'rgba(244,67,54,0.12), rgba(244,67,54,0.04)' },
};

const SectionHeader = ({ icon: Icon, title, color = '#D4AF37' }) => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '14px',
  }}>
    <div style={{
      width: '28px',
      height: '28px',
      borderRadius: '8px',
      background: `linear-gradient(135deg, ${color}25, ${color}08)`,
      border: `1px solid ${color}30`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    }}>
      <Icon size={13} style={{ color }} />
    </div>
    <h4 style={{
      fontSize: '0.74rem',
      fontWeight: 700,
      letterSpacing: '2px',
      textTransform: 'uppercase',
      color,
      fontFamily: "'DM Sans', sans-serif",
    }}>
      {title}
    </h4>
    <div style={{
      flex: 1,
      height: '1px',
      background: `linear-gradient(90deg, ${color}30, transparent)`,
    }} />
  </div>
);

const Section = ({ children, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
    style={{
      padding: '20px 22px',
      borderTop: '1px solid rgba(212,175,55,0.08)',
    }}
  >
    {children}
  </motion.div>
);

const StructuredLegalCard = ({ data, onVerifyCitation, onClose }) => {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div style={{
        background: 'rgba(14,12,6,0.96)',
        border: '1px solid rgba(212,175,55,0.15)',
        borderRadius: '20px',
        padding: '60px 24px',
        textAlign: 'center',
        height: '100%',
      }}>
        <BookOpen size={36} style={{ color: '#3A3A40', marginBottom: '14px' }} />
        <p style={{ fontSize: '0.85rem', color: '#555560', marginBottom: '4px' }}>
          Structured breakdown will appear here
        </p>
        <p style={{ fontSize: '0.74rem', color: '#3A3A40' }}>
          Ask a legal question to see laws, steps, and rights
        </p>
      </div>
    );
  }

  const sev = SEVERITY_CONFIG[data.severity] || SEVERITY_CONFIG.medium;
  const SeverityIcon = sev.icon;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      style={{
        background: 'linear-gradient(180deg, rgba(18,15,6,0.98) 0%, rgba(12,10,4,0.98) 100%)',
        border: '1px solid rgba(212,175,55,0.2)',
        borderTopColor: 'rgba(212,175,55,0.4)',
        borderRadius: '20px',
        overflow: 'hidden',
        boxShadow: '0 24px 60px rgba(0,0,0,0.7), 0 0 60px rgba(212,175,55,0.05)',
        position: 'sticky',
        top: '80px',
        maxHeight: 'calc(100vh - 100px)',
        overflowY: 'auto',
      }}
    >
      {/* Decorative top accent */}
      <div style={{
        height: '3px',
        background: 'linear-gradient(90deg, transparent, #D4AF37 30%, #FFD700 50%, #D4AF37 70%, transparent)',
        boxShadow: '0 0 12px rgba(212,175,55,0.5)',
      }} />

      {/* Hero Header */}
      <div style={{
        padding: '22px 22px 20px',
        position: 'relative',
        background: `radial-gradient(ellipse at top right, rgba(212,175,55,0.08), transparent 60%)`,
        borderBottom: '1px solid rgba(212,175,55,0.1)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '14px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, rgba(212,175,55,0.25), rgba(212,175,55,0.08))',
              border: '1px solid rgba(212,175,55,0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 24px rgba(212,175,55,0.15)',
            }}>
              <Scale size={18} style={{ color: '#FFD700' }} />
            </div>
            <div>
              <p style={{
                fontSize: '0.62rem',
                fontWeight: 600,
                letterSpacing: '2.5px',
                textTransform: 'uppercase',
                color: '#9A7D3A',
                marginBottom: '2px',
              }}>
                Legal Breakdown
              </p>
              <p style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: '1.2rem',
                fontWeight: 700,
                fontStyle: 'italic',
                color: '#FFD700',
              }}>
                CaseIQ Analysis
              </p>
            </div>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close panel"
              style={{
                padding: '6px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.06)',
                background: 'transparent',
                cursor: 'pointer',
                color: '#555560',
                display: 'flex',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#D4AF37';
                e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#555560';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {data.situation_overview && (
          <p style={{
            fontSize: '0.88rem',
            color: '#D8D8D0',
            lineHeight: 1.7,
            paddingLeft: '52px',
          }}>
            {data.situation_overview}
          </p>
        )}
      </div>

      {/* Severity Banner */}
      {data.severity && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          style={{
            margin: '16px 22px 4px',
            padding: '14px 16px',
            borderRadius: '14px',
            background: `linear-gradient(135deg, ${sev.bgGrad})`,
            border: `1px solid ${sev.color}30`,
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Animated pulse for critical */}
          {data.severity === 'critical' && (
            <div style={{
              position: 'absolute',
              inset: 0,
              background: `radial-gradient(circle at center, ${sev.color}15, transparent 70%)`,
              animation: 'sevPulse 2s ease-in-out infinite',
            }} />
          )}
          <style>{`@keyframes sevPulse{0%,100%{opacity:0.5}50%{opacity:1}}`}</style>

          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: `${sev.color}20`,
            border: `1px solid ${sev.color}40`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            position: 'relative',
            zIndex: 1,
          }}>
            <SeverityIcon size={16} style={{ color: sev.color }} />
          </div>
          <div style={{ flex: 1, position: 'relative', zIndex: 1 }}>
            <div style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: '8px',
              marginBottom: '4px',
            }}>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 600,
                letterSpacing: '2px',
                textTransform: 'uppercase',
                color: '#8A8A92',
              }}>
                Severity
              </span>
              <span style={{
                fontSize: '0.92rem',
                fontWeight: 700,
                color: sev.color,
                letterSpacing: '0.5px',
              }}>
                {sev.label}
              </span>
            </div>
            {data.severity_reason && (
              <p style={{ fontSize: '0.74rem', color: '#A8A8A0', lineHeight: 1.5 }}>
                {data.severity_reason}
              </p>
            )}
            {/* Severity bar */}
            <div style={{
              height: '3px',
              background: 'rgba(255,255,255,0.04)',
              borderRadius: '2px',
              overflow: 'hidden',
              marginTop: '8px',
            }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{
                  width: data.severity === 'low' ? '25%'
                    : data.severity === 'medium' ? '50%'
                    : data.severity === 'high' ? '75%'
                    : '100%',
                }}
                transition={{ duration: 0.8, ease: 'easeOut', delay: 0.3 }}
                style={{
                  height: '100%',
                  background: `linear-gradient(90deg, ${sev.color}99, ${sev.color})`,
                  borderRadius: '2px',
                  boxShadow: `0 0 8px ${sev.color}60`,
                }}
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Laws */}
      {data.laws_applicable?.length > 0 && (
        <Section delay={0.15}>
          <SectionHeader icon={Scale} title="Applicable Laws" color="#D4AF37" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.laws_applicable.map((law, i) => (
              <motion.button
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.06 }}
                onClick={() => onVerifyCitation?.(law.act, law.section)}
                style={{
                  textAlign: 'left',
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: '1px solid rgba(212,175,55,0.15)',
                  background: 'linear-gradient(135deg, rgba(212,175,55,0.04), rgba(212,175,55,0.01))',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  fontFamily: 'inherit',
                  width: '100%',
                  position: 'relative',
                  overflow: 'hidden',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(212,175,55,0.4)';
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(212,175,55,0.08), rgba(212,175,55,0.03))';
                  e.currentTarget.style.transform = 'translateX(2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(212,175,55,0.15)';
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(212,175,55,0.04), rgba(212,175,55,0.01))';
                  e.currentTarget.style.transform = 'translateX(0)';
                }}
              >
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginBottom: '8px',
                  flexWrap: 'wrap',
                }}>
                  <span style={{
                    fontSize: '0.7rem',
                    fontWeight: 800,
                    color: '#0B0B0B',
                    background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                    padding: '3px 10px',
                    borderRadius: '6px',
                    letterSpacing: '0.5px',
                    boxShadow: '0 2px 8px rgba(212,175,55,0.25)',
                  }}>
                    {law.act} §{law.section}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#E8E0C8', fontWeight: 600 }}>
                    {law.title}
                  </span>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#8A8A92', lineHeight: 1.6 }}>
                  {law.why_applies}
                </p>
                {law.ipc_equivalent && (
                  <p style={{
                    fontSize: '0.68rem',
                    color: '#555560',
                    marginTop: '6px',
                    fontStyle: 'italic',
                  }}>
                    IPC equivalent: {law.ipc_equivalent}
                  </p>
                )}
                <span style={{
                  position: 'absolute',
                  top: '12px',
                  right: '14px',
                  fontSize: '0.6rem',
                  color: '#555560',
                  letterSpacing: '0.5px',
                }}>
                  Click to verify ↗
                </span>
              </motion.button>
            ))}
          </div>
        </Section>
      )}

      {/* Punishments */}
      {data.punishments?.length > 0 && (
        <Section delay={0.2}>
          <SectionHeader icon={Gavel} title="Punishments" color="#F44336" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.punishments.map((p, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 + i * 0.06 }}
                style={{
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: '1px solid rgba(244,67,54,0.18)',
                  background: 'linear-gradient(135deg, rgba(244,67,54,0.05), rgba(244,67,54,0.01))',
                }}
              >
                <p style={{
                  fontSize: '0.86rem',
                  fontWeight: 700,
                  color: '#F8C8C8',
                  marginBottom: '10px',
                  letterSpacing: '0.2px',
                }}>
                  {p.offence}
                </p>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '8px',
                  fontSize: '0.74rem',
                }}>
                  <PunishField label="Imprisonment" value={p.imprisonment} />
                  <PunishField label="Fine" value={p.fine} />
                  <PunishField
                    label="Bail"
                    value={p.bailable}
                    valueColor={p.bailable === 'Bailable' ? '#4CAF50' : '#FF9800'}
                  />
                  <PunishField label="Type" value={p.cognizable} />
                </div>
              </motion.div>
            ))}
          </div>
        </Section>
      )}

      {/* Steps */}
      {data.immediate_steps?.length > 0 && (
        <Section delay={0.25}>
          <SectionHeader icon={ListChecks} title="What to Do Now" color="#D4AF37" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.immediate_steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                style={{
                  display: 'flex',
                  gap: '14px',
                  padding: '14px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.025), rgba(255,255,255,0.005))',
                  border: '1px solid rgba(255,255,255,0.06)',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <div style={{
                  position: 'absolute',
                  left: 0, top: 0, bottom: 0,
                  width: '3px',
                  background: 'linear-gradient(180deg, transparent, #D4AF37, transparent)',
                  opacity: 0.6,
                }} />
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #D4AF37, #B8960C)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.74rem',
                  fontWeight: 800,
                  color: '#0B0B0B',
                  flexShrink: 0,
                  boxShadow: '0 2px 10px rgba(212,175,55,0.3)',
                }}>
                  {step.step || i + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{
                    fontSize: '0.85rem',
                    color: '#E8E8E0',
                    fontWeight: 600,
                    marginBottom: '4px',
                  }}>
                    {step.action}
                  </p>
                  <p style={{ fontSize: '0.76rem', color: '#8A8A92', lineHeight: 1.55 }}>
                    {step.details}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </Section>
      )}

      {/* Deadlines */}
      {data.critical_deadlines?.length > 0 && (
        <Section delay={0.3}>
          <SectionHeader icon={Clock} title="Critical Deadlines" color="#FFC107" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {data.critical_deadlines.map((d, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.35 + i * 0.06 }}
                style={{
                  padding: '12px 14px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, rgba(255,193,7,0.06), rgba(255,193,7,0.01))',
                  border: '1px solid rgba(255,193,7,0.2)',
                  borderLeft: '3px solid #FFC107',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                }}
              >
                <div style={{
                  padding: '6px 10px',
                  background: 'rgba(255,193,7,0.15)',
                  borderRadius: '8px',
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  color: '#FFC107',
                  flexShrink: 0,
                  letterSpacing: '0.3px',
                }}>
                  {d.deadline}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: '0.8rem', color: '#E8E0C0', marginBottom: '4px', fontWeight: 500 }}>
                    {d.what}
                  </p>
                  <p style={{ fontSize: '0.7rem', color: '#8A8A92' }}>
                    ⚠ {d.consequence}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </Section>
      )}

      {/* Rights */}
      {data.your_rights?.length > 0 && (
        <Section delay={0.35}>
          <SectionHeader icon={Shield} title="Your Rights" color="#4CAF50" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {data.your_rights.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + i * 0.05 }}
                style={{
                  padding: '12px 14px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, rgba(76,175,80,0.06), rgba(76,175,80,0.01))',
                  border: '1px solid rgba(76,175,80,0.18)',
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'flex-start',
                }}
              >
                <CheckCircle2 size={15} style={{ color: '#4CAF50', flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1 }}>
                  <p style={{
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: '#D0E8D0',
                    marginBottom: '4px',
                  }}>
                    {r.right}
                  </p>
                  <p style={{ fontSize: '0.74rem', color: '#8A9A8A', lineHeight: 1.55, marginBottom: '6px' }}>
                    {r.explanation}
                  </p>
                  {r.law && (
                    <span style={{
                      fontSize: '0.66rem',
                      color: '#4CAF50',
                      background: 'rgba(76,175,80,0.12)',
                      border: '1px solid rgba(76,175,80,0.2)',
                      padding: '2px 10px',
                      borderRadius: '6px',
                      fontWeight: 600,
                    }}>
                      {r.law}
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </Section>
      )}

      {/* Do's & Don'ts */}
      {data.dos_and_donts && (data.dos_and_donts.dos?.length > 0 || data.dos_and_donts.donts?.length > 0) && (
        <Section delay={0.4}>
          <SectionHeader icon={CheckCircle2} title="Do's & Don'ts" color="#9A7D3A" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {data.dos_and_donts.dos?.length > 0 && (
              <DoBox label="DO" color="#4CAF50" items={data.dos_and_donts.dos} />
            )}
            {data.dos_and_donts.donts?.length > 0 && (
              <DoBox label="DON'T" color="#F44336" items={data.dos_and_donts.donts} />
            )}
          </div>
        </Section>
      )}

      {/* Helplines */}
      {data.helplines?.length > 0 && (
        <Section delay={0.45}>
          <SectionHeader icon={Phone} title="Emergency Helplines" color="#4CAF50" />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {data.helplines.map((h, i) => (
              <motion.a
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 + i * 0.05 }}
                href={`tel:${h.number}`}
                title={h.when}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, rgba(76,175,80,0.1), rgba(76,175,80,0.03))',
                  border: '1px solid rgba(76,175,80,0.25)',
                  color: '#A8D8A8',
                  fontSize: '0.76rem',
                  fontWeight: 500,
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(76,175,80,0.18), rgba(76,175,80,0.06))';
                  e.currentTarget.style.borderColor = 'rgba(76,175,80,0.4)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(76,175,80,0.1), rgba(76,175,80,0.03))';
                  e.currentTarget.style.borderColor = 'rgba(76,175,80,0.25)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <Phone size={11} />
                <span style={{ fontWeight: 700, color: '#C8E8C8' }}>{h.number}</span>
                <span style={{ color: '#6B8B6B' }}>{h.name}</span>
              </motion.a>
            ))}
          </div>
        </Section>
      )}

      {/* Footer */}
      <div style={{
        padding: '16px 22px',
        borderTop: '1px solid rgba(212,175,55,0.1)',
        background: 'linear-gradient(180deg, transparent, rgba(212,175,55,0.03))',
      }}>
        <p style={{
          fontSize: '0.68rem',
          color: '#3A3A40',
          textAlign: 'center',
          fontStyle: 'italic',
          lineHeight: 1.5,
        }}>
          ⚠️ For legal awareness only. Consult a qualified advocate for case-specific guidance.
        </p>
      </div>
    </motion.div>
  );
};

const PunishField = ({ label, value, valueColor }) => (
  <div style={{
    background: 'rgba(0,0,0,0.25)',
    padding: '8px 10px',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.04)',
  }}>
    <p style={{
      fontSize: '0.6rem',
      color: '#555560',
      textTransform: 'uppercase',
      letterSpacing: '1.5px',
      fontWeight: 600,
      marginBottom: '2px',
    }}>
      {label}
    </p>
    <p style={{
      fontSize: '0.78rem',
      color: valueColor || '#D8D8D0',
      fontWeight: valueColor ? 700 : 500,
    }}>
      {value}
    </p>
  </div>
);

const DoBox = ({ label, color, items }) => (
  <div style={{
    padding: '12px 14px',
    borderRadius: '12px',
    background: `linear-gradient(135deg, ${color}08, ${color}02)`,
    border: `1px solid ${color}20`,
  }}>
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      marginBottom: '10px',
      paddingBottom: '8px',
      borderBottom: `1px solid ${color}15`,
    }}>
      <span style={{
        fontSize: '0.7rem',
        fontWeight: 800,
        color,
        letterSpacing: '1.5px',
      }}>
        {label === 'DO' ? '✓' : '✗'} {label}
      </span>
    </div>
    <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {items.map((d, i) => (
        <li key={i} style={{
          fontSize: '0.76rem',
          color: '#C8C8C0',
          paddingLeft: '14px',
          position: 'relative',
          lineHeight: 1.55,
        }}>
          <span style={{
            position: 'absolute',
            left: 0,
            color,
            fontWeight: 700,
          }}>·</span>
          {d}
        </li>
      ))}
    </ul>
  </div>
);

export default StructuredLegalCard;