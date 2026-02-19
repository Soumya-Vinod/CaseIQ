import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useSettings } from "../../context/SettingsContext";
import { Settings, LogOut, User } from "lucide-react";

const Header = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { darkMode } = useSettings();

  return (
    <header
      className={`
        sticky top-0 z-50
        transition-all duration-300
        ${
          darkMode
            ? "bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700"
            : "bg-gradient-to-r from-[#D5DCF9] via-[#A7B0CA] to-[#D5DCF9] border-b border-[#A7B0CA]"
        }
      `}
    >
      <div className="px-10 py-4 flex justify-between items-center">

        {/* LOGO */}
        <div
          onClick={() => navigate("/")}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div
            className="
              w-9 h-9 rounded-xl
              bg-white/30 dark:bg-white/10
              backdrop-blur-md
              flex items-center justify-center
              shadow-md
              group-hover:scale-105
              transition
            "
          >
            <span className="font-bold text-[#443627] dark:text-white">
              C
            </span>
          </div>

          <h1
            className={`
              text-2xl font-semibold tracking-tight
              ${
                darkMode
                  ? "text-white"
                  : "text-[#443627]"
              }
            `}
          >
            CaseIQ
          </h1>
        </div>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-6">

          {user && (
            <div className="flex items-center gap-3">
              <div
                className="
                  w-9 h-9 rounded-full
                  bg-white/30 dark:bg-white/10
                  backdrop-blur-md
                  flex items-center justify-center
                  shadow
                "
              >
                <User size={16} className="text-[#443627] dark:text-white" />
              </div>

              <span className="text-sm text-[#443627] dark:text-slate-300 hidden sm:block">
                {user.email}
              </span>
            </div>
          )}

          {/* SETTINGS */}
          <button
            onClick={() => navigate("/settings")}
            className="
              p-2 rounded-lg
              hover:bg-white/30
              dark:hover:bg-white/10
              transition
            "
          >
            <Settings size={18} className="text-[#443627] dark:text-white" />
          </button>

          {/* LOGOUT */}
          {user && (
            <button
              onClick={logout}
              className="
                p-2 rounded-lg
                hover:bg-red-200/40
                dark:hover:bg-red-500/20
                transition
              "
            >
              <LogOut size={18} className="text-red-600 dark:text-red-400" />
            </button>
          )}

        </div>
      </div>

      {/* Soft Divider Glow */}
      <div
        className={`
          h-[2px]
          ${
            darkMode
              ? "bg-gradient-to-r from-transparent via-slate-500 to-transparent opacity-40"
              : "bg-gradient-to-r from-transparent via-[#725E54] to-transparent opacity-30"
          }
        `}
      />
    </header>
  );
};

export default Header;
