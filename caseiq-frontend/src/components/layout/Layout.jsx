import { useState } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';
import { useSettings } from '../../context/SettingsContext';

const Layout = ({ children }) => {
  const { fontSize } = useSettings();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="page-shell" style={{ fontSize: `${fontSize}px`, minHeight: '100vh' }}>
      <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} sidebarOpen={sidebarOpen} />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main style={{
        position: 'relative',
        zIndex: 1,
        minHeight: 'calc(100vh - 60px)',
      }}>
        {children}
      </main>
      <Footer />
    </div>
  );
};

export default Layout;