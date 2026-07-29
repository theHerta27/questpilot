/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        command: "#172554",
        signal: "#0f766e",
        warning: "#d97706",
        danger: "#c2410c",
        paper: "#f6f3ea"
      },
      boxShadow: {
        panel: "0 18px 45px rgba(23, 37, 84, 0.10)"
      }
    }
  },
  plugins: []
};
