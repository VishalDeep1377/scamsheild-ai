import Link from "next/link";
export default function NotFound(){return <main className="min-h-screen grid place-items-center bg-ink"><div className="text-center"><div className="text-5xl font-black">404</div><p className="muted mt-3">This page does not exist.</p><Link className="text-mint underline mt-5 inline-block" href="/dashboard">Return to dashboard</Link></div></main>}
