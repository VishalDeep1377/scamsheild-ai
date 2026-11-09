import type { Config } from "tailwindcss";
const config: Config = { content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"], theme: { extend: { colors: { ink:"#080E18", panel:"#101B2A", line:"#223247", mint:"#43E2A0" }, boxShadow: { glow:"0 0 40px rgba(67,226,160,.08)" } } }, plugins: [] };
export default config;
