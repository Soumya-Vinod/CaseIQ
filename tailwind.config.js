export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1", // Primary Brand
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },

        accent: {
          light: "#fbbf24", // Warm amber
          DEFAULT: "#f59e0b",
          dark: "#d97706",
        },

        surface: {
          light: "#ffffff",
          dark: "#1e293b",
        },

        background: {
          light: "#f8fafc",
          dark: "#0f172a",
        },
      },

      boxShadow: {
        soft: "0 10px 25px -5px rgba(0, 0, 0, 0.05)",
        warm: "0 10px 30px rgba(99, 102, 241, 0.15)",
      },

      borderRadius: {
        xl2: "1.25rem",
      },

      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
