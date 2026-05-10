"""
NOTZHUB Desync — Bot + Key Site + API (Railway)
"""

import discord
from discord.ext import commands
from aiohttp import web
import json, os, string, random
from datetime import datetime, timedelta

BOT_TOKEN      = os.environ["BOT_TOKEN"]
DESYNC_ROLE_ID = int(os.environ["DESYNC_ROLE_ID"])
LOG_CHANNEL_ID = int(os.environ["LOG_CHANNEL_ID"])
API_PORT       = int(os.environ.get("PORT", 7890))
KEYS_FILE      = "desync_keys.json"
KEY_PREFIX     = "NOTZ-DSC"
KEY_EXPIRY     = int(os.environ.get("KEY_EXPIRY_DAYS", "30"))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ── Storage ──

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE) as f: return json.load(f)
    return {}

def save_keys(d):
    with open(KEYS_FILE, "w") as f: json.dump(d, f, indent=2)

def gen_key():
    body = "".join(random.choices(string.ascii_uppercase + string.digits, k=24))
    return KEY_PREFIX + "-" + "-".join(body[i:i+4] for i in range(0, 24, 4))

def make_entry(uid, name):
    return gen_key(), {
        "discord_id": uid, "discord_name": name,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=KEY_EXPIRY)).isoformat() if KEY_EXPIRY > 0 else None,
        "hwid": None, "active": True, "uses": 0,
    }

def check_key(key, data):
    if key not in data: return False, "Key não encontrada"
    e = data[key]
    if not e.get("active"): return False, "Key revogada"
    if e.get("expires_at") and datetime.utcnow() > datetime.fromisoformat(e["expires_at"]):
        return False, "Key expirada"
    return True, "OK"

# ── Site HTML ──

SITE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NotZHub Desync</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;900&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Outfit',sans-serif;background:#080000;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden}
.bg{position:fixed;inset:0;z-index:0}
.bg::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 30% 20%,rgba(180,10,10,.15)0%,transparent 60%),radial-gradient(ellipse at 70% 80%,rgba(120,0,0,.1)0%,transparent 50%)}
.card{position:relative;z-index:1;width:420px;max-width:92vw;background:linear-gradient(145deg,#120404,#0a0202);border:1.5px solid rgba(200,20,20,.4);border-radius:20px;padding:40px 35px;box-shadow:0 0 80px rgba(180,0,0,.08),0 20px 60px rgba(0,0,0,.5)}
.logo{text-align:center;margin-bottom:8px;font-size:28px;font-weight:900;letter-spacing:2px}
.logo .w{color:#fff}.logo .r{color:#e02020}
.sub{text-align:center;color:#6a4040;font-size:11px;font-weight:600;letter-spacing:3px;text-transform:uppercase;margin-bottom:30px}
input{width:100%;padding:14px 18px;background:#1a0606;border:1.5px solid #2a0a0a;border-radius:12px;color:#e0c8c8;font-family:'Outfit';font-size:14px;font-weight:600;outline:none;transition:.2s;margin-bottom:14px}
input:focus{border-color:#c01515}
input::placeholder{color:#4a2525}
.btn{width:100%;padding:14px;border:none;background:linear-gradient(135deg,#d01818,#8a0a0a);color:#fff;font-family:'Outfit';font-size:14px;font-weight:700;letter-spacing:1px;border-radius:12px;cursor:pointer;transition:.15s;text-transform:uppercase}
.btn:hover{transform:translateY(-1px);box-shadow:0 8px 30px rgba(200,10,10,.3)}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.st{text-align:center;margin-top:14px;font-size:13px;font-weight:600;min-height:20px}
.st.ok{color:#40d040}.st.er{color:#e04040}.st.ld{color:#a08080}
.cs{margin-top:22px;padding-top:18px;border-top:1px solid #1a0808}
.cs label{display:block;color:#5a3030;font-size:10px;font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
.cb{position:relative;background:#0e0303;border:1px solid #200808;border-radius:10px;padding:12px 50px 12px 14px;font-family:'Courier New',monospace;font-size:11px;color:#c09090;word-break:break-all;line-height:1.6;user-select:all;white-space:pre-wrap}
.cp{position:absolute;top:8px;right:8px;background:#2a0808;border:1px solid #3a1010;color:#a06060;padding:4px 10px;border-radius:6px;font-size:10px;cursor:pointer;font-family:'Outfit';font-weight:600;transition:.2s}
.cp:hover{background:#3a1010;color:#e0a0a0}
.ft{text-align:center;margin-top:20px;color:#3a1818;font-size:10px;font-weight:600;letter-spacing:1px}
.dot{display:inline-block;width:6px;height:6px;background:#c01515;border-radius:50%;margin-right:6px;animation:p 1.5s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
</style>
</head>
<body>
<div class="bg"></div>
<div class="card">
<div class="logo"><span class="w">NOTZ</span><span class="r">HUB</span></div>
<div class="sub">Desync Key System</div>
<input id="ki" placeholder="NOTZ-DSC-XXXX-XXXX-XXXX-XXXX" spellcheck="false">
<button class="btn" id="cb" onclick="ck()">Verificar Key</button>
<div class="st" id="st"></div>
<div class="cs">
<label>Loader — cole no executor</label>
<div class="cb" id="lb">_G.NOTZ_DESYNC_KEY = "<span id="ks">SUA-KEY-AQUI</span>"
loadstring(game:HttpGet("GIST_RAW_URL_AQUI"))()</div>
<button class="cp" onclick="cl()">COPIAR</button>
</div>
<div class="ft"><span class="dot"></span>NotZHub Desync</div>
</div>
<script>
async function ck(){
const k=document.getElementById("ki").value.trim(),s=document.getElementById("st"),b=document.getElementById("cb");
if(!k){s.className="st er";s.textContent="Cole sua key";return}
b.disabled=1;b.textContent="VERIFICANDO...";s.className="st ld";s.textContent="...";
try{const r=await(await fetch("/validate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({key:k})})).json();
if(r.valid){s.className="st ok";s.textContent="✅ Válida — "+r.user;document.getElementById("ks").textContent=k}
else{s.className="st er";s.textContent="❌ "+r.error}}
catch(e){s.className="st er";s.textContent="Erro de conexão"}
b.disabled=0;b.textContent="VERIFICAR KEY"}
function cl(){const t=document.getElementById("lb").textContent;navigator.clipboard.writeText(t);const b=event.target;b.textContent="COPIADO!";setTimeout(()=>b.textContent="COPIAR",1500)}
document.getElementById("ki").onkeydown=e=>{if(e.key==="Enter")ck()};
</script>
</body>
</html>"""

# ── Discord ──

@bot.event
async def on_member_update(before, after):
    br = {r.id for r in before.roles}
    ar = {r.id for r in after.roles}

    if DESYNC_ROLE_ID not in br and DESYNC_ROLE_ID in ar:
        kd = load_keys()
        ex = next((k for k,v in kd.items() if v["discord_id"]==after.id and v["active"] and check_key(k,kd)[0]), None)
        if ex:
            try: await after.send(embed=discord.Embed(title="🔑 Key já ativa!", description=f"```{ex}```", color=0xFF2020))
            except: pass
            return
        key, entry = make_entry(after.id, str(after))
        kd[key] = entry; save_keys(kd)
        try:
            e = discord.Embed(title="🔑 NOTZHUB DESYNC", description=f"Sua key:\n```{key}```", color=0xFF2020)
            e.add_field(name="Validade", value=f"{KEY_EXPIRY}d" if KEY_EXPIRY else "∞")
            e.set_footer(text="Não compartilhe • Cole no executor")
            await after.send(embed=e)
        except:
            ch = bot.get_channel(LOG_CHANNEL_ID)
            if ch: await ch.send(f"⚠️ DM fechado {after.mention}: ||{key}||")
        ch = bot.get_channel(LOG_CHANNEL_ID)
        if ch: await ch.send(embed=discord.Embed(title="🔑 Gerada", description=f"{after.mention}\n||{key}||", color=0xFF2020, timestamp=datetime.utcnow()))

    if DESYNC_ROLE_ID in br and DESYNC_ROLE_ID not in ar:
        kd = load_keys()
        n = 0
        for v in kd.values():
            if v["discord_id"]==after.id and v["active"]: v["active"]=False; n+=1
        if n: save_keys(kd)
        ch = bot.get_channel(LOG_CHANNEL_ID)
        if ch and n: await ch.send(f"🚫 {n} key(s) de {after.mention} revogada(s)")

@bot.command(name="genkey")
@commands.has_permissions(administrator=True)
async def cmd_genkey(ctx, m: discord.Member):
    kd = load_keys(); k, e = make_entry(m.id, str(m)); kd[k]=e; save_keys(kd)
    try: await m.send(embed=discord.Embed(title="🔑 Desync Key", description=f"```{k}```", color=0xFF2020)); await ctx.send(f"✅ DM enviado a {m.mention}")
    except: await ctx.send(f"✅ DM fechado. ||{k}||")

@bot.command(name="revokekey")
@commands.has_permissions(administrator=True)
async def cmd_revoke(ctx, key: str):
    kd = load_keys()
    if key in kd: kd[key]["active"]=False; save_keys(kd); await ctx.send("🚫 Revogada")
    else: await ctx.send("❌ Não existe")

@bot.command(name="listkeys")
@commands.has_permissions(administrator=True)
async def cmd_list(ctx):
    kd = load_keys(); a = [(k,v) for k,v in kd.items() if v.get("active")]
    if not a: await ctx.send("Nenhuma"); return
    await ctx.send(embed=discord.Embed(title=f"🔑 {len(a)} ativas", description="\n".join(f"`{k[:16]}…` → {v['discord_name']} ({v['uses']}x)" for k,v in a[:20]), color=0xFF2020))

# ── API ──

async def h_validate(req):
    try: b = await req.json(); key = b.get("key","")
    except: return web.json_response({"valid":False,"error":"bad"},status=400)
    kd = load_keys(); ok, msg = check_key(key, kd)
    if ok:
        kd[key]["uses"] += 1
        hwid = b.get("hwid")
        if hwid:
            if kd[key]["hwid"] is None: kd[key]["hwid"]=hwid
            elif kd[key]["hwid"]!=hwid: return web.json_response({"valid":False,"error":"HWID diferente"})
        save_keys(kd)
        return web.json_response({"valid":True,"user":kd[key]["discord_name"]})
    return web.json_response({"valid":False,"error":msg})

async def h_site(req):
    return web.Response(text=SITE, content_type="text/html")

async def start_api():
    app = web.Application()
    app.router.add_get("/", h_site)
    app.router.add_post("/validate", h_validate)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", API_PORT).start()

@bot.event
async def on_ready():
    await start_api()
    print(f"[NotZHub] {bot.user} | porta {API_PORT}")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
