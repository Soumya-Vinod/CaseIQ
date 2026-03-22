import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('caseiq_access_token');
    const savedUser = localStorage.getItem('caseiq_user');
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
        // Verify token is still valid
        authAPI.getProfile()
          .then((res) => setUser(res.data))
          .catch(() => {
            localStorage.removeItem('caseiq_access_token');
            localStorage.removeItem('caseiq_refresh_token');
            localStorage.removeItem('caseiq_user');
            setUser(null);
          });
      } catch {
        setUser(null);
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const data = await authAPI.login(email, password);
    setUser(data.user);
    return data;
  };

  const register = async (formData) => {
    const res = await authAPI.register(formData);
    localStorage.setItem('caseiq_access_token', res.data.tokens.access);
    localStorage.setItem('caseiq_refresh_token', res.data.tokens.refresh);
    localStorage.setItem('caseiq_user', JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data;
  };

  const logout = async () => {
    await authAPI.logout();
    setUser(null);
  };

  const updateUser = (userData) => {
    setUser(userData);
    localStorage.setItem('caseiq_user', JSON.stringify(userData));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, register, updateUser, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);