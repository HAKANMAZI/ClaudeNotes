// Sunucu sürümü köprüsü: window.claude yeteneklerini kendi sunucumuza (/api) bağlar.
// Anahtar gerekirse kullanıcıdan kendi Anthropic API anahtarını ister ve tarayıcıda saklar.
(function(){
let u=localStorage.getItem("fu"),c=localStorage.getItem("fc");
if(!u){u=(prompt("Adın (harf/rakam):")||"misafir");localStorage.setItem("fu",u)}
if(c===null){c=prompt("Erişim kodu:")||"";localStorage.setItem("fc",c)}
async function api(p,m,b){const r=await fetch("/api"+p,{method:m||"GET",headers:Object.assign({"content-type":"application/json","x-user":u,"x-code":c},localStorage.getItem("fk")?{"x-anthropic-key":localStorage.getItem("fk")}:{}),body:b?JSON.stringify(b):undefined});
  if(!r.ok){const e=await r.json().catch(()=>({}));if(r.status===401)localStorage.removeItem("fc");const er=new Error(e.error||"Hata");er.needKey=!!e.needKey;throw er}return r.json()}
const b64=b=>new Promise(ok=>{const f=new FileReader();f.onload=()=>ok(f.result.split(",")[1]);f.readAsDataURL(b)});
async function sample(input,o){o=o||{};const images=await Promise.all((o.images||[]).map(b64));
  const body={text:typeof input==="string"?input:JSON.stringify(input),images};
  try{const d=await api("/sample","POST",body);return{text:d.text,truncated:false}}
  catch(e){if(!e.needKey)throw e;localStorage.removeItem("fk");const k=(prompt("Claude için API anahtarını gir (sk-ant-...). Ücret senin hesabından düşer, anahtar sadece bu tarayıcıda saklanır:")||"").trim();
    if(!k)throw new Error("API anahtarı girilmedi.");localStorage.setItem("fk",k);const d=await api("/sample","POST",body);return{text:d.text,truncated:false}}}
sample.json=async(i,o)=>{const t=(await sample(i,o)).text;return JSON.parse(t.slice(t.indexOf("{"),t.lastIndexOf("}")+1))};
sample.limits=async()=>({images:true});
const db={collection:()=>({get:async()=>{const d=await api("/docs");return{docs:Object.values(d).map(x=>({data:()=>x}))}},
  doc:id=>({set:x=>api("/docs/"+id,"PUT",x),delete:()=>api("/docs/"+id,"DELETE")})})};
const M={db,user:{id:async()=>u},sample};
window.claude={use:async n=>M[n]||null};
})();
