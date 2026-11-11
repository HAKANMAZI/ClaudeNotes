// Fiş Takip sunucusu (Express).
// /api/docs: kullanıcı başına kayıtlar (data/<kullanıcı>.json)
// /api/sample: Claude'a istek. Kullanıcı kendi anahtarını gönderirse onu, yoksa sunucu anahtarını kullanır.
// Ayarlar: ACCESS_CODE (erişim kodu), ANTHROPIC_API_KEY (isteğe bağlı), DAILY_LIMIT, DATA_DIR, PORT.
const express=require("express"),fs=require("fs"),path=require("path");
const app=express();app.use(express.json({limit:"15mb"}));
const CODE=process.env.ACCESS_CODE||"",KEY=process.env.ANTHROPIC_API_KEY,MODEL=process.env.MODEL||"claude-sonnet-5-5";
const LIMIT=+process.env.DAILY_LIMIT||30,DIR=process.env.DATA_DIR||path.join(__dirname,"data");
fs.mkdirSync(DIR,{recursive:true});
const used={},safe=s=>String(s||"").toLowerCase().replace(/[^a-z0-9_-]/g,"").slice(0,40);
// Her istekte kullanıcı adı ve erişim kodu kontrolü
app.use("/api",(q,r,n)=>{const u=safe(q.get("x-user"));
  if(!u||(CODE&&q.get("x-code")!==CODE))return r.status(401).json({error:"Ad veya erişim kodu hatalı"});q.u=u;n()});
const file=u=>path.join(DIR,u+".json");
const load=u=>{try{return JSON.parse(fs.readFileSync(file(u),"utf8"))}catch(e){return{}}};
// Kayıtları oku / yaz / sil
app.get("/api/docs",(q,r)=>r.json(load(q.u)));
app.put("/api/docs/:id",(q,r)=>{const d=load(q.u);d[safe(q.params.id)]=q.body;fs.writeFileSync(file(q.u),JSON.stringify(d));r.json({ok:1})});
app.delete("/api/docs/:id",(q,r)=>{const d=load(q.u);delete d[safe(q.params.id)];fs.writeFileSync(file(q.u),JSON.stringify(d));r.json({ok:1})});
// Claude isteği: günlük limit, kullanıcı anahtarı veya sunucu anahtarı
app.post("/api/sample",async(q,r)=>{
  const k=q.u+new Date().toISOString().slice(0,10);used[k]=(used[k]||0)+1;
  if(used[k]>LIMIT)return r.status(429).json({error:"Günlük limit doldu"});
  const AK=q.get("x-anthropic-key")||KEY;
  if(!AK)return r.status(400).json({error:"API anahtarı gerekli",needKey:true});
  const{text,images=[]}=q.body;
  const content=[...images.map(d=>({type:"image",source:{type:"base64",media_type:"image/jpeg",data:d}})),{type:"text",text}];
  try{const a=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",
      headers:{"content-type":"application/json","x-api-key":AK,"anthropic-version":"2023-06-01"},
      body:JSON.stringify({model:MODEL,max_tokens:4000,messages:[{role:"user",content}]})});
    const j=await a.json();if(!a.ok)return r.status(a.status===401?400:502).json({error:a.status===401?"API anahtarı geçersiz":(j.error&&j.error.message)||"API hatası",needKey:a.status===401});
    r.json({text:j.content.filter(c=>c.type==="text").map(c=>c.text).join("")});
  }catch(e){r.status(502).json({error:"API'ye ulaşılamadı"})}});
app.use(express.static(path.join(__dirname,"public")));
app.listen(process.env.PORT||3000,()=>console.log("Hazır: http://localhost:"+(process.env.PORT||3000)));
