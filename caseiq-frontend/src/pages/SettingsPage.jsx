import { useSettings } from '../context/SettingsContext';
import { useAuth } from '../context/AuthContext';
import PageTransition from '../components/ui/PageTransition';
import { Moon, Sun, Type, Globe, Bell, Shield, Info } from 'lucide-react';
import { motion } from 'framer-motion';

const SettingsSection = ({ title, icon: Icon, children, darkMode }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    className={`rounded-2xl p-6 border shadow-sm ${
      darkMode
        ? 'bg-slate-800/60 border-slate-700/60'
        : 'bg-white border-[#D5DCF9]'
    }`}
  >
    <div className="flex items-center gap-3 mb-5">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#8EDCE6] to-[#D5DCF9] flex items-center justify-center">
        <Icon size={15} className="text-[#443627]" />
      </div>
      <h2 className={`font-semibold text-base ${darkMode ? 'text-white' : 'text-[#443627]'}`}>
        {title}
      </h2>
    </div>
    {children}
  </motion.div>
);

const ToggleRow = ({ label, description, checked, onChange, darkMode }) => (
  <div className="flex items-center justify-between py-3">
    <div>
      <p className={`text-sm font-medium ${darkMode ? 'text-slate-200' : 'text-[#443627]'}`}>
        {label}
      </p>
      {description && (
        <p className={`text-xs mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
          {description}
        </p>
      )}
    </div>
    <label className="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only peer"
      />
      <div className={`w-11 h-6 rounded-full transition-colors duration-200 peer-checked:bg-[#443627] ${
        darkMode ? 'bg-slate-600' : 'bg-slate-300'
      }`}>
        <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200 ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`} />
      </div>
    </label>
  </div>
);

const SettingsPage = () => {
  const {
    darkMode, toggleDarkMode,
    language, setLanguage,
    fontSize, setFontSize,
  } = useSettings();
  const { user } = useAuth();

  const languages = [
    { value: 'English', label: 'English', native: 'English' },
    { value: 'Hindi', label: 'Hindi', native: 'हिंदी' },
    { value: 'Marathi', label: 'Marathi', native: 'मराठी' },
    { value: 'Tamil', label: 'Tamil', native: 'தமிழ்' },
    { value: 'Telugu', label: 'Telugu', native: 'తెలుగు' },
  ];

  const fontSizes = [
    { value: 14, label: 'Small' },
    { value: 16, label: 'Medium' },
    { value: 18, label: 'Large' },
    { value: 20, label: 'Extra Large' },
  ];

  return (
    <PageTransition>
      <div className="max-w-2xl mx-auto space-y-5 pb-16">

        {/* Header */}
        <div className="space-y-1 mb-2">
          <h1 className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-[#443627]'}`}>
            Settings
          </h1>
          <p className={darkMode ? 'text-slate-400' : 'text-[#725E54]'}>
            Customize your CaseIQ experience
          </p>
        </div>

        {/* Appearance */}
        <SettingsSection title="Appearance" icon={Sun} darkMode={darkMode}>
          <ToggleRow
            label="Dark Mode"
            description="Switch to a darker interface for low-light usage"
            checked={darkMode}
            onChange={toggleDarkMode}
            darkMode={darkMode}
          />

          <div className={`pt-3 border-t ${darkMode ? 'border-slate-700' : 'border-slate-100'}`}>
            <p className={`text-sm font-medium mb-3 ${darkMode ? 'text-slate-200' : 'text-[#443627]'}`}>
              Font Size
            </p>
            <div className="grid grid-cols-4 gap-2">
              {fontSizes.map((size) => (
                <button
                  key={size.value}
                  onClick={() => setFontSize(size.value)}
                  className={`py-2 rounded-xl text-sm font-medium transition border ${
                    fontSize === size.value
                      ? 'bg-[#443627] text-white border-[#443627] shadow'
                      : darkMode
                      ? 'bg-slate-700 text-slate-300 border-slate-600 hover:bg-slate-600'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-[#D5DCF9]/40'
                  }`}
                >
                  {size.label}
                </button>
              ))}
            </div>
            <p className={`text-xs mt-2 ${darkMode ? 'text-slate-400' : 'text-slate-400'}`}>
              Preview: <span style={{ fontSize: `${fontSize}px` }}>The quick brown fox</span>
            </p>
          </div>
        </SettingsSection>

        {/* Language */}
        <SettingsSection title="Language" icon={Globe} darkMode={darkMode}>
          <p className={`text-xs mb-3 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Select your preferred language for AI responses
          </p>
          <div className="space-y-2">
            {languages.map((lang) => (
              <button
                key={lang.value}
                onClick={() => setLanguage(lang.value)}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border transition ${
                  language === lang.value
                    ? 'bg-gradient-to-r from-[#8EDCE6]/30 to-[#D5DCF9]/30 border-[#A7B0CA] text-[#443627]'
                    : darkMode
                    ? 'bg-slate-700/40 border-slate-600 text-slate-300 hover:bg-slate-700'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <span className="text-sm font-medium">{lang.label}</span>
                <span className={`text-sm ${darkMode ? 'text-slate-400' : 'text-slate-400'}`}>
                  {lang.native}
                </span>
                {language === lang.value && (
                  <span className="ml-2 w-2 h-2 rounded-full bg-[#443627]" />
                )}
              </button>
            ))}
          </div>
        </SettingsSection>

        {/* Privacy */}
        <SettingsSection title="Privacy & Data" icon={Shield} darkMode={darkMode}>
          <ToggleRow
            label="Save Query History"
            description="Store your legal queries locally for quick access"
            checked={true}
            onChange={() => {}}
            darkMode={darkMode}
          />
          <div className={`pt-3 border-t ${darkMode ? 'border-slate-700' : 'border-slate-100'}`}>
            <button
              onClick={() => {
                localStorage.removeItem('caseiq_chat_guest');
                localStorage.removeItem('caseiq_fir');
              }}
              className="text-sm text-red-500 hover:text-red-600 font-medium transition"
            >
              Clear all local data
            </button>
          </div>
        </SettingsSection>

        {/* About */}
        <SettingsSection title="About CaseIQ" icon={Info} darkMode={darkMode}>
          <div className={`space-y-3 text-sm ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>
            <div className="flex justify-between">
              <span>Version</span>
              <span className="font-medium text-[#443627] dark:text-slate-200">1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span>AI Model</span>
              <span className="font-medium text-[#443627] dark:text-slate-200">Groq Llama 3.3 70B</span>
            </div>
            <div className="flex justify-between">
              <span>Legal Sections</span>
              <span className="font-medium text-[#443627] dark:text-slate-200">1,641</span>
            </div>
            <div className="flex justify-between">
              <span>Acts Covered</span>
              <span className="font-medium text-[#443627] dark:text-slate-200">BNS, BNSS, BSA, IPC, CrPC</span>
            </div>
            {user && (
              <div className="flex justify-between">
                <span>Signed in as</span>
                <span className="font-medium text-[#443627] dark:text-slate-200 truncate max-w-[160px]">
                  {user.email}
                </span>
              </div>
            )}
          </div>

          <div className={`mt-4 pt-4 border-t text-xs ${
            darkMode ? 'border-slate-700 text-slate-500' : 'border-slate-100 text-slate-400'
          }`}>
            CaseIQ provides legal information for awareness only. It does not constitute legal advice.
            Always consult a qualified advocate for your specific situation.
          </div>
        </SettingsSection>

      </div>
    </PageTransition>
  );
};

export default SettingsPage;