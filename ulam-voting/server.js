const express = require('express');
const path = require('path');
const crypto = require('crypto');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const app = express();
const PORT = Number(process.env.PORT || 10000);
const TZ = 'Asia/Manila';
const MAX_VOTES = 10;
const ADMIN_PIN = String(process.env.ADMIN_PIN || '1234');
const JWT_SECRET = process.env.JWT_SECRET || crypto.randomBytes(32).toString('hex');
const ANALYZE_URL = String(process.env.ANALYZE_URL || '').trim();
const AI_API_KEY = String(process.env.AI_API_KEY || process.env.GEMINI_API_KEY || '').trim();
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL && !/localhost|127\.0.0.1/.test(process.env.DATABASE_URL)
    ? { rejectUnauthorized: false } : false
});

app.use(express.json({ limit: '200kb' }));
app.use(express.static(path.join(__dirname, 'public')));

const DEFAULT_ULAMS = ['Adobo','Sinigang na Baboy','Kare-kare','Menudo','Chicken Tinola','Lechon Kawali','Bicol Express','Pinakbet','Tinolang Isda','Afritada'];

function partsInManila(date = new Date()) {
  const f = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false });
  const p = Object.fromEntries(f.formatToParts(date).filter(x => x.type !== 'literal').map(x => [x.type, x.value]));
  return { year:+p.year, month:+p.month, day:+p.day, hour:+p.hour, minute:+p.minute, second:+p.second };
}
function dateKey(y,m,d){ return `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
function shiftDate(key, days){ const [y,m,d]=key.split('-').map(Number); const x=new Date(Date.UTC(y,m-1,d+days)); return dateKey(x.getUTCFullYear(),x.getUTCMonth()+1,x.getUTCDate()); }
function cycleInfo(now = new Date()) {
  const p=partsInManila(now); const today=dateKey(p.year,p.month,p.day); let cycle=today; let open;
  if(p.hour >= 18) open=true;
  else if(p.hour < 12) { open=true; cycle=shiftDate(today,-1); }
  else { open=false; cycle=shiftDate(today,-1); }
  const targetKey = open ? shiftDate(cycle,1) : today;
  const targetHour = open ? 12 : 18;
  const target = new Date(`${targetKey}T${String(targetHour).padStart(2,'0')}:00:00+08:00`).getTime();
  return { open, cycle, targetMs: target, nowMs: now.getTime() };
}
function validPin(pin){ return /^\d{4}$/.test(String(pin || '')); }
function normalizePhone(raw){ let d=String(raw||'').replace(/\D/g,''); if(d.startsWith('63')&&d.length===12)d='0'+d.slice(2); if(d.startsWith('9')&&d.length===10)d='0'+d; return d; }
function token(payload){ return jwt.sign(payload, JWT_SECRET, { expiresIn: '30d' }); }
function auth(req,res,next){ try { const h=req.headers.authorization||''; if(!h.startsWith('Bearer ')) return res.status(401).json({error:'Login required.'}); req.auth=jwt.verify(h.slice(7),JWT_SECRET); next(); } catch(e){ return res.status(401).json({error:'Session expired. Please log in again.'}); } }
function adminOnly(req,res,next){ if(req.auth?.role!=='admin') return res.status(403).json({error:'Admin access required.'}); next(); }
function memberOnly(req,res,next){ if(req.auth?.role!=='member') return res.status(403).json({error:'Member access required.'}); next(); }
function cleanName(s){ return String(s||'').trim().replace(/\s+/g,' ').slice(0,120); }
function cleanUlam(s){ return String(s||'').trim().replace(/\s+/g,' ').slice(0,120); }
function uniqueNames(list){ const seen=new Set(); return list.map(cleanUlam).filter(Boolean).filter(n=>{const k=n.toLowerCase();if(seen.has(k))return false;seen.add(k);return true;}); }
async function q(text, params=[]){ return pool.query(text,params); }

async function init(){
  if(!process.env.DATABASE_URL) throw new Error('DATABASE_URL is required for shared voting data.');
  await q(`CREATE TABLE IF NOT EXISTS ulam_voting_members (phone TEXT PRIMARY KEY, name TEXT NOT NULL, pin_hash TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`);
  await q(`CREATE TABLE IF NOT EXISTS ulam_voting_ulams (id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, name_key TEXT NOT NULL UNIQUE, active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`);
  await q(`CREATE TABLE IF NOT EXISTS ulam_voting_submissions (cycle_date DATE NOT NULL, member_phone TEXT NOT NULL REFERENCES ulam_voting_members(phone) ON DELETE CASCADE, submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(cycle_date, member_phone))`);
  await q(`CREATE TABLE IF NOT EXISTS ulam_voting_votes (cycle_date DATE NOT NULL, member_phone TEXT NOT NULL REFERENCES ulam_voting_members(phone) ON DELETE CASCADE, ulam_id BIGINT NOT NULL REFERENCES ulam_voting_ulams(id) ON DELETE RESTRICT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(cycle_date, member_phone, ulam_id))`);
  await q(`CREATE TABLE IF NOT EXISTS ulam_voting_suggestions (id BIGSERIAL PRIMARY KEY, text TEXT NOT NULL, member_phone TEXT REFERENCES ulam_voting_members(phone) ON DELETE SET NULL, member_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','added','dismissed')), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`);
  await q(`CREATE TABLE IF NOT EXISTS ulam_voting_menus (cycle_date DATE PRIMARY KEY, ulam_names JSONB NOT NULL, saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`);
  const count=await q(`SELECT COUNT(*)::int AS n FROM ulam_voting_ulams`);
  if(count.rows[0].n===0){ for(const n of DEFAULT_ULAMS) await q(`INSERT INTO ulam_voting_ulams(name,name_key) VALUES($1,$2) ON CONFLICT(name_key) DO NOTHING`,[n,n.toLowerCase()]); }
}

app.get('/healthz',(req,res)=>res.json({ok:true,service:'ulam-voting'}));
app.get('/api/state',(req,res)=>{ const c=cycleInfo(); res.json({open:c.open,cycle_date:c.cycle,target_ms:c.targetMs,server_now_ms:c.nowMs,max_votes:MAX_VOTES}); });

app.post('/api/register', async(req,res)=>{
  try {
    const name=cleanName(req.body.name), phone=normalizePhone(req.body.phone), pin=String(req.body.pin||'');
    if(name.length<2)return res.status(400).json({error:'Enter your full name.'});
    if(phone.length<10)return res.status(400).json({error:'Enter a valid mobile number.'});
    if(!validPin(pin))return res.status(400).json({error:'PIN must be exactly 4 digits.'});
    const exists=await q(`SELECT phone FROM ulam_voting_members WHERE phone=$1`,[phone]);
    if(exists.rowCount)return res.status(409).json({error:'This number is already registered. Please log in.'});
    const hash=await bcrypt.hash(pin,12);
    await q(`INSERT INTO ulam_voting_members(phone,name,pin_hash) VALUES($1,$2,$3)`,[phone,name,hash]);
    return res.json({token:token({role:'member',phone}),name,phone});
  } catch(e){ console.error(e); res.status(500).json({error:'Registration failed.'}); }
});
app.post('/api/login', async(req,res)=>{
  try {
    const phone=normalizePhone(req.body.phone), pin=String(req.body.pin||'');
    const r=await q(`SELECT phone,name,pin_hash FROM ulam_voting_members WHERE phone=$1`,[phone]);
    if(!r.rowCount || !(await bcrypt.compare(pin,r.rows[0].pin_hash)))return res.status(401).json({error:'Mobile number or PIN is incorrect.'});
    const m=r.rows[0]; res.json({token:token({role:'member',phone:m.phone}),name:m.name,phone:m.phone});
  } catch(e){ console.error(e); res.status(500).json({error:'Login failed.'}); }
});
app.post('/api/admin/login',(req,res)=>{
  const pin=String(req.body.pin||'');
  if(pin!==ADMIN_PIN)return res.status(401).json({error:'Wrong admin PIN.'});
  res.json({token:token({role:'admin'}),role:'admin'});
});
app.get('/api/me/status',auth,memberOnly,async(req,res)=>{
  try{
    const c=cycleInfo();
    const r=await q(`SELECT 1 FROM ulam_voting_submissions WHERE cycle_date=$1 AND member_phone=$2`,[c.cycle,req.auth.phone]);
    const votes=r.rowCount?await q(`SELECT ulam_id FROM ulam_voting_votes WHERE cycle_date=$1 AND member_phone=$2 ORDER BY ulam_id`,[c.cycle,req.auth.phone]):{rows:[]};
    res.json({voted:r.rowCount>0,ulam_ids:votes.rows.map(x=>Number(x.ulam_id))});
  }catch(e){res.status(500).json({error:'Could not load member status.'});}
});

app.get('/api/ulams', async(req,res)=>{
  try { const r=await q(`SELECT id,name FROM ulam_voting_ulams WHERE active=true ORDER BY lower(name)`); res.json({ulams:r.rows}); }
  catch(e){res.status(500).json({error:'Could not load ulams.'});}
});
app.post('/api/ulams',auth,adminOnly,async(req,res)=>{
  try {
    const names=uniqueNames(Array.isArray(req.body.names)?req.body.names:String(req.body.names||'').split(','));
    if(!names.length)return res.status(400).json({error:'Enter at least one ulam.'});
    const added=[];
    for(const n of names){
      const r=await q(`INSERT INTO ulam_voting_ulams(name,name_key,active) VALUES($1,$2,true) ON CONFLICT(name_key) DO UPDATE SET active=true RETURNING id,name`,[n,n.toLowerCase()]);
      if(r.rowCount)added.push(r.rows[0]);
    }
    res.json({ulams:added});
  }catch(e){console.error(e);res.status(500).json({error:'Could not add ulams.'});}
});
app.delete('/api/ulams/:id',auth,adminOnly,async(req,res)=>{
  try { await q(`UPDATE ulam_voting_ulams SET active=false WHERE id=$1`,[req.params.id]); res.json({ok:true}); }
  catch(e){res.status(500).json({error:'Could not remove ulam.'});}
});

app.post('/api/vote',auth,memberOnly,async(req,res)=>{
  const client=await pool.connect();
  try {
    const c=cycleInfo();
    if(!c.open)return res.status(403).json({error:'Voting is closed. Voting opens again at 6:00 PM.'});
    const ids=[...new Set((Array.isArray(req.body.ulam_ids)?req.body.ulam_ids:[]).map(Number).filter(Number.isInteger))];
    if(!ids.length||ids.length>MAX_VOTES)return res.status(400).json({error:`Pick 1 to ${MAX_VOTES} ulams.`});
    await client.query('BEGIN');
    const locked=await client.query(`SELECT 1 FROM ulam_voting_submissions WHERE cycle_date=$1 AND member_phone=$2 FOR UPDATE`,[c.cycle,req.auth.phone]);
    if(locked.rowCount){await client.query('ROLLBACK');return res.status(409).json({error:'You already voted for this round.'});}
    const ul=await client.query(`SELECT id FROM ulam_voting_ulams WHERE active=true AND id=ANY($1::bigint[])`,[ids]);
    if(ul.rowCount!==ids.length){await client.query('ROLLBACK');return res.status(400).json({error:'One or more selected ulams are no longer available.'});}
    await client.query(`INSERT INTO ulam_voting_submissions(cycle_date,member_phone) VALUES($1,$2)`,[c.cycle,req.auth.phone]);
    for(const id of ids) await client.query(`INSERT INTO ulam_voting_votes(cycle_date,member_phone,ulam_id) VALUES($1,$2,$3)`,[c.cycle,req.auth.phone,id]);
    await client.query('COMMIT'); res.json({ok:true,cycle_date:c.cycle,count:ids.length});
  }catch(e){
    await client.query('ROLLBACK').catch(()=>{});
    console.error(e);
    if(e && e.code==='23505') return res.status(409).json({error:'You already voted for this round.'});
    res.status(500).json({error:'Could not submit votes.'});
  }
  finally{client.release();}
});

async function ranking(cycle){
  const r=await q(`SELECT u.id,u.name,COUNT(v.ulam_id)::int AS n FROM ulam_voting_ulams u LEFT JOIN ulam_voting_votes v ON v.ulam_id=u.id AND v.cycle_date=$1 WHERE u.active=true GROUP BY u.id,u.name ORDER BY n DESC, lower(u.name)`,[cycle]);
  return r.rows;
}
app.get('/api/results',async(req,res)=>{
  try {
    const c=cycleInfo(); let admin=false;
    try{const h=req.headers.authorization||'';if(h.startsWith('Bearer ')){const a=jwt.verify(h.slice(7),JWT_SECRET);admin=a.role==='admin';}}catch(_){}
    if(c.open&&!admin)return res.status(403).json({error:'Live results are available to admin only until voting closes.'});
    const r=await ranking(c.cycle),v=await q(`SELECT COUNT(*)::int AS n FROM ulam_voting_submissions WHERE cycle_date=$1`,[c.cycle]);
    res.json({cycle_date:c.cycle,voters:v.rows[0].n,ranking:r.slice(0,10)});
  }catch(e){res.status(500).json({error:'Could not load results.'});}
});

app.post('/api/suggestions',auth,memberOnly,async(req,res)=>{
  try{
    const text=cleanUlam(req.body.text).slice(0,60);
    if(!text)return res.status(400).json({error:'Enter an ulam suggestion.'});
    const m=await q(`SELECT name FROM ulam_voting_members WHERE phone=$1`,[req.auth.phone]);
    await q(`INSERT INTO ulam_voting_suggestions(text,member_phone,member_name) VALUES($1,$2,$3)`,[text,req.auth.phone,m.rows[0]?.name||'Member']);
    res.json({ok:true});
  }catch(e){res.status(500).json({error:'Could not send suggestion.'});}
});
app.get('/api/suggestions',auth,adminOnly,async(req,res)=>{
  try{const r=await q(`SELECT id,text,member_name AS by,status,created_at FROM ulam_voting_suggestions ORDER BY created_at DESC`);res.json({suggestions:r.rows});}
  catch(e){res.status(500).json({error:'Could not load suggestions.'});}
});
app.patch('/api/suggestions/:id',auth,adminOnly,async(req,res)=>{
  const client=await pool.connect();
  try{
    const action=req.body.action;if(!['add','dismiss'].includes(action))return res.status(400).json({error:'Invalid action.'});
    await client.query('BEGIN');
    const s=await client.query(`SELECT id,text,status FROM ulam_voting_suggestions WHERE id=$1 FOR UPDATE`,[req.params.id]);
    if(!s.rowCount){await client.query('ROLLBACK');return res.status(404).json({error:'Suggestion not found.'});}
    const text=s.rows[0].text;
    if(action==='add'){
      await client.query(`INSERT INTO ulam_voting_ulams(name,name_key,active) VALUES($1,$2,true) ON CONFLICT(name_key) DO UPDATE SET active=true`,[text,text.toLowerCase()]);
      await client.query(`UPDATE ulam_voting_suggestions SET status='added' WHERE id=$1`,[req.params.id]);
    }else await client.query(`UPDATE ulam_voting_suggestions SET status='dismissed' WHERE id=$1`,[req.params.id]);
    await client.query('COMMIT');res.json({ok:true});
  }catch(e){await client.query('ROLLBACK').catch(()=>{});console.error(e);res.status(500).json({error:'Could not update suggestion.'});}
  finally{client.release();}
});

function localAnalysis(r,voters){
  if(!voters)return 'No votes yet for this round.';
  const top=r.slice(0,10), tenth=top[Math.min(9,top.length-1)]?.n??0;
  const lines=[`${voters} member(s) voted. Leader: ${top[0]?.name||'None'} with ${top[0]?.n||0} vote(s) (${Math.round((top[0]?.n||0)/voters*100)}% of voters).`];
  const ties=r.filter(x=>x.n===tenth);if(ties.length>1)lines.push(`Tie around the 10th spot: ${ties.map(x=>x.name).join(', ')}.`);
  const zero=r.filter(x=>x.n===0).map(x=>x.name);if(zero.length)lines.push(`Zero votes: ${zero.join(', ')}.`);
  lines.push(`Recommendation: use the strongest vote-getters for tomorrow's menu and use cost, stock, and prep time to break any ties.`);
  return lines.join('\n');
}
app.post('/api/analyze',auth,adminOnly,async(req,res)=>{
  try{
    const c=cycleInfo(),r=await ranking(c.cycle),v=await q(`SELECT COUNT(*)::int AS n FROM ulam_voting_submissions WHERE cycle_date=$1`,[c.cycle]),voters=v.rows[0].n,payload={ranking:r,voters};
    if(ANALYZE_URL){
      const headers={'Content-Type':'application/json'};if(AI_API_KEY)headers.Authorization=`Bearer ${AI_API_KEY}`;
      const rr=await fetch(ANALYZE_URL,{method:'POST',headers,body:JSON.stringify(payload)});
      if(rr.ok){const j=await rr.json();if(j.text)return res.json({text:j.text,source:'ai'});}
    }
    res.json({text:localAnalysis(r,voters),source:'local'});
  }catch(e){console.error(e);res.status(500).json({error:'Analysis failed.'});}
});

app.get('/api/menu',async(req,res)=>{
  try{const r=await q(`SELECT cycle_date,ulam_names,saved_at FROM ulam_voting_menus ORDER BY cycle_date DESC LIMIT 1`);res.json({menu:r.rowCount?{cycle_date:r.rows[0].cycle_date,ulam_names:r.rows[0].ulam_names}:null});}
  catch(e){res.status(500).json({error:'Could not load menu.'});}
});
app.post('/api/menu',auth,adminOnly,async(req,res)=>{
  try{
    const c=cycleInfo();if(c.open)return res.status(403).json({error:'Save the next-day menu after voting closes at 12:00 NN.'});
    const cycle=String(req.body.cycle_date||c.cycle);if(cycle!==c.cycle)return res.status(400).json({error:'Menu must be saved for the current voting cycle.'});
    const names=uniqueNames(Array.isArray(req.body.ulam_names)?req.body.ulam_names:[]);
    if(!names.length||names.length>10)return res.status(400).json({error:'Pick 1 to 10 ulams.'});
    const r=await ranking(cycle),allowed=new Set(r.slice(0,10).map(x=>x.name.toLowerCase()));
    if(names.some(n=>!allowed.has(n.toLowerCase())))return res.status(400).json({error:'Menu choices must come from the top 10 results.'});
    await q(`INSERT INTO ulam_voting_menus(cycle_date,ulam_names) VALUES($1,$2::jsonb) ON CONFLICT(cycle_date) DO UPDATE SET ulam_names=EXCLUDED.ulam_names,saved_at=NOW()`,[cycle,JSON.stringify(names)]);
    res.json({ok:true,cycle_date:cycle,ulam_names:names});
  }catch(e){console.error(e);res.status(500).json({error:'Could not save menu.'});}
});

app.use((req,res)=>res.sendFile(path.join(__dirname,'public','ulam-voting.html')));
init().then(()=>app.listen(PORT,()=>console.log(`Ulam Voting listening on ${PORT}`))).catch(e=>{console.error(e);process.exit(1)});
