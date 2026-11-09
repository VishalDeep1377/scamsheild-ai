const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export function getToken(){ if(typeof window==="undefined") return ""; return localStorage.getItem("scamshield_token") || ""; }
export function setToken(token:string){ localStorage.setItem("scamshield_token",token); }
export function clearToken(){ localStorage.removeItem("scamshield_token"); }
export async function api<T>(path:string, options:RequestInit = {}):Promise<T>{
  const token=getToken();
  const headers:Record<string,string>={"Content-Type":"application/json",...(options.headers as Record<string,string>||{})};
  if(token) headers.Authorization=`Bearer ${token}`;
  const response=await fetch(`${API}${path}`,{...options,headers,cache:"no-store"});
  const body=await response.json().catch(()=>({detail:"Unexpected server response"}));
  if(!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body as T;
}
export async function downloadReport(id:number){
 const token=getToken(); const r=await fetch(`${API}/scans/${id}/report`,{headers:{Authorization:`Bearer ${token}`}});
 if(!r.ok) throw new Error("Could not download report");
 const blob=await r.blob(); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=`scamshield-${id}.pdf`; a.click(); URL.revokeObjectURL(url);
}
