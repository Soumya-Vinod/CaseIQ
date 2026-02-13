import { useState, useEffect } from "react";

const useAccessibility = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [fontSize, setFontSize] = useState(16);

  useEffect(() => {
    const savedDark = localStorage.getItem("caseiq_dark");
    const savedFont = localStorage.getItem("caseiq_font");

    if (savedDark) setDarkMode(JSON.parse(savedDark));
    if (savedFont) setFontSize(Number(savedFont));
  }, []);

  useEffect(() => {
    localStorage.setItem("caseiq_dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    localStorage.setItem("caseiq_font", fontSize);
  }, [fontSize]);

  return {
    darkMode,
    setDarkMode,
    fontSize,
    setFontSize,
  };
};

export default useAccessibility;
