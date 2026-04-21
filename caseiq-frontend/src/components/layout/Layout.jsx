import Header from "./Header";
import Sidebar from "./Sidebar";
import Footer from "./Footer";
import DisclaimerBar from "./DisclaimerBar";
import { useSettings } from "../../context/SettingsContext";

const Layout = ({ children }) => {
  const { darkMode, fontSize } = useSettings();

  return (
    <div
      style={{
        fontSize: `${fontSize}px`,
        height: '100vh',          /* lock to viewport */
        display: 'flex',
        flexDirection: 'column',
        background: '#0B0B0B',
        color: '#E5E5E5',
        overflow: 'hidden',       /* nothing on the outer shell scrolls */
        position: 'relative',
      }}
    >
      {/* Global radial gold glow */}
      <div style={{
        position: 'fixed',
        inset: 0,
        background: 'radial-gradient(ellipse at 50% -10%, rgba(212,175,55,0.09) 0%, transparent 60%)',
        pointerEvents: 'none',
        zIndex: 0,
      }} />

      {/* ── HEADER ── fixed height, never scrolls */}
      <div style={{ flexShrink: 0, position: 'relative', zIndex: 40 }}>
        <Header />
      </div>

      {/* ── BODY ROW ── fills the remaining height */}
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',       /* children handle their own scroll */
        position: 'relative',
        zIndex: 1,
      }}>

        {/* ── SIDEBAR ── fills full body height, never scrolls away */}
        <div style={{
          flexShrink: 0,
          height: '100%',
          overflowY: 'auto',
          overflowX: 'hidden',
        }}>
          <Sidebar />
        </div>

        {/* ── MAIN CONTENT ── only this panel scrolls */}
        <main style={{
          flex: 1,
          height: '100%',
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '32px',
          background: 'transparent',
        }}>
          {children}

          {/* Footer appears at the natural bottom of page content */}
          <div style={{ marginTop: '64px' }}>
            <DisclaimerBar />
            <Footer />
          </div>
        </main>

      </div>
    </div>
  );
};

export default Layout;
