import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title:"ScamShield AI | Think Before You Click", description:"Explainable suspicious-message and phishing analysis." };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
