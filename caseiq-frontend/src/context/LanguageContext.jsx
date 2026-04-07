import { createContext, useContext, useState, useEffect } from 'react';

const translations = {
  en: {
    appName: 'CaseIQ',
    tagline: 'AI-Powered Legal Knowledge',
    home: 'Home',
    aiAssistant: 'AI Assistant',
    firDraft: 'FIR Draft',
    lawExplorer: 'Law Explorer',
    legalNews: 'Legal News',
    education: 'Education',
    dashboard: 'Dashboard',
    history: 'History',
    settings: 'Settings',
    signIn: 'Sign In',
    signOut: 'Sign Out',
    createAccount: 'Create Account',
    askQuery: 'Ask a Legal Question',
    queryPlaceholder: 'Type your legal question...',
    sendButton: 'Send',
    generateFIR: 'Generate FIR Draft',
    downloadPDF: 'Download PDF',
    clearChat: 'Clear Chat',
    noHistory: 'No history yet',
    loading: 'Loading...',
    disclaimer: '⚠️ CaseIQ provides legal knowledge only, not legal advice.',
    welcomeMessage: '👋 Welcome to CaseIQ. Ask any legal question about Indian law.',
  },
  hi: {
    appName: 'केसआईक्यू',
    tagline: 'AI-संचालित कानूनी ज्ञान',
    home: 'होम',
    aiAssistant: 'AI सहायक',
    firDraft: 'FIR ड्राफ्ट',
    lawExplorer: 'कानून खोजक',
    legalNews: 'कानूनी समाचार',
    education: 'शिक्षा',
    dashboard: 'डैशबोर्ड',
    history: 'इतिहास',
    settings: 'सेटिंग्स',
    signIn: 'साइन इन',
    signOut: 'साइन आउट',
    createAccount: 'खाता बनाएं',
    askQuery: 'कानूनी प्रश्न पूछें',
    queryPlaceholder: 'अपना कानूनी प्रश्न टाइप करें...',
    sendButton: 'भेजें',
    generateFIR: 'FIR ड्राफ्ट बनाएं',
    downloadPDF: 'PDF डाउनलोड करें',
    clearChat: 'चैट साफ करें',
    noHistory: 'अभी तक कोई इतिहास नहीं',
    loading: 'लोड हो रहा है...',
    disclaimer: '⚠️ केसआईक्यू केवल कानूनी जानकारी प्रदान करता है, कानूनी सलाह नहीं।',
    welcomeMessage: '👋 केसआईक्यू में आपका स्वागत है। भारतीय कानून के बारे में कोई भी प्रश्न पूछें।',
  },
  mr: {
    appName: 'केसआयक्यू',
    tagline: 'AI-चालित कायदेशीर ज्ञान',
    home: 'मुखपृष्ठ',
    aiAssistant: 'AI सहाय्यक',
    firDraft: 'FIR मसुदा',
    lawExplorer: 'कायदा शोधक',
    legalNews: 'कायदेशीर बातम्या',
    education: 'शिक्षण',
    dashboard: 'डॅशबोर्ड',
    history: 'इतिहास',
    settings: 'सेटिंग्ज',
    signIn: 'साइन इन',
    signOut: 'साइन आउट',
    createAccount: 'खाते तयार करा',
    askQuery: 'कायदेशीर प्रश्न विचारा',
    queryPlaceholder: 'तुमचा कायदेशीर प्रश्न टाइप करा...',
    sendButton: 'पाठवा',
    generateFIR: 'FIR मसुदा तयार करा',
    downloadPDF: 'PDF डाउनलोड करा',
    clearChat: 'चॅट साफ करा',
    noHistory: 'अद्याप इतिहास नाही',
    loading: 'लोड होत आहे...',
    disclaimer: '⚠️ केसआयक्यू फक्त कायदेशीर माहिती देते, कायदेशीर सल्ला नाही।',
    welcomeMessage: '👋 केसआयक्यूमध्ये आपले स्वागत आहे। भारतीय कायद्याबद्दल कोणताही प्रश्न विचारा।',
  },
};

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [uiLanguage, setUiLanguage] = useState(() => {
    return localStorage.getItem('caseiq_ui_language') || 'en';
  });

  useEffect(() => {
    localStorage.setItem('caseiq_ui_language', uiLanguage);
  }, [uiLanguage]);

  const t = (key) => translations[uiLanguage]?.[key] || translations.en[key] || key;

  return (
    <LanguageContext.Provider value={{ uiLanguage, setUiLanguage, t, translations }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);