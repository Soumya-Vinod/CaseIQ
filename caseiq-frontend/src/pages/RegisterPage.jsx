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
      const msg = data ? Object.values(data).flat().join(' ') : 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '13px 14px',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: '10px',
    color: '#E5E5E5',
    outline: 'none',
    fontFamily: 'system-ui, sans-serif',
    fontSize: '14px',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    boxSizing: 'border-box',
  };

  const handleFocus = (e) => {
    e.target.style.borderColor = '#D4AF37';
    e.target.style.boxShadow = '0 0 0 3px rgba(212,175,55,0.12)';
  };
  const handleBlur = (e) => {
    e.target.style.borderColor = 'rgba(212,175,55,0.2)';
    e.target.style.boxShadow = 'none';
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(ellipse at 50% 0%, rgba(212,175,55,0.1) 0%, #0B0B0B 55%)',
      padding: '32px 20px',
    }}>
      {/* Decorative background glow */}
      <div style={{
        position: 'fixed', top: '-150px', left: '50%', transform: 'translateX(-50%)',
        width: '700px', height: '700px',
        background: 'radial-gradient(circle, rgba(212,175,55,0.06) 0%, transparent 65%)',
        pointerEvents: 'none',
      }} />

      <div style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(212,175,55,0.22)',
        borderRadius: '24px',
        padding: '44px',
        width: '100%',
        maxWidth: '500px',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 32px 80px rgba(0,0,0,0.6), inset 0 1px 0 rgba(212,175,55,0.12)',
        position: 'relative',
      }}>
        {/* Top gold line */}
        <div style={{
          position: 'absolute', top: 0, left: '15%', right: '15%', height: '1px',
          background: 'linear-gradient(90deg, transparent, #D4AF37, transparent)',
        }} />

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '16px',
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 28px rgba(212,175,55,0.4)',
            margin: '0 auto 16px',
            fontSize: '26px',
          }}>⚖️</div>
          <h1 style={{
            fontSize: '28px', fontWeight: '800',
            fontFamily: "'Georgia', 'Times New Roman', serif",
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            marginBottom: '6px',
          }}>Create Account</h1>
          <p style={{ color: '#A1A1AA', fontSize: '13px', fontFamily: 'system-ui, sans-serif' }}>
            Join CaseIQ — Free Legal Knowledge for All
          </p>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.3)',
            color: '#FCA5A5',
            fontSize: '13px',
            borderRadius: '10px',
            padding: '12px 16px',
            marginBottom: '20px',
            fontFamily: 'system-ui, sans-serif',
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="grid grid-cols-2 gap-3">
            <input name="full_name" placeholder="Full Name *" value={formData.full_name} onChange={handleChange} required
              style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />
            <input name="phone" placeholder="Phone Number" value={formData.phone} onChange={handleChange}
              style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />
          </div>

          <input name="email" type="email" placeholder="Email Address *" value={formData.email} onChange={handleChange} required
            style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />

          <div className="grid grid-cols-2 gap-3">
            <input name="password" type="password" placeholder="Password *" value={formData.password} onChange={handleChange} required
              style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />
            <input name="password2" type="password" placeholder="Confirm Password *" value={formData.password2} onChange={handleChange} required
              style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <input name="state" placeholder="State" value={formData.state} onChange={handleChange}
              style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />
            <input name="district" placeholder="District" value={formData.district} onChange={handleChange}
              style={inputStyle} onFocus={handleFocus} onBlur={handleBlur} />
          </div>

          <select name="preferred_language" value={formData.preferred_language} onChange={handleChange}
            style={{ ...inputStyle, cursor: 'pointer' }} onFocus={handleFocus} onBlur={handleBlur}>
            <option value="en" style={{ background: '#111111' }}>English</option>
            <option value="hi" style={{ background: '#111111' }}>Hindi</option>
            <option value="mr" style={{ background: '#111111' }}>Marathi</option>
            <option value="ta" style={{ background: '#111111' }}>Tamil</option>
            <option value="te" style={{ background: '#111111' }}>Telugu</option>
          </select>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '14px',
              background: loading ? 'rgba(212,175,55,0.4)' : 'linear-gradient(135deg, #D4AF37, #FFD700)',
              border: 'none',
              borderRadius: '12px',
              color: '#0B0B0B',
              fontWeight: '700',
              fontSize: '15px',
              cursor: loading ? 'not-allowed' : 'pointer',
              boxShadow: loading ? 'none' : '0 4px 20px rgba(212,175,55,0.4)',
              fontFamily: 'system-ui, sans-serif',
              transition: 'all 0.2s',
              marginTop: '4px',
              letterSpacing: '0.3px',
            }}
            onMouseEnter={e => { if (!loading) { e.target.style.boxShadow = '0 8px 32px rgba(212,175,55,0.6)'; e.target.style.transform = 'translateY(-1px)'; }}}
            onMouseLeave={e => { e.target.style.boxShadow = '0 4px 20px rgba(212,175,55,0.4)'; e.target.style.transform = 'translateY(0)'; }}
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p style={{ textAlign: 'center', fontSize: '13px', color: '#A1A1AA', marginTop: '24px', fontFamily: 'system-ui, sans-serif' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: '#D4AF37', fontWeight: '600', textDecoration: 'none' }}
            onMouseEnter={e => e.target.style.textDecoration = 'underline'}
            onMouseLeave={e => e.target.style.textDecoration = 'none'}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
