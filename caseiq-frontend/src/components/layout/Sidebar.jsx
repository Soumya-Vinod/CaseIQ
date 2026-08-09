import { NavLink, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import {
  Home, MessageCircle, FileText, LayoutDashboard,
  BookOpen, History, Newspaper, Scale, Settings,
  LogOut, MapPin, X,
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    label: 'Main',
    items: [
      { to: '/', icon: Home, label: 'Home' },
      { to: '/chat', icon: MessageCircle, label: 'AI Assistant' },
      { to: '/fir-draft', icon: FileText, label: 'Complaint Draft' },
    ],
  },
  {
    label: 'Resources',
    items: [
      { to: '/laws', icon: Scale, label: 'Law Explorer' },
      { to: '/news', icon: Newspaper, label: 'Legal News' },
      { to: '/education', icon: BookOpen, label: 'Education' },
      { to: '/stations', icon: MapPin, label: 'Find Stations' },
    ],
  },
  {
    label: 'Personal',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/history', icon: History, label: 'History' },
    ],
  },
];

const Sidebar = ({ open, onClose }) => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleNav = () => {
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(4px)',
              zIndex: 90,
            }}
          />

          {/* Sidebar */}
          <motion.aside
            initial={{ x: -260 }}
            animate={{ x: 0 }}
            exit={{ x: -260 }}
            transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              bottom: 0,
              width: '260px',
              background: 'rgba(8,7,3,0.98)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              borderRight: '1px solid rgba(212,175,55,0.12)',
              zIndex: 101,
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '4px 0 32px rgba(0,0,0,0.6)',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '16px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(212,175,55,0.1)',
            }}>
              <p style={{
                fontFamily: "'Cormorant Garamond', serif",
                fontSize: '1.1rem',
                fontWeight: 700,
                fontStyle: 'italic',
                color: '#D4AF37',
              }}>
                Menu
              </p>
              <button
                onClick={onClose}
                aria-label="Close menu"
                style={{
                  padding: '6px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.06)',
                  background: 'transparent',
                  cursor: 'pointer',
                  color: '#555560',
                  display: 'flex',
                }}
              >
                <X size={14} />
              </button>
            </div>

            {/* Nav */}
            <nav style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}>
              {NAV_SECTIONS.map((section, si) => (
                <div key={section.label}>
                  <p style={{
                    fontSize: '0.6rem',
                    fontWeight: 600,
                    letterSpacing: '2.5px',
                    textTransform: 'uppercase',
                    color: '#3A3A40',
                    padding: '0 8px 8px',
                  }}>
                    {section.label}
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    {section.items.map(({ to, icon: Icon, label }) => (
                      <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        onClick={handleNav}
                        style={({ isActive }) => ({
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          padding: '10px 12px',
                          borderRadius: '10px',
                          textDecoration: 'none',
                          fontSize: '0.83rem',
                          fontWeight: isActive ? 600 : 400,
                          color: isActive ? '#D4AF37' : '#6B6B75',
                          background: isActive
                            ? 'linear-gradient(135deg, rgba(212,175,55,0.14), rgba(212,175,55,0.06))'
                            : 'transparent',
                          border: isActive
                            ? '1px solid rgba(212,175,55,0.2)'
                            : '1px solid transparent',
                          transition: 'all 0.15s ease',
                        })}
                      >
                        <Icon size={15} style={{ flexShrink: 0 }} />
                        <span>{label}</span>
                      </NavLink>
                    ))}
                  </div>
                </div>
              ))}
            </nav>

            {/* Footer */}
            <div style={{
              padding: '14px 12px',
              borderTop: '1px solid rgba(212,175,55,0.1)',
            }}>
              {isAuthenticated ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <button
                    onClick={() => { navigate('/profile'); onClose(); }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px',
                      borderRadius: '10px',
                      border: '1px solid rgba(212,175,55,0.12)',
                      background: 'rgba(212,175,55,0.04)',
                      cursor: 'pointer',
                      width: '100%',
                    }}
                  >
                    <div style={{
                      width: '30px',
                      height: '30px',
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #B8960C, #D4AF37)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      color: '#0B0B0B',
                      flexShrink: 0,
                    }}>
                      {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
                    </div>
                    <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                      <p style={{
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: '#C9A84C',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {user?.full_name || 'Profile'}
                      </p>
                      <p style={{
                        fontSize: '0.66rem',
                        color: '#3A3A40',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {user?.email}
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={() => { logout(); onClose(); }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: '1px solid transparent',
                      background: 'transparent',
                      cursor: 'pointer',
                      fontSize: '0.82rem',
                      color: '#6B4040',
                      width: '100%',
                      transition: 'all 0.15s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = '#ff6b6b';
                      e.currentTarget.style.background = 'rgba(255,100,100,0.06)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = '#6B4040';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <LogOut size={15} />
                    <span>Sign Out</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button
                    onClick={() => { navigate('/login'); onClose(); }}
                    className="btn-gold"
                    style={{ width: '100%' }}
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => { navigate('/register'); onClose(); }}
                    className="btn-ghost"
                    style={{ width: '100%' }}
                  >
                    Create Account
                  </button>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

export default Sidebar;