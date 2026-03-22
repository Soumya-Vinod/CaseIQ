import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const RegisterPage = () => {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    password2: '',
    preferred_language: 'en',
    state: '',
    district: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (formData.password !== formData.password2) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await register(formData);
      navigate('/');
    } catch (err) {
      const data = err.response?.data;
      const msg = data
        ? Object.values(data).flat().join(' ')
        : 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6] py-10">
      <div className="bg-white rounded-3xl shadow-2xl p-10 w-full max-w-lg space-y-6">

        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-[#443627]">Create Account</h1>
          <p className="text-[#725E54] text-sm">Join CaseIQ — Free Legal Knowledge for All</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <input name="full_name" placeholder="Full Name *" value={formData.full_name} onChange={handleChange} required
              className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />
            <input name="phone" placeholder="Phone Number" value={formData.phone} onChange={handleChange}
              className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />
          </div>

          <input name="email" type="email" placeholder="Email Address *" value={formData.email} onChange={handleChange} required
            className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />

          <div className="grid grid-cols-2 gap-4">
            <input name="password" type="password" placeholder="Password *" value={formData.password} onChange={handleChange} required
              className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />
            <input name="password2" type="password" placeholder="Confirm Password *" value={formData.password2} onChange={handleChange} required
              className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <input name="state" placeholder="State" value={formData.state} onChange={handleChange}
              className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />
            <input name="district" placeholder="District" value={formData.district} onChange={handleChange}
              className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]" />
          </div>

          <select name="preferred_language" value={formData.preferred_language} onChange={handleChange}
            className="w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6]">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="mr">Marathi</option>
            <option value="ta">Tamil</option>
            <option value="te">Telugu</option>
          </select>

          <button type="submit" disabled={loading}
            className="w-full bg-[#443627] text-white py-3 rounded-xl hover:bg-[#725E54] transition disabled:opacity-50">
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-sm text-[#725E54]">
          Already have an account?{' '}
          <Link to="/login" className="text-[#443627] font-semibold hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;