import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        pokemon: {
          red: "#EF5350",
          pokedex: "#CC0000",   // klassisches Pokédex-Rot
          yellow: "#FFCA28",
          blue: "#42A5F5",
          dark: "#1a1a2e",
          card: "#16213e",
          accent: "#0f3460",
        },
      },
    },
  },
  plugins: [],
};

export default config;
