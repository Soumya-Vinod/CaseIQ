import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6]">
      <div className="bg-white rounded-3xl shadow-2xl p-10 w-full max-w-md space-y-6">

        {/* Logo */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-[#443627]">CaseIQ</h1>
          <p className="text-[#725E54] text-sm">AI-Powered Legal Knowledge Platform</p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <input
            type="email"
            placeholder="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] transition"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] transition"
          />

          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-sm text-[#725E54] hover:text-[#443627]">
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#443627] text-white py-3 rounded-xl hover:bg-[#725E54] transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <hr className="flex-1 border-slate-200" />
          <span className="text-slate-400 text-sm">or</span>
          <hr className="flex-1 border-slate-200" />
        </div>

        {/* Guest */}
        <button
          onClick={() => navigate('/')}
          className="w-full border border-[#A7B0CA] text-[#443627] py-3 rounded-xl hover:bg-[#D5DCF9]/40 transition"
        >
          Continue as Guest
        </button>

        {/* Register */}
        <p className="text-center text-sm text-[#725E54]">
          Don't have an account?{' '}
          <Link to="/register" className="text-[#443627] font-semibold hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;