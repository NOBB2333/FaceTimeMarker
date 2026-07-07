import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        ink: "#171717",
        paper: "#f7f4ef",
        line: "#d7d2c8",
        accent: "#0f766e"
      }
    }
  },
  plugins: []
} satisfies Config;
