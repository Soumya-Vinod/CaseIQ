import { useSettings } from "../context/SettingsContext";

const SettingsPage = () => {
  const {
    darkMode,
    toggleDarkMode,
    language,
    setLanguage,
    fontSize,
    setFontSize,
  } = useSettings();

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h2
        className="text-3xl font-bold text-indigo-600 dark:text-indigo-400
"
      >
        Settings
      </h2>

      {/* Language Selection */}
      <div className="bg-white dark:bg-slate-800 shadow-sm rounded-xl p-6 border space-y-4">
        <h3 className="font-semibold">Language</h3>

        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option>English</option>
          <option>Hindi</option>
          <option>Tamil</option>
          <option>Marathi</option>
        </select>
      </div>

      {/* Dark Mode Toggle */}
      <div className="bg-white dark:bg-slate-800 shadow-sm rounded-xl p-6 border space-y-4">
        <h3 className="font-semibold">Dark Mode</h3>

        <button
          onClick={toggleDarkMode}
          className={`px-4 py-2 rounded-lg text-white transition ${
            darkMode ? "bg-indigo-600" : "bg-slate-500"
          }`}
        >
          {darkMode ? "Disable Dark Mode" : "Enable Dark Mode"}
        </button>
      </div>

      {/* Font Size */}
      <div className="bg-white dark:bg-slate-800 shadow-sm rounded-xl p-6 border space-y-4">
        <h3 className="font-semibold">Font Size</h3>

        <input
          type="range"
          min="14"
          max="24"
          value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          className="w-full"
        />

        <p className="text-sm text-slate-600">
          Current Font Size: {fontSize}px
        </p>
      </div>
    </div>
  );
};

export default SettingsPage;
