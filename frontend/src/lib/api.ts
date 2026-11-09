import { money } from './format';
export { money };

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export type User = {id:number;name:string;email:string;role:'manager'|'officer';branch_id:number|null};
export type Loan = {id:number;loan_id:string;borrower_name:string;pincode:string;branch_name:string;outstanding:number;dpd:number;promise_date:string|null;payment_history:string;assigned_to:number|null;officer_name:string;status:string;priority:{score:number;reasons:string[]}};
let token = localStorage.getItem('collectiq_token') || '';
export function setToken(value:string){token=value; if(value)localStorage.setItem('collectiq_token',value);else localStorage.removeItem('collectiq_token')}
export async function api<T>(path:string, init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers); if(token)headers.set('Authorization',`Bearer ${token}`);
 if(init.body && !(init.body instanceof FormData))headers.set('Content-Type','application/json');
 const response=await fetch(`${API}${path}`,{...init,headers});
 if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=body.detail||message}catch{}throw new Error(message)}
 return response.json();
}

