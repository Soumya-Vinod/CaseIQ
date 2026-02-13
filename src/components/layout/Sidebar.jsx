import { NavLink } from "react-router-dom";
import { useSettings } from "../../context/SettingsContext";
import {
  Home,
  MessageCircle,
  FileText,
  LayoutDashboard,
  BookOpen,
  History,
} from "lucide-react";

const Sidebar = () => {
  const { darkMode } = useSettings();

  const baseStyle =
    "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium";

  const iconStyle = "w-4 h-4";

  return (
    <aside
      className={`
        w-64
        h-full
        sticky top-0
        p-6 space-y-2
        border-r
        backdrop-blur-xl
        transition-all duration-300
        ${
          darkMode
            ? "bg-slate-900/70 border-slate-700/60"
            : "bg-white/70 border-slate-200/60"
        }
      `}
    >
      {/* Navigation Title */}
      <div className="mb-6 text-xs uppercase tracking-wider text-slate-500">
        Navigation
      </div>

      {/* HOME */}
      <NavLink
        to="/"
        className={({ isActive }) =>
          `${baseStyle} ${
            isActive
              ? "bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md"
              : darkMode
              ? "text-slate-300 hover:bg-slate-800/60"
              : "text-slate-700 hover:bg-[#D5DCF9]/40"
          }`
        }
      >
        <Home className={iconStyle} />
        Home
      </NavLink>

      {/* CHAT */}
      <NavLink
        to="/chat"
        className={({ isActive }) =>
          `${baseStyle} ${
            isActive
              ? "bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md"
              : darkMode
              ? "text-slate-300 hover:bg-slate-800/60"
              : "text-slate-700 hover:bg-[#D5DCF9]/40"
          }`
        }
      >
        <MessageCircle className={iconStyle} />
        AI Assistant
      </NavLink>

      {/* FIR */}
      <NavLink
        to="/fir-draft"
        className={({ isActive }) =>
          `${baseStyle} ${
            isActive
              ? "bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md"
              : darkMode
              ? "text-slate-300 hover:bg-slate-800/60"
              : "text-slate-700 hover:bg-[#D5DCF9]/40"
          }`
        }
      >
        <FileText className={iconStyle} />
        FIR Draft
      </NavLink>

      {/* DASHBOARD */}
      <NavLink
        to="/dashboard"
        className={({ isActive }) =>
          `${baseStyle} ${
            isActive
              ? "bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md"
              : darkMode
              ? "text-slate-300 hover:bg-slate-800/60"
              : "text-slate-700 hover:bg-[#D5DCF9]/40"
          }`
        }
      >
        <LayoutDashboard className={iconStyle} />
        Dashboard
      </NavLink>

      {/* EDUCATION */}
      <NavLink
        to="/education"
        className={({ isActive }) =>
          `${baseStyle} ${
            isActive
              ? "bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md"
              : darkMode
              ? "text-slate-300 hover:bg-slate-800/60"
              : "text-slate-700 hover:bg-[#D5DCF9]/40"
          }`
        }
      >
        <BookOpen className={iconStyle} />
        Education
      </NavLink>

      {/* HISTORY */}
      <NavLink
        to="/history"
        className={({ isActive }) =>
          `${baseStyle} ${
            isActive
              ? "bg-gradient-to-r from-[#8EDCE6] to-[#D5DCF9] text-[#443627] shadow-md"
              : darkMode
              ? "text-slate-300 hover:bg-slate-800/60"
              : "text-slate-700 hover:bg-[#D5DCF9]/40"
          }`
        }
      >
        <History className={iconStyle} />
        History
      </NavLink>
    </aside>
  );
};

export default Sidebar;
