import type { Config } from "tailwindcss";

/**
 * Colours are CSS variables holding raw RGB channels, so Tailwind's opacity
 * modifiers still work (bg-brass/10, border-hairline/60) and the whole palette
 * can be swapped by setting data-theme on <html>. Both themes are defined in
 * app/globals.css.
 */
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        abyss: token("abyss"),
        hull: token("hull"),
        deck: token("deck"),
        raised: token("raised"),
        hairline: token("hairline"),
        ink: token("ink"),
        dim: token("dim"),
        faint: token("faint"),
        brass: token("brass"),
        sea: token("sea"),
        kelp: token("kelp"),
        coral: token("coral"),
      },
      fontFamily: {
        sans: ["Geist Sans", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "monospace"],
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
