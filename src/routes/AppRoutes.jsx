import { Routes, Route } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

import Layout from "../components/layout/Layout";

import HomePage from "../pages/HomePage";
import ChatPage from "../pages/ChatPage";
import FIRDraftPage from "../pages/FIRDraftPage";
import DashboardPage from "../pages/DashboardPage";
import EducationPage from "../pages/EducationPage";
import HistoryPage from "../pages/HistoryPage";
import SettingsPage from "../pages/SettingsPage";
import LoginPage from "../pages/LoginPage";

const AppRoutes = () => {
  const { user } = useAuth();

  if (!user) {
    return <LoginPage />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/fir-draft" element={<FIRDraftPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/education" element={<EducationPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
};

export default AppRoutes;
