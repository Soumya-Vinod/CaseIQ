import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useSettings } from '../../context/SettingsContext';
import { Settings, LogOut } from 'lucide-react';
import GlobalSearch from '../ui/GlobalSearch';
import logo from '../../assets/logo.png';

const Header = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { darkMode } = useSettings();

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 40,
      background: 'rgba(11,11,11,0.88)',
      borderBottom: '1px solid rgba(212,175,55,0.18)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      transition: 'all 300ms',
    }}>
      <div style={{
        padding: '10px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '16px',
      }}>

        {/* Logo */}
        <div
          onClick={() => navigate('/')}
          style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', flexShrink: 0 }}
        >
          <img
            src={logo}
            alt="CaseIQ"
            style={{
              height: '56px',
              width: 'auto',
              objectFit: 'contain',
              transition: 'transform 300ms, filter 300ms',
              filter: 'drop-shadow(0 0 10px rgba(212,175,55,0.28))',
            }}
            onMouseEnter={e => {
              e.target.style.transform = 'scale(1.05)';
              e.target.style.filter = 'drop-shadow(0 0 20px rgba(212,175,55,0.55))';
            }}
            onMouseLeave={e => {
              e.target.style.transform = 'scale(1)';
              e.target.style.filter = 'drop-shadow(0 0 10px rgba(212,175,55,0.28))';
            }}
          />
        </div>

        {/* Global Search — center */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', maxWidth: '440px', margin: '0 auto' }}>
          <GlobalSearch />
        </div>

        {/* Right Side */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          {user && (
            <div
              onClick={() => navigate('/profile')}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                cursor: 'pointer',
                padding: '6px 10px', borderRadius: '10px',
                transition: 'background 0.2s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(212,175,55,0.08)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{
                width: '34px', height: '34px', borderRadius: '50%',
                background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 2px 10px rgba(212,175,55,0.4)',
                flexShrink: 0,
              }}>
                <span style={{ color: '#0B0B0B', fontWeight: '800', fontSize: '13px', fontFamily: 'system-ui, sans-serif' }}>
                  {(user.full_name || user.email || 'U')[0].toUpperCase()}
                </span>
              </div>
              <span style={{
                fontSize: '13px', fontWeight: '500', color: '#E5E5E5',
                fontFamily: 'system-ui, sans-serif',
              }} className="hidden md:block">
                {user.full_name || user.email}
              </span>
            </div>
          )}

          <button
            onClick={() => navigate('/settings')}
            style={{
              padding: '8px', borderRadius: '10px',
              background: 'transparent', border: 'none',
              cursor: 'pointer', transition: 'all 0.2s',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(212,175,55,0.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <Settings size={17} color="#A1A1AA" />
          </button>

          {user && (
            <button
              onClick={logout}
              style={{
                padding: '8px', borderRadius: '10px',
                background: 'transparent', border: 'none',
                cursor: 'pointer', transition: 'all 0.2s',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.12)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <LogOut size={17} color="#F87171" />
            </button>
          )}

          {!user && (
            <button
              onClick={() => navigate('/login')}
              style={{
                background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                color: '#0B0B0B',
                padding: '8px 18px',
                borderRadius: '10px',
                fontSize: '13px',
                fontWeight: '700',
                border: 'none',
                cursor: 'pointer',
                boxShadow: '0 3px 14px rgba(212,175,55,0.4)',
                transition: 'all 0.2s',
                fontFamily: 'system-ui, sans-serif',
              }}
              onMouseEnter={e => {
                e.target.style.boxShadow = '0 5px 20px rgba(212,175,55,0.6)';
                e.target.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={e => {
                e.target.style.boxShadow = '0 3px 14px rgba(212,175,55,0.4)';
                e.target.style.transform = 'translateY(0)';
              }}
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Bottom gold shimmer line */}
      <div style={{
        height: '1px',
        background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.55), transparent)',
      }} />
    </header>
  );
};

export default Header;
