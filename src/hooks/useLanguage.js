import { useState, useEffect } from "react";

const useLanguage = () => {
  const [language, setLanguage] = useState("English");

  useEffect(() => {
    const saved = localStorage.getItem("caseiq_language");
    if (saved) setLanguage(saved);
  }, []);

  useEffect(() => {
    localStorage.setItem("caseiq_language", language);
  }, [language]);

  return { language, setLanguage };
};

export default useLanguage;
