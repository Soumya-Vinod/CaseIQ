import { useSettings } from '../context/SettingsContext';
import { useAuth } from '../context/AuthContext';
import PageTransition from '../components/ui/PageTransition';
import { Moon, Sun, Type, Globe, Bell, Shield, Info } from 'lucide-react';
import { motion } from 'framer-motion';

const SettingsSection = ({ title, icon: Icon, children }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    style={{
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(212,175,55,0.18)',
      borderRadius: '18px',
      padding: '28px',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(212,175,55,0.07)',
      position: 'relative',
      overflow: 'hidden',
    }}
  >
    {/* subtle top accent */}
    <div style={{ position: 'absolute', top: 0, left: '20%', right: '20%', height: '1px', background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent)' }} />

    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '22px' }}>
      <div style={{
        width: '36px', height: '36px', borderRadius: '10px',
        background: 'linear-gradient(135deg, rgba(212,175,55,0.2), rgba(197,164,109,0.1))',
        border: '1px solid rgba(212,175,55,0.25)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <Icon size={16} color="#D4AF37" />
      </div>
      <h2 style={{
        fontWeight: '700', fontSize: '16px',
        color: '#E5E5E5',
        fontFamily: "'Georgia', 'Times New Roman', serif",
      }}>{title}</h2>
    </div>
    {children}
  </motion.div>
);

const ToggleRow = ({ label, description, checked, onChange }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0' }}>
    <div>
      <p style={{ fontSize: '14px', fontWeight: '500', color: '#E5E5E5', fontFamily: 'system-ui, sans-serif' }}>{label}</p>
      {description && (
        <p style={{ fontSize: '12px', marginTop: '2px', color: '#71717A', fontFamily: 'system-ui, sans-serif' }}>{description}</p>
      )}
    </div>
    <label style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', cursor: 'pointer', flexShrink: 0 }}>
      <input type="checkbox" checked={checked} onChange={onChange} style={{ display: 'none' }} />
      <div
        onClick={onChange}
        style={{
          width: '44px', height: '24px', borderRadius: '12px',
          background: checked ? 'linear-gradient(135deg, #D4AF37, #FFD700)' : 'rgba(255,255,255,0.1)',
          border: checked ? 'none' : '1px solid rgba(212,175,55,0.2)',
          transition: 'all 0.25s ease',
          cursor: 'pointer',
          position: 'relative',
          boxShadow: checked ? '0 2px 12px rgba(212,175,55,0.4)' : 'none',
        }}
      >
        <div style={{
          position: 'absolute', top: '2px',
          left: checked ? '22px' : '2px',
          width: '20px', height: '20px',
          background: checked ? '#0B0B0B' : '#71717A',
          borderRadius: '50%',
          transition: 'left 0.25s ease',
          boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
        }} />
      </div>
    </label>
  </div>
);

const SettingsPage = () => {
  const { darkMode, toggleDarkMode, language, setLanguage, fontSize, setFontSize } = useSettings();
  const { user } = useAuth();

  const languages = [
    { value: 'English', label: 'English', native: 'English' },
    { value: 'Hindi', label: 'Hindi', native: 'हिंदी' },
    { value: 'Marathi', label: 'Marathi', native: 'मराठी' },
    { value: 'Tamil', label: 'Tamil', native: 'தமிழ்' },
    { value: 'Telugu', label: 'Telugu', native: 'తెలుగు' },
  ];

  const fontSizes = [
    { value: 14, label: 'Small' },
    { value: 16, label: 'Medium' },
    { value: 18, label: 'Large' },
    { value: 20, label: 'XL' },
  ];

  const dividerStyle = { height: '1px', background: 'rgba(212,175,55,0.1)', margin: '4px 0' };

  return (
    <PageTransition>
      <div className="max-w-2xl mx-auto space-y-5 pb-16">

        {/* Header */}
        <div style={{ marginBottom: '8px' }}>
          <h1 style={{
            fontSize: '32px', fontWeight: '800',
            fontFamily: "'Georgia', 'Times New Roman', serif",
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            marginBottom: '6px',
          }}>Settings</h1>
          <p style={{ color: '#A1A1AA', fontFamily: 'system-ui, sans-serif', fontSize: '14px' }}>
            Customize your CaseIQ experience
          </p>
        </div>

        {/* Appearance */}
        <SettingsSection title="Appearance" icon={Sun}>
          <ToggleRow
            label="Dark Mode"
            description="Switch to a darker interface for low-light usage"
            checked={darkMode}
            onChange={toggleDarkMode}
          />

          <div style={dividerStyle} />

          <div style={{ paddingTop: '16px' }}>
            <p style={{ fontSize: '13px', fontWeight: '600', color: '#C5A46D', marginBottom: '12px', fontFamily: 'system-ui, sans-serif', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
              Font Size
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
              {fontSizes.map((size) => (
                <button
                  key={size.value}
                  onClick={() => setFontSize(size.value)}
                  style={{
                    padding: '9px 8px',
                    borderRadius: '10px',
                    fontSize: '13px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    fontFamily: 'system-ui, sans-serif',
                    ...(fontSize === size.value ? {
                      background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                      color: '#0B0B0B',
                      border: 'none',
                      boxShadow: '0 3px 12px rgba(212,175,55,0.4)',
                    } : {
                      background: 'rgba(255,255,255,0.04)',
                      color: '#A1A1AA',
                      border: '1px solid rgba(212,175,55,0.15)',
                    }),
                  }}
                  onMouseEnter={e => { if (fontSize !== size.value) { e.target.style.borderColor = 'rgba(212,175,55,0.4)'; e.target.style.color = '#D4AF37'; }}}
                  onMouseLeave={e => { if (fontSize !== size.value) { e.target.style.borderColor = 'rgba(212,175,55,0.15)'; e.target.style.color = '#A1A1AA'; }}}
                >
                  {size.label}
                </button>
              ))}
            </div>
            <p style={{ fontSize: '12px', marginTop: '12px', color: '#71717A', fontFamily: 'system-ui, sans-serif' }}>
              Preview: <span style={{ fontSize: `${fontSize}px`, color: '#C5A46D' }}>The quick brown fox</span>
            </p>
          </div>
        </SettingsSection>

        {/* Language */}
        <SettingsSection title="Language" icon={Globe}>
          <p style={{ fontSize: '12px', color: '#71717A', marginBottom: '14px', fontFamily: 'system-ui, sans-serif' }}>
            Select your preferred language for AI responses
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {languages.map((lang) => (
              <button
                key={lang.value}
                onClick={() => setLanguage(lang.value)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '13px 16px',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  fontFamily: 'system-ui, sans-serif',
                  ...(language === lang.value ? {
                    background: 'rgba(212,175,55,0.1)',
                    border: '1px solid rgba(212,175,55,0.4)',
                    boxShadow: '0 2px 12px rgba(212,175,55,0.1)',
                  } : {
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }),
                }}
                onMouseEnter={e => { if (language !== lang.value) e.currentTarget.style.borderColor = 'rgba(212,175,55,0.2)'; }}
                onMouseLeave={e => { if (language !== lang.value) e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; }}
              >
                <span style={{ fontSize: '14px', fontWeight: '500', color: language === lang.value ? '#D4AF37' : '#E5E5E5' }}>
                  {lang.label}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', color: '#71717A' }}>{lang.native}</span>
                  {language === lang.value && (
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#D4AF37', boxShadow: '0 0 6px rgba(212,175,55,0.6)', display: 'inline-block' }} />
                  )}
                </div>
              </button>
            ))}
          </div>
        </SettingsSection>

        {/* Privacy */}
        <SettingsSection title="Privacy & Data" icon={Shield}>
          <ToggleRow
            label="Save Query History"
            description="Store your legal queries locally for quick access"
            checked={true}
            onChange={() => {}}
          />
          <div style={{ ...dividerStyle, marginTop: '8px' }} />
          <div style={{ paddingTop: '16px' }}>
            <button
              onClick={() => {
                localStorage.removeItem('caseiq_chat_guest');
                localStorage.removeItem('caseiq_fir');
              }}
              style={{
                fontSize: '13px',
                color: '#F87171',
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.2)',
                padding: '8px 16px',
                borderRadius: '10px',
                cursor: 'pointer',
                fontWeight: '500',
                fontFamily: 'system-ui, sans-serif',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.target.style.background = 'rgba(239,68,68,0.15)'; e.target.style.borderColor = 'rgba(239,68,68,0.4)'; }}
              onMouseLeave={e => { e.target.style.background = 'rgba(239,68,68,0.08)'; e.target.style.borderColor = 'rgba(239,68,68,0.2)'; }}
            >
              Clear all local data
            </button>
          </div>
        </SettingsSection>

        {/* About */}
        <SettingsSection title="About CaseIQ" icon={Info}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {[
              { label: 'Version', value: '1.0.0' },
              { label: 'AI Model', value: 'Groq Llama 3.3 70B' },
              { label: 'Legal Sections', value: '1,641' },
              { label: 'Acts Covered', value: 'BNS, BNSS, BSA, IPC, CrPC' },
              ...(user ? [{ label: 'Signed in as', value: user.email }] : []),
            ].map(({ label, value }, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '11px 0',
                borderBottom: i < 4 ? '1px solid rgba(212,175,55,0.08)' : 'none',
              }}>
                <span style={{ fontSize: '13px', color: '#71717A', fontFamily: 'system-ui, sans-serif' }}>{label}</span>
                <span style={{
                  fontSize: '13px', fontWeight: '600', color: '#D4AF37',
                  fontFamily: 'system-ui, sans-serif',
                  maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{value}</span>
              </div>
            ))}
          </div>

          <div style={{
            marginTop: '20px', paddingTop: '16px',
            borderTop: '1px solid rgba(212,175,55,0.1)',
            fontSize: '12px', color: '#52525B',
            fontFamily: 'system-ui, sans-serif',
            lineHeight: '1.6',
          }}>
            CaseIQ provides legal information for awareness only. It does not constitute legal advice.
            Always consult a qualified advocate for your specific situation.
          </div>
        </SettingsSection>

      </div>
    </PageTransition>
  );
};

export default SettingsPage;
