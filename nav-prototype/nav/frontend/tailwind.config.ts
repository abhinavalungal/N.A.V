import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        abyss: "#070D13",
        hull: "#0D1620",
        deck: "#131F2B",
        raised: "#182634",
        hairline: "#1E2E3D",
        ink: "#E4EDF5",
        dim: "#8CA3B8",
        faint: "#5A7188",
        brass: "#E3A54B",
        sea: "#4C9BC4",
        kelp: "#4FB286",
        coral: "#D9634F",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "2px",
        sm: "2px",
        md: "3px",
        lg: "4px",
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};

export default config;
