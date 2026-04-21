import { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';
import PageTransition from '../components/ui/PageTransition';
import toast from 'react-hot-toast';

const ProfilePage = () => {
  const { user, updateUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    phone: user?.phone || '',
    state: user?.state || '',
    district: user?.district || '',
    preferred_language: user?.preferred_language || 'en',
  });
  const [passwords, setPasswords] = useState({ old_password: '', new_password: '', confirm: '' });

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await authAPI.updateProfile(formData);
      updateUser(res.data);
      toast.success('Profile updated successfully!');
      setEditing(false);
    } catch {
      toast.error('Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (passwords.new_password !== passwords.confirm) {
      toast.error('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await authAPI.changePassword({ old_password: passwords.old_password, new_password: passwords.new_password });
      toast.success('Password changed successfully!');
      setPasswords({ old_password: '', new_password: '', confirm: '' });
    } catch {
      toast.error('Incorrect current password.');
    } finally {
      setLoading(false);
    }
  };

  const baseInputStyle = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: '10px',
    fontFamily: 'system-ui, sans-serif',
    fontSize: '14px',
    outline: 'none',
    transition: 'all 0.2s',
    boxSizing: 'border-box',
  };

  const activeInputStyle = {
    ...baseInputStyle,
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(212,175,55,0.3)',
    color: '#E5E5E5',
  };

  const disabledInputStyle = {
    ...baseInputStyle,
    background: 'rgba(255,255,255,0.02)',
    border: '1px solid rgba(255,255,255,0.06)',
    color: '#71717A',
    cursor: 'not-allowed',
  };

  const handleInputFocus = (e) => {
    e.target.style.borderColor = '#D4AF37';
    e.target.style.boxShadow = '0 0 0 3px rgba(212,175,55,0.15)';
  };
  const handleInputBlur = (e) => {
    e.target.style.borderColor = 'rgba(212,175,55,0.3)';
    e.target.style.boxShadow = 'none';
  };

  const cardStyle = {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: '20px',
    padding: '36px',
    backdropFilter: 'blur(12px)',
    boxShadow: '0 8px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(212,175,55,0.08)',
    position: 'relative',
    overflow: 'hidden',
  };

  return (
    <PageTransition>
      <div className="max-w-3xl mx-auto space-y-8 pb-16">

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: '80px', height: '80px', borderRadius: '50%',
            background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 32px rgba(212,175,55,0.45), 0 0 0 3px rgba(212,175,55,0.2)',
            flexShrink: 0,
          }}>
            <span style={{ fontSize: '32px', fontWeight: '800', color: '#0B0B0B', fontFamily: "'Georgia', serif" }}>
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </span>
          </div>
          <div>
            <h1 style={{
              fontSize: '28px', fontWeight: '800',
              fontFamily: "'Georgia', 'Times New Roman', serif",
              background: 'linear-gradient(135deg, #D4AF37, #FFD700)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              marginBottom: '4px',
            }}>{user?.full_name || 'Your Profile'}</h1>
            <p style={{ color: '#A1A1AA', fontSize: '14px', fontFamily: 'system-ui, sans-serif', marginBottom: '8px' }}>
              {user?.email}
            </p>
            <span style={{
              fontSize: '11px',
              background: 'rgba(212,175,55,0.15)',
              color: '#D4AF37',
              padding: '4px 12px',
              borderRadius: '20px',
              border: '1px solid rgba(212,175,55,0.3)',
              fontWeight: '600',
              fontFamily: 'system-ui, sans-serif',
              textTransform: 'capitalize',
            }}>
              {user?.role || 'citizen'}
            </span>
          </div>
        </div>

        {/* Profile Form */}
        <div style={cardStyle}>
          {/* Top accent line */}
          <div style={{ position: 'absolute', top: 0, left: '10%', right: '10%', height: '1px', background: 'linear-gradient(90deg, transparent, #D4AF37, transparent)' }} />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#E5E5E5', fontFamily: "'Georgia', 'Times New Roman', serif" }}>
              Personal Information
            </h2>
            <button
              onClick={() => setEditing(!editing)}
              style={{
                fontSize: '13px',
                color: editing ? '#A1A1AA' : '#D4AF37',
                background: 'transparent',
                border: `1px solid ${editing ? 'rgba(255,255,255,0.1)' : 'rgba(212,175,55,0.3)'}`,
                padding: '7px 16px',
                borderRadius: '10px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontFamily: 'system-ui, sans-serif',
                fontWeight: '500',
              }}
              onMouseEnter={e => { e.target.style.background = 'rgba(212,175,55,0.08)'; }}
              onMouseLeave={e => { e.target.style.background = 'transparent'; }}
            >
              {editing ? 'Cancel' : '✏️ Edit'}
            </button>
          </div>

          <form onSubmit={handleUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#C5A46D', marginBottom: '6px', fontFamily: 'system-ui, sans-serif', letterSpacing: '0.5px', textTransform: 'uppercase' }}>Full Name</label>
                <input
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  disabled={!editing}
                  style={editing ? activeInputStyle : disabledInputStyle}
                  onFocus={editing ? handleInputFocus : undefined}
                  onBlur={editing ? handleInputBlur : undefined}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#C5A46D', marginBottom: '6px', fontFamily: 'system-ui, sans-serif', letterSpacing: '0.5px', textTransform: 'uppercase' }}>Phone</label>
                <input
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  disabled={!editing}
                  style={editing ? activeInputStyle : disabledInputStyle}
                  onFocus={editing ? handleInputFocus : undefined}
                  onBlur={editing ? handleInputBlur : undefined}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#C5A46D', marginBottom: '6px', fontFamily: 'system-ui, sans-serif', letterSpacing: '0.5px', textTransform: 'uppercase' }}>State</label>
                <input
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  disabled={!editing}
                  style={editing ? activeInputStyle : disabledInputStyle}
                  onFocus={editing ? handleInputFocus : undefined}
                  onBlur={editing ? handleInputBlur : undefined}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#C5A46D', marginBottom: '6px', fontFamily: 'system-ui, sans-serif', letterSpacing: '0.5px', textTransform: 'uppercase' }}>District</label>
                <input
                  value={formData.district}
                  onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                  disabled={!editing}
                  style={editing ? activeInputStyle : disabledInputStyle}
                  onFocus={editing ? handleInputFocus : undefined}
                  onBlur={editing ? handleInputBlur : undefined}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: '#C5A46D', marginBottom: '6px', fontFamily: 'system-ui, sans-serif', letterSpacing: '0.5px', textTransform: 'uppercase' }}>Preferred Language</label>
              <select
                value={formData.preferred_language}
                onChange={(e) => setFormData({ ...formData, preferred_language: e.target.value })}
                disabled={!editing}
                style={editing ? { ...activeInputStyle, cursor: 'pointer' } : { ...disabledInputStyle }}
                onFocus={editing ? handleInputFocus : undefined}
                onBlur={editing ? handleInputBlur : undefined}
              >
                <option value="en" style={{ background: '#111111' }}>English</option>
                <option value="hi" style={{ background: '#111111' }}>Hindi</option>
                <option value="mr" style={{ background: '#111111' }}>Marathi</option>
                <option value="ta" style={{ background: '#111111' }}>Tamil</option>
                <option value="te" style={{ background: '#111111' }}>Telugu</option>
              </select>
            </div>

            {editing && (
              <motion.button
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
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
                }}
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </motion.button>
            )}
          </form>
        </div>

        {/* Change Password */}
        <div style={{ ...cardStyle }}>
          <div style={{ position: 'absolute', top: 0, left: '10%', right: '10%', height: '1px', background: 'linear-gradient(90deg, transparent, rgba(197,164,109,0.6), transparent)' }} />

          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#E5E5E5', fontFamily: "'Georgia', 'Times New Roman', serif", marginBottom: '24px' }}>
            Change Password
          </h2>
          <form onSubmit={handlePasswordChange} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {[
              { placeholder: 'Current Password', key: 'old_password' },
              { placeholder: 'New Password', key: 'new_password' },
              { placeholder: 'Confirm New Password', key: 'confirm' },
            ].map(({ placeholder, key }) => (
              <input
                key={key}
                type="password"
                placeholder={placeholder}
                value={passwords[key]}
                onChange={(e) => setPasswords({ ...passwords, [key]: e.target.value })}
                required
                style={activeInputStyle}
                onFocus={handleInputFocus}
                onBlur={handleInputBlur}
              />
            ))}
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '13px 32px',
                background: loading ? 'rgba(212,175,55,0.4)' : 'linear-gradient(135deg, #D4AF37, #FFD700)',
                border: 'none',
                borderRadius: '12px',
                color: '#0B0B0B',
                fontWeight: '700',
                fontSize: '14px',
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: loading ? 'none' : '0 4px 20px rgba(212,175,55,0.35)',
                fontFamily: 'system-ui, sans-serif',
                alignSelf: 'flex-start',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { if (!loading) { e.target.style.boxShadow = '0 6px 28px rgba(212,175,55,0.55)'; e.target.style.transform = 'translateY(-1px)'; }}}
              onMouseLeave={e => { e.target.style.boxShadow = '0 4px 20px rgba(212,175,55,0.35)'; e.target.style.transform = 'translateY(0)'; }}
            >
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>

      </div>
    </PageTransition>
  );
};

export default ProfilePage;
