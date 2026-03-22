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
      await authAPI.changePassword({
        old_password: passwords.old_password,
        new_password: passwords.new_password,
      });
      toast.success('Password changed successfully!');
      setPasswords({ old_password: '', new_password: '', confirm: '' });
    } catch {
      toast.error('Incorrect current password.');
    } finally {
      setLoading(false);
    }
  };

  const inputClass = 'w-full rounded-xl p-3 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#8EDCE6] bg-white transition';

  return (
    <PageTransition>
      <div className="max-w-3xl mx-auto space-y-8 pb-16">

        {/* Header */}
        <div className="flex items-center gap-5">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center shadow-xl">
            <span className="text-3xl font-bold text-[#443627]">
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </span>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-[#443627]">{user?.full_name || 'Your Profile'}</h1>
            <p className="text-[#725E54]">{user?.email}</p>
            <span className="text-xs bg-[#D5DCF9] text-[#443627] px-2 py-1 rounded-full font-medium mt-1 inline-block capitalize">
              {user?.role || 'citizen'}
            </span>
          </div>
        </div>

        {/* Profile Form */}
        <div className="bg-white rounded-3xl p-8 shadow border border-[#D5DCF9] space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold text-[#443627]">Personal Information</h2>
            <button
              onClick={() => setEditing(!editing)}
              className="text-sm text-[#725E54] hover:text-[#443627] border border-[#A7B0CA] px-4 py-1.5 rounded-xl transition"
            >
              {editing ? 'Cancel' : '✏️ Edit'}
            </button>
          </div>

          <form onSubmit={handleUpdate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#443627] mb-1">Full Name</label>
                <input
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  disabled={!editing}
                  className={`${inputClass} disabled:bg-slate-50 disabled:text-slate-500`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#443627] mb-1">Phone</label>
                <input
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  disabled={!editing}
                  className={`${inputClass} disabled:bg-slate-50 disabled:text-slate-500`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#443627] mb-1">State</label>
                <input
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  disabled={!editing}
                  className={`${inputClass} disabled:bg-slate-50 disabled:text-slate-500`}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#443627] mb-1">District</label>
                <input
                  value={formData.district}
                  onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                  disabled={!editing}
                  className={`${inputClass} disabled:bg-slate-50 disabled:text-slate-500`}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#443627] mb-1">Preferred Language</label>
              <select
                value={formData.preferred_language}
                onChange={(e) => setFormData({ ...formData, preferred_language: e.target.value })}
                disabled={!editing}
                className={`${inputClass} disabled:bg-slate-50 disabled:text-slate-500`}
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="mr">Marathi</option>
                <option value="ta">Tamil</option>
                <option value="te">Telugu</option>
              </select>
            </div>

            {editing && (
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                type="submit"
                disabled={loading}
                className="w-full bg-[#443627] text-white py-3 rounded-xl hover:bg-[#725E54] transition font-medium shadow disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </motion.button>
            )}
          </form>
        </div>

        {/* Change Password */}
        <div className="bg-white rounded-3xl p-8 shadow border border-[#D5DCF9] space-y-5">
          <h2 className="text-xl font-semibold text-[#443627]">Change Password</h2>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <input
              type="password"
              placeholder="Current Password"
              value={passwords.old_password}
              onChange={(e) => setPasswords({ ...passwords, old_password: e.target.value })}
              required
              className={inputClass}
            />
            <input
              type="password"
              placeholder="New Password"
              value={passwords.new_password}
              onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
              required
              className={inputClass}
            />
            <input
              type="password"
              placeholder="Confirm New Password"
              value={passwords.confirm}
              onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}
              required
              className={inputClass}
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-[#443627] text-white px-8 py-3 rounded-xl hover:bg-[#725E54] transition font-medium shadow disabled:opacity-50"
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