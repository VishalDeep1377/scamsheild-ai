"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ShieldCheck,LayoutDashboard,ScanSearch,Link2,Mail,History,GraduationCap,Flag,Settings,LogOut,Menu } from "lucide-react";
import { clearToken } from "@/lib/api";
const nav=[["Dashboard","/dashboard",LayoutDashboard],["Message scanner","/scanner",ScanSearch],["URL intelligence","/url-analyzer",Link2],["Email analyzer","/email-analyzer",Mail],["Scan history","/history",History],["Awareness academy","/academy",GraduationCap],["Report a scam","/reports",Flag],["Settings","/settings",Settings]] as const;
export default function Shell({children}:{children:React.ReactNode}){
 const path=usePathname(); const router=useRouter();
 return <div className="min-h-screen md:flex">
  <aside className="w-full md:w-[250px] md:min-h-screen border-b md:border-b-0 md:border-r border-line bg-[#0b1420] p-5 flex md:flex-col gap-5">
   <Link href="/dashboard" className="flex items-center gap-3"><div className="h-10 w-10 rounded-xl bg-emerald-400/10 border border-emerald-300/20 grid place-items-center"><ShieldCheck className="text-mint"/></div><div><div className="font-black tracking-[.16em]">SCAMSHIELD</div><div className="text-[10px] muted tracking-[.2em]">THREAT INTELLIGENCE</div></div></Link>
   <div className="hidden md:block text-[10px] muted tracking-[.2em] mt-4">WORKSPACE</div>
   <nav className="flex md:flex-col gap-1 flex-wrap">{nav.map(([label,href,Icon])=><Link key={href} href={href} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm ${path===href?"bg-emerald-400/10 text-mint border border-emerald-300/10":"text-slate-400 hover:text-white hover:bg-white/5"}`}><Icon size={17}/>{label}</Link>)}</nav>
   <div className="hidden md:block mt-auto card p-4"><div className="text-xs font-semibold text-mint">SAFETY REMINDER</div><p className="text-xs muted mt-2 leading-5">Never share OTPs, passwords or PINs. Verify requests through official channels.</p></div>
   <button onClick={()=>{clearToken();router.push("/");}} className="md:mt-4 text-xs muted flex items-center gap-2 hover:text-white"><LogOut size={15}/> Sign out</button>
  </aside>
  <main className="flex-1 min-w-0"><div className="max-w-7xl mx-auto p-5 md:p-9">{children}</div></main>
 </div>
}
