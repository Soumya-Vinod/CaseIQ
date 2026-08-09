import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Settings, LogOut, Menu, X } from 'lucide-react';
import logo from '../../assets/logo.png';

const Header = ({ onToggleSidebar, sidebarOpen }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: 'rgba(11,11,11,0.94)',
      backdropFilter: 'blur(24px)',
      WebkitBackdropFilter: 'blur(24px)',
      borderBottom: '1px solid rgba(212,175,55,0.12)',
    }}>
      <div style={{
        maxWidth: '1280px',
        margin: '0 auto',
        padding: '0 20px',
        height: '60px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={onToggleSidebar}
            aria-label="Toggle menu"
            style={{
              padding: '8px',
              borderRadius: '10px',
              border: '1px solid rgba(212,175,55,0.25)',
              background: sidebarOpen ? 'rgba(212,175,55,0.18)' : 'rgba(212,175,55,0.06)',
              cursor: 'pointer',
              color: sidebarOpen ? '#FFD700' : '#D4AF37',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
              boxShadow: '0 0 12px rgba(212,175,55,0.15)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#FFD700';
              e.currentTarget.style.borderColor = 'rgba(212,175,55,0.5)';
              e.currentTarget.style.background = 'rgba(212,175,55,0.15)';
              e.currentTarget.style.boxShadow = '0 0 18px rgba(212,175,55,0.3)';
            }}
            onMouseLeave={(e) => {
              if (!sidebarOpen) {
                e.currentTarget.style.color = '#D4AF37';
                e.currentTarget.style.borderColor = 'rgba(212,175,55,0.25)';
                e.currentTarget.style.background = 'rgba(212,175,55,0.06)';
                e.currentTarget.style.boxShadow = '0 0 12px rgba(212,175,55,0.15)';
              }
            }}
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          <div
            onClick={() => navigate('/')}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            <img
              src={logo}
              alt="CaseIQ"
              style={{
                height: '40px',
                width: 'auto',
                objectFit: 'contain',
                filter: 'drop-shadow(0 0 12px rgba(212,175,55,0.3))',
              }}
            />
            <span style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontSize: '1.3rem',
              fontWeight: 700,
              fontStyle: 'italic',
              background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '0.5px',
            }}>
              CaseIQ
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {user && (
            <div
              onClick={() => navigate('/profile')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                cursor: 'pointer',
                padding: '6px 14px 6px 8px',
                borderRadius: '20px',
                border: '1px solid rgba(212,175,55,0.15)',
                background: 'rgba(212,175,55,0.04)',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(212,175,55,0.35)';
                e.currentTarget.style.background = 'rgba(212,175,55,0.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(212,175,55,0.15)';
                e.currentTarget.style.background = 'rgba(212,175,55,0.04)';
              }}
            >
              <div style={{
                width: '26px',
                height: '26px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #B8960C, #D4AF37)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.7rem',
                fontWeight: 700,
                color: '#0B0B0B',
              }}>
                {(user.full_name || user.email || 'U')[0].toUpperCase()}
              </div>
              <span style={{
                fontSize: '0.78rem',
                color: '#C9A84C',
                fontWeight: 500,
                maxWidth: '120px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {user.full_name || user.email?.split('@')[0]}
              </span>
            </div>
          )}

          <button
            onClick={() => navigate('/settings')}
            aria-label="Settings"
            style={{
              padding: '8px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.06)',
              background: 'transparent',
              cursor: 'pointer',
              color: '#555560',
              display: 'flex',
              alignItems: 'center',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#C9A84C';
              e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = '#555560';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
            }}
          >
            <Settings size={15} />
          </button>

          {user ? (
            <button
              onClick={logout}
              aria-label="Sign out"
              style={{
                padding: '8px',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.06)',
                background: 'transparent',
                cursor: 'pointer',
                color: '#555560',
                display: 'flex',
                alignItems: 'center',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ff6b6b';
                e.currentTarget.style.borderColor = 'rgba(255,100,100,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#555560';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
              }}
            >
              <LogOut size={15} />
            </button>
          ) : (
            <button
              onClick={() => navigate('/login')}
              style={{
                background: 'linear-gradient(135deg, #B8960C 0%, #D4AF37 50%, #FFD700 100%)',
                color: '#0B0B0B',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '8px 18px',
                border: 'none',
                borderRadius: '10px',
                cursor: 'pointer',
                letterSpacing: '0.4px',
                textTransform: 'uppercase',
                boxShadow: '0 4px 16px rgba(212,175,55,0.25)',
              }}
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      <div style={{
        height: '1px',
        background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.25), transparent)',
      }} />
    </header>
  );
};

export default Header;