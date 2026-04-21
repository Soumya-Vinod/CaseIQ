import { NavLink, useNavigate } from 'react-router-dom';
import { useSettings } from '../../context/SettingsContext';
import { useAuth } from '../../context/AuthContext';
import {
  Home, MessageCircle, FileText, LayoutDashboard,
  BookOpen, History, Newspaper, Scale, Settings,
  LogOut, ChevronRight, MapPin,
} from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = () => {
  const { darkMode } = useSettings();
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { to: '/',          icon: Home,            label: 'Home' },
    { to: '/chat',      icon: MessageCircle,   label: 'AI Assistant' },
    { to: '/fir-draft', icon: FileText,        label: 'FIR Draft' },
    { to: '/laws',      icon: Scale,           label: 'Law Explorer' },
    { to: '/news',      icon: Newspaper,       label: 'Legal News' },
    { to: '/education', icon: BookOpen,        label: 'Education' },
    { to: '/stations',  icon: MapPin,          label: 'Find Stations' },
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/history',   icon: History,         label: 'History' },
  ];

  return (
    // height: 100% + no minHeight/sticky — Layout wrapper controls sizing
    <aside style={{
      width: '240px',
      height: '100%',             /* fill the Layout wrapper, not the viewport */
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 12px',
      background: 'rgba(10,10,10,0.92)',
      borderRight: '1px solid rgba(212,175,55,0.15)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      flexShrink: 0,
      boxSizing: 'border-box',
    }}>

      {/* ── Nav items ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px', overflowY: 'auto' }}>
        <p style={{
          fontSize: '10px',
          textTransform: 'uppercase',
          letterSpacing: '2px',
          color: 'rgba(212,175,55,0.45)',
          padding: '0 12px',
          marginBottom: '12px',
          fontWeight: '600',
          fontFamily: 'system-ui, sans-serif',
          flexShrink: 0,
        }}>
          Navigation
        </p>

        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={{ textDecoration: 'none', flexShrink: 0 }}
          >
            {({ isActive }) => (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '9px 12px',
                  borderRadius: '10px',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer',
                  fontFamily: 'system-ui, sans-serif',
                  fontSize: '13px',
                  fontWeight: isActive ? '600' : '500',
                  position: 'relative',
                  ...(isActive ? {
                    background: 'linear-gradient(135deg, rgba(212,175,55,0.18), rgba(255,215,0,0.08))',
                    color: '#D4AF37',
                    border: '1px solid rgba(212,175,55,0.3)',
                    boxShadow: '0 2px 12px rgba(212,175,55,0.12)',
                  } : {
                    background: 'transparent',
                    color: '#A1A1AA',
                    border: '1px solid transparent',
                  }),
                }}
                onMouseEnter={e => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'rgba(212,175,55,0.07)';
                    e.currentTarget.style.color = '#D4AF37';
                    e.currentTarget.style.borderColor = 'rgba(212,175,55,0.15)';
                  }
                }}
                onMouseLeave={e => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = '#A1A1AA';
                    e.currentTarget.style.borderColor = 'transparent';
                  }
                }}
              >
                {isActive && (
                  <div style={{
                    position: 'absolute',
                    left: 0, top: '20%', bottom: '20%',
                    width: '3px',
                    background: 'linear-gradient(180deg, #D4AF37, #FFD700)',
                    borderRadius: '0 3px 3px 0',
                    boxShadow: '0 0 8px rgba(212,175,55,0.6)',
                  }} />
                )}
                <Icon size={15} style={{ flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{label}</span>
                {isActive && <ChevronRight size={12} style={{ opacity: 0.6 }} />}
              </div>
            )}
          </NavLink>
        ))}
      </div>

      {/* ── Divider ── */}
      <div style={{
        height: '1px',
        margin: '16px 0',
        flexShrink: 0,
        background: 'linear-gradient(90deg, transparent, rgba(212,175,55,0.25), transparent)',
      }} />

      {/* ── Bottom section ── */}
      <div style={{ flexShrink: 0 }}>
        {isAuthenticated ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>

            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => navigate('/profile')}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 12px',
                borderRadius: '12px',
                background: 'rgba(212,175,55,0.06)',
                border: '1px solid rgba(212,175,55,0.15)',
                cursor: 'pointer',
                marginBottom: '6px',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(212,175,55,0.11)';
                e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(212,175,55,0.06)';
                e.currentTarget.style.borderColor = 'rgba(212,175,55,0.15)';
              }}
            >
              <div style={{
                width: '34px', height: '34px', borderRadius: '50%',
                background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 2px 10px rgba(212,175,55,0.35)',
                flexShrink: 0,
              }}>
                <span style={{ color: '#0B0B0B', fontWeight: '800', fontSize: '13px', fontFamily: 'system-ui, sans-serif' }}>
                  {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                </span>
              </div>
              <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                <p style={{
                  fontSize: '13px', fontWeight: '600', color: '#E5E5E5',
                  fontFamily: 'system-ui, sans-serif',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  margin: 0,
                }}>
                  {user?.full_name || 'My Account'}
                </p>
                <p style={{
                  fontSize: '11px', color: '#71717A',
                  fontFamily: 'system-ui, sans-serif',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  margin: 0,
                }}>
                  {user?.email}
                </p>
              </div>
            </motion.button>

            <NavLink to="/settings" style={{ textDecoration: 'none' }}>
              {({ isActive }) => (
                <div
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '9px 12px', borderRadius: '10px',
                    cursor: 'pointer', transition: 'all 0.2s',
                    fontSize: '13px', fontWeight: '500',
                    fontFamily: 'system-ui, sans-serif',
                    color: isActive ? '#D4AF37' : '#A1A1AA',
                    background: isActive ? 'rgba(212,175,55,0.1)' : 'transparent',
                    border: isActive ? '1px solid rgba(212,175,55,0.25)' : '1px solid transparent',
                  }}
                  onMouseEnter={e => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'rgba(212,175,55,0.07)';
                      e.currentTarget.style.color = '#D4AF37';
                    }
                  }}
                  onMouseLeave={e => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#A1A1AA';
                    }
                  }}
                >
                  <Settings size={15} style={{ flexShrink: 0 }} />
                  <span style={{ flex: 1 }}>Settings</span>
                </div>
              )}
            </NavLink>

            <button
              onClick={logout}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '9px 12px', borderRadius: '10px',
                cursor: 'pointer', transition: 'all 0.2s',
                fontSize: '13px', fontWeight: '500',
                fontFamily: 'system-ui, sans-serif',
                color: '#F87171',
                background: 'transparent',
                border: '1px solid transparent',
                width: '100%',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(239,68,68,0.1)';
                e.currentTarget.style.borderColor = 'rgba(239,68,68,0.2)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.borderColor = 'transparent';
              }}
            >
              <LogOut size={15} style={{ flexShrink: 0 }} />
              <span style={{ flex: 1, textAlign: 'left' }}>Sign Out</span>
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <p style={{
              fontSize: '12px', textAlign: 'center', color: '#71717A',
              marginBottom: '6px', fontFamily: 'system-ui, sans-serif',
            }}>
              Sign in to save your history
            </p>
            <button
              onClick={() => navigate('/login')}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
                color: '#0B0B0B',
                padding: '10px 16px',
                borderRadius: '10px',
                fontSize: '13px',
                fontWeight: '700',
                border: 'none',
                cursor: 'pointer',
                boxShadow: '0 3px 14px rgba(212,175,55,0.35)',
                transition: 'all 0.2s',
                fontFamily: 'system-ui, sans-serif',
              }}
              onMouseEnter={e => {
                e.target.style.boxShadow = '0 5px 20px rgba(212,175,55,0.55)';
                e.target.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={e => {
                e.target.style.boxShadow = '0 3px 14px rgba(212,175,55,0.35)';
                e.target.style.transform = 'translateY(0)';
              }}
            >
              Sign In
            </button>
            <button
              onClick={() => navigate('/register')}
              style={{
                width: '100%',
                background: 'transparent',
                color: '#C5A46D',
                padding: '10px 16px',
                borderRadius: '10px',
                fontSize: '13px',
                fontWeight: '500',
                border: '1px solid rgba(212,175,55,0.25)',
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontFamily: 'system-ui, sans-serif',
              }}
              onMouseEnter={e => {
                e.target.style.background = 'rgba(212,175,55,0.07)';
                e.target.style.borderColor = 'rgba(212,175,55,0.45)';
                e.target.style.color = '#D4AF37';
              }}
              onMouseLeave={e => {
                e.target.style.background = 'transparent';
                e.target.style.borderColor = 'rgba(212,175,55,0.25)';
                e.target.style.color = '#C5A46D';
              }}
            >
              Create Account
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
