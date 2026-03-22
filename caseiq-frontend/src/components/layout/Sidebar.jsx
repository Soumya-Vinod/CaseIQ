import { NavLink, useNavigate } from 'react-router-dom';
import { useSettings } from '../../context/SettingsContext';
import { useAuth } from '../../context/AuthContext';
import {
  Home, MessageCircle, FileText, LayoutDashboard,
  BookOpen, History, Newspaper, Scale, Settings,
  LogOut, User, ChevronRight,
} from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = () => {
  const { darkMode } = useSettings();
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const baseStyle = 'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm';
  const iconStyle = 'w-4 h-4 shrink-0';

  const navClass = ({ isActive }) =>
    `${baseStyle} ${isActive
      ? 'bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md font-semibold'
      : darkMode
      ? 'text-slate-300 hover:bg-slate-800/60'
      : 'text-slate-600 hover:bg-[#D5DCF9]/50 hover:text-[#443627]'
    }`;

  const navItems = [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/chat', icon: MessageCircle, label: 'AI Assistant' },
    { to: '/fir-draft', icon: FileText, label: 'FIR Draft' },
    { to: '/laws', icon: Scale, label: 'Law Explorer' },
    { to: '/news', icon: Newspaper, label: 'Legal News' },
    { to: '/education', icon: BookOpen, label: 'Education' },
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/history', icon: History, label: 'History' },
  ];

  return (
    <aside className={`w-64 min-h-screen sticky top-0 flex flex-col p-5 border-r transition-all duration-300 ${
      darkMode ? 'bg-slate-900/90 border-slate-700/60' : 'bg-white/80 border-slate-200/60'
    } backdrop-blur-xl`}>

      {/* Nav Links */}
      <div className="flex-1 space-y-1">
        <p className="text-xs uppercase tracking-widest text-slate-400 px-4 mb-4 font-medium">
          Menu
        </p>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'} className={navClass}>
            {({ isActive }) => (
              <>
                <Icon className={iconStyle} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight className="w-3 h-3 opacity-60" />}
              </>
            )}
          </NavLink>
        ))}
      </div>

      {/* Divider */}
      <div className={`my-4 border-t ${darkMode ? 'border-slate-700' : 'border-slate-200'}`} />

      {/* User Profile Section */}
      {isAuthenticated ? (
        <div className="space-y-2">
          <motion.div
            whileHover={{ scale: 1.02 }}
            onClick={() => navigate('/profile')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition ${
              darkMode ? 'hover:bg-slate-800' : 'hover:bg-[#D5DCF9]/50'
            }`}
          >
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center shadow-md shrink-0">
              <span className="text-[#443627] font-bold text-sm">
                {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold truncate ${darkMode ? 'text-white' : 'text-[#443627]'}`}>
                {user?.full_name || 'User'}
              </p>
              <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            </div>
          </motion.div>

          <NavLink to="/settings" className={navClass}>
            <Settings className={iconStyle} /> Settings
          </NavLink>

          <button
            onClick={logout}
            className={`w-full ${baseStyle} text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10`}
          >
            <LogOut className={iconStyle} /> Sign Out
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <button
            onClick={() => navigate('/login')}
            className="w-full bg-[#443627] text-white px-4 py-3 rounded-xl hover:bg-[#725E54] transition text-sm font-medium"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/register')}
            className="w-full border border-[#A7B0CA] text-[#443627] px-4 py-3 rounded-xl hover:bg-[#D5DCF9]/40 transition text-sm font-medium"
          >
            Create Account
          </button>
        </div>
      )}
    </aside>
  );
};

export default Sidebar;