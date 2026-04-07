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
    <header className={`sticky top-0 z-40 transition-all duration-300 ${
      darkMode
        ? 'bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700'
        : 'bg-gradient-to-r from-[#D5DCF9] via-[#A7B0CA] to-[#D5DCF9] border-b border-[#A7B0CA]'
    }`}>
      <div className="px-6 py-2 flex justify-between items-center gap-4">

        {/* Logo */}
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-2 cursor-pointer group shrink-0"
        >
          <img
            src={logo}
            alt="CaseIQ"
            className="h-16 w-auto object-contain group-hover:scale-105 transition-transform duration-300 drop-shadow-lg"
          />
        </div>

        {/* Global Search — center */}
        <div className="flex-1 flex justify-center max-w-md">
          <GlobalSearch />
        </div>

        {/* Right Side */}
        <div className="flex items-center gap-2 shrink-0">
          {user && (
            <div
              onClick={() => navigate('/profile')}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition"
            >
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center shadow text-[#443627] font-bold text-xs">
                {(user.full_name || user.email || 'U')[0].toUpperCase()}
              </div>
              <span className={`text-sm hidden md:block font-medium ${
                darkMode ? 'text-slate-300' : 'text-[#443627]'
              }`}>
                {user.full_name || user.email}
              </span>
            </div>
          )}

          <button
            onClick={() => navigate('/settings')}
            className="p-2 rounded-lg hover:bg-white/30 transition"
          >
            <Settings size={16} className={darkMode ? 'text-white' : 'text-[#443627]'} />
          </button>

          {user && (
            <button
              onClick={logout}
              className="p-2 rounded-lg hover:bg-red-200/40 transition"
            >
              <LogOut size={16} className="text-red-500" />
            </button>
          )}

          {!user && (
            <button
              onClick={() => navigate('/login')}
              className="bg-[#443627] text-white px-4 py-1.5 rounded-xl text-sm hover:bg-[#725E54] transition font-medium shadow"
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      <div className={`h-px ${
        darkMode
          ? 'bg-gradient-to-r from-transparent via-slate-500 to-transparent opacity-40'
          : 'bg-gradient-to-r from-transparent via-[#725E54] to-transparent opacity-20'
      }`} />
    </header>
  );
};

export default Header;