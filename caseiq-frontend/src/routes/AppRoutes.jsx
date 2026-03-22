import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/layout/Layout';
import HomePage from '../pages/HomePage';
import ChatPage from '../pages/ChatPage';
import FIRDraftPage from '../pages/FIRDraftPage';
import DashboardPage from '../pages/DashboardPage';
import EducationPage from '../pages/EducationPage';
import HistoryPage from '../pages/HistoryPage';
import SettingsPage from '../pages/SettingsPage';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import NewsPage from '../pages/NewsPage';
import LawExplorerPage from '../pages/LawExplorerPage';
import ProfilePage from '../pages/ProfilePage';
import NotFoundPage from '../pages/NotFoundPage';

const AppRoutes = () => {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={!user ? <LoginPage /> : <Navigate to="/" />} />
      <Route path="/register" element={!user ? <RegisterPage /> : <Navigate to="/" />} />
      <Route path="/*" element={
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/fir-draft" element={<FIRDraftPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/education" element={<EducationPage />} />
            <Route path="/news" element={<NewsPage />} />
            <Route path="/laws" element={<LawExplorerPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/profile" element={user ? <ProfilePage /> : <Navigate to="/login" />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Layout>
      } />
    </Routes>
  );
};

export default AppRoutes;