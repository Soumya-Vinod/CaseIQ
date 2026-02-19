import Header from "./Header";
import Sidebar from "./Sidebar";
import Footer from "./Footer";
import DisclaimerBar from "./DisclaimerBar";
import { useSettings } from "../../context/SettingsContext";

const Layout = ({ children }) => {
  const { darkMode, fontSize } = useSettings();

  return (
    <div
      style={{ fontSize: `${fontSize}px` }}
      className={`
        min-h-screen
        flex flex-col
        transition-colors duration-300
        ${darkMode ? "bg-slate-900 text-slate-200" : "bg-slate-50 text-slate-800"}
      `}
    >
      {/* HEADER */}
      <Header />

      {/* MAIN LAYOUT AREA */}
      <div className="flex flex-1 overflow-hidden">

        {/* SIDEBAR */}
        <Sidebar />

        {/* SCROLLABLE CONTENT AREA */}
        <main
          className={`
            flex-1
            overflow-y-auto
            p-8
            transition-colors duration-300
            ${darkMode ? "bg-slate-800" : "bg-slate-100"}
          `}
        >
          {children}
        </main>

      </div>

      {/* Optional Footer / Disclaimer */}
      <DisclaimerBar />
      <Footer />
    </div>
  );
};

export default Layout;
