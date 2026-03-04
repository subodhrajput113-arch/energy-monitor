# ==========================================
# Energy Monitor Pro — Flask Backend v3.0
# Run: python3 server.py
# ==========================================

import os, sqlite3, json, math
from flask import Flask, render_template_string, request, Response, jsonify
from threading import Thread, Lock
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt

BROKER    = "broker.hivemq.com"
PORT      = 1883
TOPIC     = "subodh/energy/home1"
DB        = "/tmp/energy_v3.db"
RATE      = 8.0
MAX_LOAD  = 5000.0
FREQUENCY = 50.0

SLABS = [
    (100,  3.50),
    (200,  5.00),
    (300,  7.00),
    (float("inf"), 9.50),
]

db_lock     = Lock()
latest_data = {}

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Energy Monitor Pro</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Mulish:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
/*==== RESET & VARS ====*/
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#f2f0ea;--sb:#ffffff;--card:#ffffff;--card2:#faf8f3;
  --bdr:#e5e1d8;--bdr2:#ede9e0;
  --y:#f5c518;--yl:#fff9db;--yd:#c9a100;
  --ink:#1a1a1a;--g1:#5c6470;--g2:#9199a6;--g3:#d4d0c8;
  --red:#e53935;--grn:#22c55e;--blu:#3b82f6;--org:#f97316;--pur:#8b5cf6;
  --ok-bg:#f0fdf4;--ok-c:#16a34a;--ok-b:#bbf7d0;
  --wn-bg:#fefce8;--wn-c:#a16207;--wn-b:#fde68a;
  --er-bg:#fef2f2;--er-c:#dc2626;--er-b:#fecaca;
  --shd:0 1px 3px rgba(0,0,0,.06),0 4px 14px rgba(0,0,0,.04);
  --shd2:0 4px 24px rgba(0,0,0,.10);
  --r:14px;--rs:9px;
  --fh:'Syne',sans-serif;--fb:'Mulish',sans-serif;
}
[data-theme="dark"]{
  --bg:#0f1117;--sb:#161b22;--card:#161b22;--card2:#1c2230;
  --bdr:#2a303c;--bdr2:#222836;
  --ink:#e8edf5;--g1:#8892a4;--g2:#5a6880;--g3:#2e3847;
  --ok-bg:rgba(34,197,94,.08);--ok-c:#4ade80;--ok-b:rgba(34,197,94,.2);
  --wn-bg:rgba(245,197,24,.08);--wn-c:#fbbf24;--wn-b:rgba(245,197,24,.2);
  --er-bg:rgba(239,68,68,.08);--er-c:#f87171;--er-b:rgba(239,68,68,.2);
  --shd:0 1px 3px rgba(0,0,0,.3),0 4px 14px rgba(0,0,0,.2);
}
body{background:var(--bg);font-family:var(--fb);color:var(--ink);display:flex;min-height:100vh;overflow-x:hidden;transition:background .3s,color .3s}

/*==== SIDEBAR ====*/
.sb{width:220px;min-height:100vh;background:var(--sb);border-right:1px solid var(--bdr);display:flex;flex-direction:column;position:fixed;top:0;left:0;bottom:0;z-index:200;transition:width .25s,background .3s}
.sb.collapsed{width:64px}
.sb-logo{display:flex;align-items:center;gap:10px;padding:20px 16px 18px;border-bottom:1px solid var(--bdr);overflow:hidden;white-space:nowrap}
.logo-ico{width:34px;height:34px;background:var(--ink);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.logo-txt{font-family:var(--fh);font-size:14px;font-weight:700;color:var(--ink)}
.logo-sub{font-size:10px;color:var(--g2);letter-spacing:.4px}
.sb-search{margin:12px 10px 6px;position:relative}
.sb-search input{width:100%;background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:7px 10px 7px 28px;font-size:12px;font-family:var(--fb);color:var(--ink);outline:none;transition:background .3s,border .2s}
.sb-search input:focus{border-color:var(--y)}
.sb-search::before{content:'⌕';position:absolute;left:9px;top:50%;transform:translateY(-50%);font-size:13px;color:var(--g2)}
.nav-sec{flex:1;padding:6px 0;overflow-y:auto}
.nav-lbl{font-size:9px;font-weight:700;letter-spacing:1.8px;color:var(--g2);text-transform:uppercase;padding:10px 18px 4px;white-space:nowrap;overflow:hidden}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 16px;font-size:13px;font-weight:500;color:var(--g1);cursor:pointer;transition:all .15s;position:relative;white-space:nowrap;overflow:hidden;border-radius:0;text-decoration:none}
.nav-item:hover{background:var(--bg);color:var(--ink)}
.nav-item.active{background:var(--ink);color:#fff;border-radius:var(--rs);margin:2px 10px;padding:9px 10px}
[data-theme="dark"] .nav-item.active{background:var(--y);color:#1a1a1a}
.nav-ico{width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.nav-badge{margin-left:auto;background:var(--y);color:var(--ink);font-size:9px;font-weight:700;padding:2px 6px;border-radius:100px}
.sb-foot{padding:14px;border-top:1px solid var(--bdr)}
.user-card{display:flex;align-items:center;gap:9px;padding:9px;background:var(--bg);border-radius:var(--rs);cursor:pointer;overflow:hidden;white-space:nowrap}
.ua{width:32px;height:32px;background:linear-gradient(135deg,var(--y),var(--org));border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#1a1a1a;flex-shrink:0}
.un{font-size:13px;font-weight:600;color:var(--ink)}
.ur{font-size:10px;color:var(--g2)}
.sb-toggle{position:absolute;top:18px;right:-12px;width:24px;height:24px;background:var(--sb);border:1px solid var(--bdr);border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:11px;color:var(--g1);z-index:10;transition:background .2s}
.sb-toggle:hover{background:var(--bg)}

/*==== MAIN ====*/
.main{margin-left:220px;flex:1;min-height:100vh;display:flex;flex-direction:column;transition:margin .25s}
.main.expanded{margin-left:64px}

/*==== TOPBAR ====*/
.topbar{background:var(--sb);border-bottom:1px solid var(--bdr);padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;transition:background .3s}
.bc{font-size:12px;color:var(--g2);display:flex;align-items:center;gap:5px}
.bc b{color:var(--ink);font-weight:600}
.tr{display:flex;align-items:center;gap:10px}
.tb-btn{width:34px;height:34px;border:1px solid var(--bdr);border-radius:8px;background:transparent;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:15px;color:var(--g1);transition:background .15s}
.tb-btn:hover{background:var(--bg)}
.live-pill{display:flex;align-items:center;gap:5px;background:var(--ok-bg);border:1px solid var(--ok-b);color:var(--ok-c);font-size:11px;font-weight:700;padding:5px 11px;border-radius:100px;letter-spacing:.4px}
.ld{width:6px;height:6px;background:var(--ok-c);border-radius:50%;animation:blink 1.4s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.clock{font-family:var(--fh);font-size:12px;color:var(--g2);min-width:80px;text-align:right}

/*==== PAGE ====*/
.page{padding:24px;flex:1}

/*==== GREETING ====*/
.g-row{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:22px;flex-wrap:wrap;gap:14px}
.g-row h2{font-family:var(--fh);font-size:28px;font-weight:800;color:var(--ink);line-height:1.1}
.g-row p{font-size:12px;color:var(--g2);margin-top:3px}

/*==== FILTER BAR ====*/
.fbr{display:flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--bdr);border-radius:var(--rs);padding:4px}
.fb{padding:6px 14px;border-radius:7px;border:none;background:transparent;font-size:12px;font-weight:600;font-family:var(--fb);color:var(--g1);cursor:pointer;transition:all .15s;text-decoration:none}
.fb:hover{background:var(--bg);color:var(--ink)}
.fb.active{background:var(--ink);color:#fff}
[data-theme="dark"] .fb.active{background:var(--y);color:#1a1a1a}

/*==== STATUS STRIP ====*/
.sstatus{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--card);border:1px solid var(--bdr);border-radius:var(--rs);padding:10px 18px;margin-bottom:20px;box-shadow:var(--shd)}
.ssi{display:flex;align-items:center;gap:7px;font-size:11px;font-family:var(--fh);font-weight:600;color:var(--g1)}
.sdot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.sdiv{width:1px;height:16px;background:var(--bdr)}
.tag-ok  {color:var(--ok-c)}.tag-warn{color:var(--wn-c)}.tag-err{color:var(--er-c)}
.dot-ok  {background:var(--grn)}.dot-warn{background:var(--y)}.dot-err{background:var(--red)}

/*==== KPI TOP ROW ====*/
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr) 260px;gap:14px;margin-bottom:18px}
.kchip{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:16px 18px;box-shadow:var(--shd);transition:box-shadow .2s,transform .2s;position:relative;overflow:hidden}
.kchip:hover{box-shadow:var(--shd2);transform:translateY(-1px)}
.kchip::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px}
.kchip.v::after{background:linear-gradient(90deg,var(--blu),transparent)}
.kchip.i::after{background:linear-gradient(90deg,var(--org),transparent)}
.kchip.p::after{background:linear-gradient(90deg,var(--y),transparent)}
.kchip.e::after{background:linear-gradient(90deg,var(--grn),transparent)}
.kc-lbl{font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--g2);margin-bottom:6px;display:flex;align-items:center;gap:6px}
.kc-val{font-family:var(--fh);font-size:28px;font-weight:800;color:var(--ink);line-height:1;display:flex;align-items:baseline;gap:5px}
.kc-unit{font-size:13px;color:var(--g2);font-weight:500;font-family:var(--fb)}
.kc-sub{font-size:11px;color:var(--g2);margin-top:5px;display:flex;align-items:center;gap:5px}
.delta-up{color:var(--red);font-weight:700}.delta-dn{color:var(--grn);font-weight:700}

/*==== GAUGE CARD ====*/
.gauge-card{background:var(--yl);border:1px solid var(--y);border-radius:var(--r);padding:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:var(--shd);position:relative;overflow:hidden}
[data-theme="dark"] .gauge-card{background:rgba(245,197,24,.06);border-color:rgba(245,197,24,.25)}
.gauge-card::before{content:'';position:absolute;bottom:-30px;right:-30px;width:90px;height:90px;background:var(--y);border-radius:50%;opacity:.12}
.g-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--g1);margin-bottom:8px}
.gwrap{position:relative;width:120px;height:65px;overflow:hidden}
.garc{width:120px;height:120px}
.gval{position:absolute;bottom:0;left:50%;transform:translateX(-50%);text-align:center}
.gpct{font-family:var(--fh);font-size:20px;font-weight:800;color:var(--ink)}
.gsub{font-size:10px;color:var(--g1);font-weight:600}

/*==== MAIN GRID ====*/
.mgrid{display:grid;grid-template-columns:1fr 280px;gap:14px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:18px;box-shadow:var(--shd);transition:background .3s,border .3s}
.card-hdr{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:14px}
.card-ttl{font-family:var(--fh);font-size:14px;font-weight:700;color:var(--ink)}
.card-sub{font-size:11px;color:var(--g2);margin-top:2px}
.card-menu{width:28px;height:28px;border:1px solid var(--bdr);border-radius:7px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:14px;color:var(--g2);background:var(--bg)}
.big-v{font-family:var(--fh);font-size:38px;font-weight:800;color:var(--ink);line-height:1;display:flex;align-items:baseline;gap:7px}
.big-u{font-size:16px;color:var(--g2);font-weight:500}
.big-lbl{font-size:11px;color:var(--g2);margin-bottom:14px}
.comp-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:100px;font-size:11px;font-weight:700;margin-left:8px}
.comp-up{background:var(--er-bg);color:var(--er-c)}.comp-dn{background:var(--ok-bg);color:var(--ok-c)}

/*==== RIGHT COL ====*/
.rcol{display:flex;flex-direction:column;gap:14px}
.srow{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--bdr)}
.srow:last-child{border:none}
.sl{font-size:12px;color:var(--g1)}.sv{font-size:12px;font-weight:700;color:var(--ink);font-family:var(--fh)}

/*==== BARS ====*/
.bar-wrap{display:flex;align-items:flex-end;gap:8px;height:90px;margin:10px 0 6px}
.bi{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px}
.bf{width:100%;border-radius:5px 5px 0 0;min-height:4px;transition:height .4s ease}
.bl{font-size:9px;color:var(--g2);font-weight:600;text-align:center}
.bv{font-size:10px;font-weight:700;color:var(--ink)}

/*==== TILES ROW ====*/
.tiles{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:18px}
.tile{background:var(--card);border:1px solid var(--bdr);border-radius:var(--rs);padding:13px;box-shadow:var(--shd);transition:box-shadow .2s,transform .2s}
.tile:hover{box-shadow:var(--shd2);transform:translateY(-1px)}
.tile.hl{background:var(--yl);border-color:var(--y)}
[data-theme="dark"] .tile.hl{background:rgba(245,197,24,.08);border-color:rgba(245,197,24,.3)}
.t-lbl{font-size:10px;color:var(--g2);font-weight:600;text-transform:uppercase;letter-spacing:.6px;margin-bottom:5px}
.t-val{font-family:var(--fh);font-size:20px;font-weight:800;color:var(--ink);line-height:1}
.t-unit{font-size:10px;color:var(--g2);margin-top:2px}
.t-tag{display:inline-flex;align-items:center;gap:3px;font-size:10px;font-weight:700;margin-top:6px;padding:2px 7px;border-radius:100px}
.tt-ok{background:var(--ok-bg);color:var(--ok-c)}.tt-warn{background:var(--wn-bg);color:var(--wn-c)}.tt-err{background:var(--er-bg);color:var(--er-c)}

/*==== POWER TRIANGLE ====*/
.ptri-svg{width:100%;max-width:240px;margin:0 auto;display:block}

/*==== BOTTOM GRID ====*/
.bgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px}
.chart-full{margin-bottom:14px}

/*==== TABLE ====*/
table{width:100%;border-collapse:collapse}
thead th{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--g2);padding:7px 10px;text-align:left;border-bottom:1px solid var(--bdr);white-space:nowrap}
tbody tr{transition:background .12s}
tbody tr:hover{background:var(--card2)}
tbody td{padding:9px 10px;font-size:11px;font-weight:500;color:var(--ink);border-bottom:1px solid var(--bdr2)}
tbody tr:last-child td{border:none}
.tn{font-family:var(--fh);font-size:12px;font-weight:700}
.pill{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:100px;font-size:10px;font-weight:700}
.pill-ok{background:var(--ok-bg);color:var(--ok-c)}.pill-warn{background:var(--wn-bg);color:var(--wn-c)}.pill-err{background:var(--er-bg);color:var(--er-c)}

/*==== ALERTS ====*/
.alr{display:flex;align-items:flex-start;gap:9px;padding:9px 11px;border-radius:var(--rs);margin-bottom:7px;font-size:12px;font-weight:500;border-left:3px solid transparent}
.alr:last-child{margin:0}
.alr.ok{background:var(--ok-bg);color:var(--ok-c);border-color:var(--grn)}
.alr.warn{background:var(--wn-bg);color:var(--wn-c);border-color:var(--y)}
.alr.err{background:var(--er-bg);color:var(--er-c);border-color:var(--red)}
.alr-ico{font-size:13px;margin-top:1px;flex-shrink:0}

/*==== TOAST ====*/
#toast-container{position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{background:var(--card);border:1px solid var(--bdr);border-radius:var(--rs);padding:11px 16px;box-shadow:var(--shd2);font-size:12px;font-weight:500;display:flex;align-items:center;gap:9px;max-width:280px;animation:slideIn .3s ease;border-left:3px solid var(--grn)}
.toast.warn-t{border-color:var(--y)}.toast.err-t{border-color:var(--red)}
@keyframes slideIn{from{transform:translateX(60px);opacity:0}to{transform:translateX(0);opacity:1}}

/*==== SKELETON ====*/
.skel{background:linear-gradient(90deg,var(--bdr) 25%,var(--bg) 50%,var(--bdr) 75%);background-size:200% 100%;animation:shimmer 1.5s infinite;border-radius:6px;height:24px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/*==== FOOTER ====*/
footer{text-align:center;padding:14px 24px;font-size:11px;color:var(--g2);border-top:1px solid var(--bdr);font-family:var(--fb)}

/*==== RESPONSIVE ====*/
@media(max-width:1300px){.kpi-row{grid-template-columns:repeat(2,1fr) 1fr}.tiles{grid-template-columns:repeat(3,1fr)}}
@media(max-width:1000px){.mgrid,.bgrid{grid-template-columns:1fr}.sb{width:64px}.sb-logo .logo-txt,.sb-logo .logo-sub,.sb-search,.nav-lbl,.nav-item span:not(.nav-ico),.nav-badge,.user-card .un,.user-card .ur{display:none}.nav-item{padding:10px;justify-content:center;margin:2px 8px;border-radius:var(--rs)}.main{margin-left:64px}}
@media(max-width:640px){.kpi-row{grid-template-columns:1fr 1fr}.tiles{grid-template-columns:repeat(2,1fr)}.page{padding:14px}.g-row{flex-direction:column;align-items:flex-start}}
</style>
</head>
<body>

<!--==== SIDEBAR ====-->
<aside class="sb" id="sidebar">
  <div class="sb-toggle" onclick="toggleSidebar()">‹</div>
  <div class="sb-logo">
    <div class="logo-ico">⚡</div>
    <div><div class="logo-txt">EnergyPro</div><div class="logo-sub">v3.0 · 50Hz</div></div>
  </div>
  <div class="sb-search"><input type="text" placeholder="Search…"></div>
  <nav class="nav-sec">
    <a class="nav-item active" href="/"><div class="nav-ico">⊞</div><span>Dashboard</span></a>
    <a class="nav-item" href="/api/stats?range=today"><div class="nav-ico">📈</div><span>Analytics</span></a>
    <a class="nav-item" href="/?range=today"><div class="nav-ico">📅</div><span>History</span></a>
    <a class="nav-item" href="/api/export?range=today"><div class="nav-ico">📥</div><span>Export CSV</span><span class="nav-badge">↓</span></a>
    <div class="nav-lbl">Metrics</div>
    <a class="nav-item" href="/?range=week"><div class="nav-ico">🔋</div><span>Energy</span></a>
    <a class="nav-item" href="/?range=month"><div class="nav-ico">💰</div><span>Cost</span></a>
    <a class="nav-item" href="#alerts"><div class="nav-ico">🔔</div><span>Alerts</span></a>
    <div class="nav-lbl">System</div>
    <a class="nav-item" href="/api/latest"><div class="nav-ico">📡</div><span>MQTT API</span></a>
  </nav>
  <div class="sb-foot">
    <div class="user-card">
      <div class="ua">S</div>
      <div><div class="un">Subodh</div><div class="ur">Admin</div></div>
    </div>
  </div>
</aside>

<!--==== MAIN ====-->
<div class="main" id="main-panel">
  <div class="topbar">
    <div class="bc">Home &rsaquo; <b>Dashboard</b></div>
    <div class="tr">
      <div class="live-pill"><div class="ld"></div>LIVE</div>
      <div class="clock" id="live-clock">{{ current_time[-8:] }}</div>
      <button class="tb-btn" onclick="toggleTheme()" title="Toggle theme">🌓</button>
      <a class="tb-btn" href="/api/export?range={{ range }}" title="Export CSV">↓</a>
    </div>
  </div>

  <div class="page">

    <!--==== GREETING + FILTER ====-->
    <div class="g-row">
      <div>
        <h2>Good {{ greeting }}, Subodh</h2>
        <p>{{ current_time }} &nbsp;·&nbsp; {{ total_readings }} readings &nbsp;·&nbsp; {{ range_count }} in view</p>
      </div>
      <div class="fbr">
        <a href="?range=live"  class="fb {% if range=='live' %}active{% endif %}">Live</a>
        <a href="?range=today" class="fb {% if range=='today' %}active{% endif %}">Today</a>
        <a href="?range=week"  class="fb {% if range=='week' %}active{% endif %}">Week</a>
        <a href="?range=month" class="fb {% if range=='month' %}active{% endif %}">Month</a>
        <a href="?range=all"   class="fb {% if range=='all' %}active{% endif %}">All</a>
      </div>
    </div>

    <!--==== STATUS STRIP ====-->
    <div class="sstatus">
      <div class="ssi"><div class="sdot dot-{{ vs_cls }}"></div>VOLTAGE: <span class="tag-{{ vs_cls }}">{{ vs_txt }}</span></div>
      <div class="sdiv"></div>
      <div class="ssi"><div class="sdot dot-{{ pfs_cls }}"></div>PF: <span class="tag-{{ pfs_cls }}">{{ pfs_txt }}</span></div>
      <div class="sdiv"></div>
      <div class="ssi"><div class="sdot dot-{{ thds_cls }}"></div>THD: <span class="tag-{{ thds_cls }}">{{ thds_txt }}</span></div>
      <div class="sdiv"></div>
      <div class="ssi"><div class="sdot dot-{{ ls_cls }}"></div>LOAD: <span class="tag-{{ ls_cls }}">{{ ls_txt }}</span></div>
      <div class="sdiv"></div>
      <div class="ssi"><div class="sdot dot-ok"></div>FREQ: <span class="tag-ok">{{ freq }} Hz</span></div>
      <div class="sdiv"></div>
      <div class="ssi"><div class="sdot dot-ok"></div>MQTT: <span class="tag-ok">CONNECTED</span></div>
    </div>

    <!--==== KPI TOP ROW ====-->
    <div class="kpi-row">
      <div class="kchip v">
        <div class="kc-lbl">🔌 Voltage</div>
        <div class="kc-val" id="kv">{{ lv }}<span class="kc-unit">V</span></div>
        <div class="kc-sub">Nominal 230V &nbsp;·&nbsp; <span class="tag-{{ vs_cls }}">{{ vs_txt }}</span></div>
      </div>
      <div class="kchip i">
        <div class="kc-lbl">〰 Current</div>
        <div class="kc-val" id="ki">{{ li }}<span class="kc-unit">A</span></div>
        <div class="kc-sub">Peak: {{ max_i }} A</div>
      </div>
      <div class="kchip p">
        <div class="kc-lbl">⚡ Active Power</div>
        <div class="kc-val" id="kp">{{ lp }}
          <span class="kc-unit">W</span>
          {% if power_delta != 0 %}
          <span class="comp-badge {% if power_delta > 0 %}comp-up{% else %}comp-dn{% endif %}">
            {% if power_delta > 0 %}↑{% else %}↓{% endif %} {{ power_delta_pct|abs }}%
          </span>
          {% endif %}
        </div>
        <div class="kc-sub">vs Yesterday: {{ yest_p }} W</div>
      </div>
      <div class="kchip e">
        <div class="kc-lbl">🔋 Energy ({{ range_label }})</div>
        <div class="kc-val" id="ke">{{ period_e }}<span class="kc-unit">kWh</span></div>
        <div class="kc-sub">Cost: ₹{{ period_cost }}</div>
      </div>
      <!--Power Factor Gauge-->
      <div class="gauge-card">
        <div class="g-title">Power Factor</div>
        <div class="gwrap">
          <svg class="garc" viewBox="0 0 120 120">
            <path d="M 10 95 A 55 55 0 1 1 110 95" fill="none" stroke="var(--bdr)" stroke-width="9" stroke-linecap="round"/>
            <path d="M 10 95 A 55 55 0 1 1 110 95" fill="none" stroke="var(--ink)" stroke-width="9" stroke-linecap="round"
                  stroke-dasharray="157" stroke-dashoffset="{{ pf_dashoffset }}" id="pf-arc"/>
          </svg>
          <div class="gval"><div class="gpct" id="gpct">{{ pf_pct }}%</div><div class="gsub">{{ pfs_txt }}</div></div>
        </div>
      </div>
    </div>

    <!--==== MAIN GRID ====-->
    <div class="mgrid">
      <!--Power trend chart-->
      <div class="card">
        <div class="card-hdr">
          <div>
            <div style="font-size:10px;color:var(--g2);font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px">{{ range_label }}</div>
            <div class="big-v" id="bv">{{ avg_p }}<span class="big-u">W avg</span>
              {% if power_delta > 0 %}<span class="comp-badge comp-up">↑{{ power_delta_pct }}%</span>
              {% elif power_delta < 0 %}<span class="comp-badge comp-dn">↓{{ power_delta_pct|abs }}%</span>{% endif %}
            </div>
            <div class="big-lbl">Active Power · P, Q, S — {{ range_label }}</div>
          </div>
          <div class="card-menu">···</div>
        </div>
        <canvas id="powerChart" height="150"></canvas>
      </div>

      <!--Right column-->
      <div class="rcol">
        <!--Load bars-->
        <div class="card">
          <div class="card-hdr">
            <div><div class="card-ttl">Load Utilisation</div><div class="card-sub">{{ ls_txt }} · {{ llp }}% of {{ max_load|int }}W</div></div>
            <div class="card-menu">···</div>
          </div>
          <div style="font-size:24px;font-family:var(--fh);font-weight:800;color:var(--ink)">
            {{ llp }}<span style="font-size:13px;color:var(--g2);font-weight:500">%</span>
          </div>
          <div class="bar-wrap">
            {% for b in load_bars %}
            <div class="bi">
              <div class="bv">{{ b.pct }}%</div>
              <div class="bf" style="height:{{ b.h }}px;background:{{ b.color }}"></div>
              <div class="bl">{{ b.ts }}</div>
            </div>
            {% endfor %}
          </div>
        </div>
        <!--Cost summary-->
        <div class="card">
          <div class="card-hdr"><div class="card-ttl">Cost (Slab Tariff)</div><div class="card-menu">···</div></div>
          <div class="srow"><span class="sl">Today</span><span class="sv">₹{{ cost_today }}</span></div>
          <div class="srow"><span class="sl">This period</span><span class="sv">₹{{ period_cost }}</span></div>
          <div class="srow"><span class="sl">Monthly proj.</span><span class="sv">₹{{ monthly_cost }}</span></div>
          <div class="srow"><span class="sl">Tariff basis</span><span class="sv">Slab</span></div>
          <div class="srow"><span class="sl">CO₂ est.</span><span class="sv">{{ co2 }} kg</span></div>
        </div>
      </div>
    </div>

    <!--==== TILES — all KPIs ====-->
    <div class="tiles">
      <div class="tile">
        <div class="t-lbl">Reactive Power</div>
        <div class="t-val" id="tlq">{{ lq }}</div>
        <div class="t-unit">VAR</div>
      </div>
      <div class="tile">
        <div class="t-lbl">Apparent Power</div>
        <div class="t-val" id="tls">{{ ls }}</div>
        <div class="t-unit">VA</div>
      </div>
      <div class="tile">
        <div class="t-lbl">Voltage THD</div>
        <div class="t-val" id="tlt">{{ lt }}</div>
        <div class="t-unit">%</div>
        <div class="t-tag tt-{{ thds_cls }}">{{ thds_txt }}</div>
      </div>
      <div class="tile hl">
        <div class="t-lbl">Energy Today</div>
        <div class="t-val">{{ energy_today }}</div>
        <div class="t-unit">kWh &nbsp;·&nbsp; ₹{{ cost_today }}</div>
      </div>
      <div class="tile">
        <div class="t-lbl">Peak Demand</div>
        <div class="t-val">{{ peak_demand }}</div>
        <div class="t-unit">kW (15-min)</div>
      </div>
      <div class="tile">
        <div class="t-lbl">Frequency</div>
        <div class="t-val">{{ freq }}</div>
        <div class="t-unit">Hz (fixed)</div>
        <div class="t-tag tt-ok">Stable</div>
      </div>
    </div>

    <!--==== BOTTOM GRID ====-->
    <div class="bgrid">
      <!--Voltage & Current chart-->
      <div class="card">
        <div class="card-hdr">
          <div><div class="card-ttl">Voltage & Current</div><div class="card-sub">Dual-axis · {{ range_label }}</div></div>
          <div class="card-menu">···</div>
        </div>
        <canvas id="vcChart" height="160"></canvas>
      </div>
      <!--PF & THD chart-->
      <div class="card">
        <div class="card-hdr">
          <div><div class="card-ttl">Power Factor & THD</div><div class="card-sub">Power quality · {{ range_label }}</div></div>
          <div class="card-menu">···</div>
        </div>
        <canvas id="pfThdChart" height="160"></canvas>
      </div>
    </div>

    <!--==== POWER TRIANGLE + DEMAND ====-->
    <div class="bgrid">
      <!--Power triangle-->
      <div class="card">
        <div class="card-hdr">
          <div><div class="card-ttl">Power Triangle</div><div class="card-sub">P · Q · S relationship</div></div>
          <div class="card-menu">···</div>
        </div>
        <svg class="ptri-svg" viewBox="0 0 300 160" id="ptri-svg">
          <!-- Base: Apparent power (hypotenuse) -->
          <defs>
            <marker id="ah" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L0,6 L8,3 z" fill="var(--g2)"/>
            </marker>
          </defs>
          <!-- Active power (horizontal) -->
          <line x1="30" y1="130" x2="230" y2="130" stroke="var(--grn)" stroke-width="3" stroke-linecap="round" marker-end="url(#ah)"/>
          <text x="120" y="148" text-anchor="middle" font-size="11" fill="var(--grn)" font-family="Syne" font-weight="700">P = {{ lp }}W</text>
          <!-- Reactive power (vertical) -->
          <line x1="230" y1="130" x2="230" y2="50" stroke="var(--pur)" stroke-width="3" stroke-linecap="round" marker-end="url(#ah)"/>
          <text x="258" y="95" text-anchor="middle" font-size="11" fill="var(--pur)" font-family="Syne" font-weight="700" transform="rotate(90,258,95)">Q = {{ lq }}VAR</text>
          <!-- Apparent power (hypotenuse) -->
          <line x1="30" y1="130" x2="230" y2="50" stroke="var(--org)" stroke-width="3" stroke-linecap="round" stroke-dasharray="6,3" marker-end="url(#ah)"/>
          <text x="115" y="82" text-anchor="middle" font-size="11" fill="var(--org)" font-family="Syne" font-weight="700" transform="rotate(-24,115,82)">S = {{ ls }}VA</text>
          <!-- Angle arc -->
          <path d="M 90 130 A 60 60 0 0 0 {{ pf_angle|round|int }} 96" fill="none" stroke="var(--y)" stroke-width="1.5" stroke-dasharray="4,2"/>
          <text x="75" y="115" font-size="10" fill="var(--yd)" font-family="Syne" font-weight="700">φ={{ pf_angle }}°</text>
          <!-- PF label -->
          <text x="150" y="25" text-anchor="middle" font-size="12" fill="var(--ink)" font-family="Syne" font-weight="700">PF = cos(φ) = {{ lpf }}</text>
        </svg>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:12px">
          <div style="text-align:center"><div style="font-size:10px;color:var(--g2);text-transform:uppercase;letter-spacing:.5px">Active P</div><div style="font-family:var(--fh);font-size:15px;font-weight:700;color:var(--grn)">{{ lp }} W</div></div>
          <div style="text-align:center"><div style="font-size:10px;color:var(--g2);text-transform:uppercase;letter-spacing:.5px">Reactive Q</div><div style="font-family:var(--fh);font-size:15px;font-weight:700;color:var(--pur)">{{ lq }} VAR</div></div>
          <div style="text-align:center"><div style="font-size:10px;color:var(--g2);text-transform:uppercase;letter-spacing:.5px">Apparent S</div><div style="font-family:var(--fh);font-size:15px;font-weight:700;color:var(--org)">{{ ls }} VA</div></div>
        </div>
      </div>
      <!--Demand interval chart-->
      <div class="card">
        <div class="card-hdr">
          <div><div class="card-ttl">Demand Intervals</div><div class="card-sub">15-min avg kW · Peak: {{ peak_demand }} kW</div></div>
          <div class="card-menu">···</div>
        </div>
        <canvas id="demandChart" height="160"></canvas>
      </div>
    </div>

    <!--==== ENERGY CHART full width ====-->
    <div class="card chart-full">
      <div class="card-hdr">
        <div><div class="card-ttl">Energy Accumulation</div><div class="card-sub">Cumulative kWh · {{ range_label }}</div></div>
        <div class="card-menu">···</div>
      </div>
      <canvas id="energyChart" height="80"></canvas>
    </div>

    <!--==== ALERTS ====-->
    <div class="card chart-full" id="alerts">
      <div class="card-hdr"><div class="card-ttl">System Alerts</div><div class="card-menu">···</div></div>
      {% for a in alerts %}
      <div class="alr {{ a.cls }}"><span class="alr-ico">{{ a.icon }}</span><span>{{ a.msg }}</span></div>
      {% endfor %}
    </div>

    <!--==== SESSION STATS ====-->
    <div class="bgrid">
      <div class="card">
        <div class="card-hdr"><div class="card-ttl">Session Statistics</div></div>
        <div class="srow"><span class="sl">Avg Voltage</span><span class="sv">{{ avg_v }} V</span></div>
        <div class="srow"><span class="sl">Min / Max Voltage</span><span class="sv">{{ min_v }} / {{ max_v }} V</span></div>
        <div class="srow"><span class="sl">Max Current</span><span class="sv">{{ max_i }} A</span></div>
        <div class="srow"><span class="sl">Avg Power</span><span class="sv">{{ avg_p }} W</span></div>
        <div class="srow"><span class="sl">Min / Max Power</span><span class="sv">{{ min_p }} / {{ max_p }} W</span></div>
        <div class="srow"><span class="sl">Avg Power Factor</span><span class="sv">{{ avg_pf }}</span></div>
        <div class="srow"><span class="sl">Avg THD</span><span class="sv">{{ avg_thd }}%</span></div>
        <div class="srow"><span class="sl">Peak Demand (15-min)</span><span class="sv">{{ peak_demand }} kW</span></div>
        <div class="srow"><span class="sl">Efficiency</span><span class="sv">{{ efficiency }}%</span></div>
        <div class="srow"><span class="sl">Monthly Proj.</span><span class="sv">{{ monthly_kwh }} kWh · ₹{{ monthly_cost }}</span></div>
      </div>
      <div class="card">
        <div class="card-hdr"><div class="card-ttl">Yesterday vs Today</div></div>
        <div class="srow"><span class="sl">Yesterday avg power</span><span class="sv">{{ yest_p }} W</span></div>
        <div class="srow"><span class="sl">Yesterday energy</span><span class="sv">{{ yest_e }} kWh</span></div>
        <div class="srow"><span class="sl">Today energy</span><span class="sv">{{ energy_today }} kWh</span></div>
        <div class="srow"><span class="sl">Today cost (slab)</span><span class="sv">₹{{ cost_today }}</span></div>
        <div class="srow"><span class="sl">Power Δ</span>
          <span class="sv {% if power_delta > 0 %}tag-err{% else %}tag-ok{% endif %}">
            {% if power_delta > 0 %}+{% endif %}{{ power_delta }} W ({{ power_delta_pct }}%)
          </span>
        </div>
        <div class="srow"><span class="sl">CO₂ emitted</span><span class="sv">{{ co2 }} kg</span></div>
        <div class="srow"><span class="sl">Frequency</span><span class="sv">{{ freq }} Hz</span></div>
      </div>
    </div>

    <!--==== READINGS TABLE ====-->
    <div class="card chart-full">
      <div class="card-hdr">
        <div><div class="card-ttl">Recent Readings</div><div class="card-sub">All computed KPIs per reading</div></div>
        <a href="/api/export?range={{ range }}" style="font-size:12px;color:var(--g1);font-weight:600;text-decoration:none;border:1px solid var(--bdr);padding:5px 12px;border-radius:var(--rs)">Export ↓</a>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th><th>V (V)</th><th>I (A)</th><th>P (W)</th>
              <th>Q (VAR)</th><th>S (VA)</th><th>PF</th><th>THD%</th>
              <th>kWh</th><th>Load%</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {% for row in table_rows %}
            <tr>
              <td style="color:var(--g2);font-size:10px;white-space:nowrap">{{ row.ts }}</td>
              <td class="tn">{{ row.v }}</td><td class="tn">{{ row.i }}</td>
              <td class="tn">{{ row.p }}</td><td class="tn">{{ row.q }}</td>
              <td class="tn">{{ row.s }}</td><td class="tn">{{ row.pf }}</td>
              <td class="tn">{{ row.thd }}</td><td class="tn">{{ row.e }}</td>
              <td class="tn">{{ row.lp }}%</td>
              <td><span class="pill {{ row.pill }}">{{ row.status }}</span></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

  </div><!--/page-->
  <footer>EnergyMonitor Pro v3.0 &nbsp;·&nbsp; MQTT: {{ topic }} &nbsp;·&nbsp; Filter: {{ range_label }} &nbsp;·&nbsp; Auto-refresh via fetch</footer>
</div>

<div id="toast-container"></div>

<script>
/*==== DATA ====*/
const TS   = {{ c_ts|tojson }};
const CV   = {{ c_v|tojson }};
const CI   = {{ c_i|tojson }};
const CP   = {{ c_p|tojson }};
const CQ   = {{ c_q|tojson }};
const CS   = {{ c_s|tojson }};
const CPF  = {{ c_pf|tojson }};
const CTHD = {{ c_thd|tojson }};
const CE   = {{ c_e|tojson }};
const DL   = {{ demand_labels|tojson }};
const DV   = {{ demand_values|tojson }};

/*==== THEME ====*/
function toggleTheme(){
  const d=document.documentElement;
  const t=d.getAttribute('data-theme')==='dark'?'light':'dark';
  d.setAttribute('data-theme',t);
  localStorage.setItem('theme',t);
  updateChartThemes();
}
(function(){
  const t=localStorage.getItem('theme')||'light';
  document.documentElement.setAttribute('data-theme',t);
})();

/*==== SIDEBAR TOGGLE ====*/
function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('collapsed');
  document.getElementById('main-panel').classList.toggle('expanded');
}

/*==== LIVE CLOCK ====*/
function tickClock(){
  const n=new Date();
  document.getElementById('live-clock').textContent=
    n.toTimeString().slice(0,8);
}
setInterval(tickClock,1000); tickClock();

/*==== TOAST ====*/
let prevAlertState={};
function showToast(msg,type='ok'){
  const c=document.getElementById('toast-container');
  const t=document.createElement('div');
  t.className='toast'+(type==='warn'?' warn-t':type==='err'?' err-t':'');
  t.innerHTML=(type==='ok'?'✓':type==='warn'?'⚠':'✗')+' '+msg;
  c.appendChild(t);
  setTimeout(()=>t.remove(),4000);
}

/*==== ANIMATED COUNTER ====*/
function animateVal(el, from, to, decimals=2, duration=600){
  const start=performance.now();
  const diff=to-from;
  function step(now){
    const p=Math.min((now-start)/duration,1);
    const ease=p<.5?2*p*p:(4-2*p)*p-1;
    el.childNodes[0].textContent=(from+diff*ease).toFixed(decimals);
    if(p<1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/*==== CHART OPTS ====*/
function getThemeColors(){
  const s=getComputedStyle(document.documentElement);
  return {
    grid:  s.getPropertyValue('--bdr').trim()||'#e5e1d8',
    tick:  s.getPropertyValue('--g2').trim()||'#9199a6',
    ink:   s.getPropertyValue('--ink').trim()||'#1a1a1a',
  };
}

const baseOpts=(extra={})=>({
  responsive:true,
  interaction:{mode:'index',intersect:false},
  plugins:{
    legend:{labels:{color:getThemeColors().tick,font:{family:'Mulish',size:11,weight:'600'},boxWidth:10,boxHeight:10}},
    tooltip:{backgroundColor:getThemeColors().ink,titleColor:'#fff',bodyColor:'#9199a6',
      borderColor:'rgba(255,255,255,.08)',borderWidth:1,
      titleFont:{family:'Syne',size:12,weight:'700'},bodyFont:{family:'Mulish',size:12},
      padding:12,cornerRadius:10}
  },
  scales:{
    x:{ticks:{color:getThemeColors().tick,font:{family:'Mulish',size:9},maxTicksLimit:8,maxRotation:0},
       grid:{color:getThemeColors().grid}},
    y:{ticks:{color:getThemeColors().tick,font:{family:'Mulish',size:10}},
       grid:{color:getThemeColors().grid}},
    ...extra
  }
});

/*==== CHARTS ====*/
const charts={};

charts.power = new Chart(document.getElementById('powerChart'),{
  type:'line',
  data:{labels:TS,datasets:[
    {label:'P Active (W)',data:CP,borderColor:'#f5c518',backgroundColor:'rgba(245,197,24,.10)',fill:true,tension:.4,borderWidth:2.5,pointRadius:0,pointHoverRadius:5},
    {label:'Q Reactive (VAR)',data:CQ,borderColor:'#8b5cf6',backgroundColor:'rgba(139,92,246,.07)',fill:true,tension:.4,borderWidth:1.5,pointRadius:0,pointHoverRadius:5},
    {label:'S Apparent (VA)',data:CS,borderColor:'#f97316',backgroundColor:'rgba(249,115,22,.05)',fill:false,tension:.4,borderWidth:1.5,borderDash:[5,3],pointRadius:0,pointHoverRadius:5},
  ]},
  options:baseOpts()
});

charts.vc = new Chart(document.getElementById('vcChart'),{
  type:'line',
  data:{labels:TS,datasets:[
    {label:'Voltage (V)',data:CV,borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,.07)',fill:true,tension:.4,borderWidth:2,pointRadius:0,pointHoverRadius:5},
    {label:'Current (A)',data:CI,borderColor:'#f97316',backgroundColor:'rgba(249,115,22,.07)',fill:true,tension:.4,borderWidth:2,pointRadius:0,pointHoverRadius:5,yAxisID:'y2'},
  ]},
  options:baseOpts({y2:{position:'right',ticks:{color:'#f97316',font:{family:'Mulish',size:10}},grid:{drawOnChartArea:false}}})
});

charts.pfthd = new Chart(document.getElementById('pfThdChart'),{
  type:'line',
  data:{labels:TS,datasets:[
    {label:'Power Factor',data:CPF,borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,.08)',fill:true,tension:.4,borderWidth:2,pointRadius:0,pointHoverRadius:5},
    {label:'THD% / 100',data:CTHD.map(v=>v/100),borderColor:'#e53935',backgroundColor:'rgba(229,57,53,.07)',fill:true,tension:.4,borderWidth:2,pointRadius:0,pointHoverRadius:5,yAxisID:'y2'},
  ]},
  options:baseOpts({y2:{position:'right',ticks:{color:'#e53935',font:{family:'Mulish',size:10}},grid:{drawOnChartArea:false}}})
});

charts.demand = new Chart(document.getElementById('demandChart'),{
  type:'bar',
  data:{labels:DL,datasets:[
    {label:'Avg kW (15-min)',data:DV,backgroundColor:'rgba(245,197,24,.7)',borderColor:'#f5c518',borderWidth:1.5,borderRadius:5},
  ]},
  options:{...baseOpts(),scales:{...baseOpts().scales,y:{...baseOpts().scales.y,title:{display:true,text:'kW',color:getThemeColors().tick,font:{family:'Mulish',size:10}}}}}
});

charts.energy = new Chart(document.getElementById('energyChart'),{
  type:'line',
  data:{labels:TS,datasets:[
    {label:'Energy (kWh)',data:CE,borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,.10)',fill:true,tension:.4,borderWidth:2.5,pointRadius:0,pointHoverRadius:5},
  ]},
  options:baseOpts()
});

function updateChartThemes(){
  Object.values(charts).forEach(ch=>{
    const tc=getThemeColors();
    if(ch.options.scales.x){ch.options.scales.x.ticks.color=tc.tick;ch.options.scales.x.grid.color=tc.grid}
    if(ch.options.scales.y){ch.options.scales.y.ticks.color=tc.tick;ch.options.scales.y.grid.color=tc.grid}
    ch.options.plugins.tooltip.backgroundColor=tc.ink;
    ch.options.plugins.legend.labels.color=tc.tick;
    ch.update('none');
  });
}

/*==== FETCH POLLING (no hard reload) ====*/
let prevData=null;
async function poll(){
  try{
    const res=await fetch('/api/latest');
    if(!res.ok)return;
    const d=await res.json();
    if(!d.voltage)return;

    // Animated KPI updates
    function updEl(id,val,dec=2){
      const el=document.getElementById(id);
      if(!el)return;
      const cur=parseFloat(el.childNodes[0]?.textContent)||0;
      animateVal(el,cur,val,dec);
    }
    updEl('kv',d.voltage,2); updEl('ki',d.current,3);
    updEl('kp',d.power,2);   updEl('ke',d.energy_kwh,4);
    updEl('tlq',d.reactive_power,2);
    updEl('tls',d.apparent_power,2);
    updEl('tlt',d.thd_v,2);

    // PF gauge
    const pf=d.power_factor||0;
    const offset=(157*(1-pf)).toFixed(1);
    document.getElementById('pf-arc').setAttribute('stroke-dashoffset',offset);
    document.getElementById('gpct').textContent=Math.round(pf*100)+'%';

    // Alert on state change
    if(prevData){
      if(d.voltage>250 && prevData.voltage<=250) showToast('High voltage: '+d.voltage+'V','err');
      if(d.load_pct>90 && prevData.load_pct<=90) showToast('Critical load: '+d.load_pct+'%','err');
      if(d.thd_v>15 && prevData.thd_v<=15) showToast('High THD: '+d.thd_v+'%','warn');
      if(d.power_factor<0.7 && prevData.power_factor>=0.7) showToast('Poor power factor: '+d.power_factor,'warn');
    }
    prevData=d;
  }catch(e){console.warn('poll error',e)}
}
setInterval(poll,5000); poll();
</script>
</body>
</html>
"""


def get_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_lock:
        conn = get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voltage REAL DEFAULT 0, current REAL DEFAULT 0,
                power REAL DEFAULT 0, reactive_power REAL DEFAULT 0,
                apparent_power REAL DEFAULT 0, power_factor REAL DEFAULT 0,
                thd_v REAL DEFAULT 0, frequency REAL DEFAULT 50,
                energy_kwh REAL DEFAULT 0, peak_demand_kw REAL DEFAULT 0,
                load_pct REAL DEFAULT 0, timestamp TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON readings(timestamp)")
        conn.commit(); conn.close()

def save_reading(d):
    with db_lock:
        conn = get_db()
        conn.execute("""
            INSERT INTO readings
              (voltage,current,power,reactive_power,apparent_power,
               power_factor,thd_v,frequency,energy_kwh,peak_demand_kw,load_pct,timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (d.get("voltage",0), d.get("current",0), d.get("power",0),
              d.get("reactive_power",0), d.get("apparent_power",0),
              d.get("power_factor",0), d.get("thd_v",0), d.get("frequency",50),
              d.get("energy_kwh",0), d.get("peak_demand_kw",0),
              d.get("load_pct",0),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); conn.close()

def calc_slab_cost(kwh):
    cost = 0.0; remaining = kwh; prev = 0
    for limit, rate in SLABS:
        if remaining <= 0: break
        slab_size = limit - prev if limit != float("inf") else remaining
        consumed  = min(remaining, slab_size)
        cost     += consumed * rate
        remaining -= consumed; prev = limit if limit != float("inf") else prev
    return round(cost, 2)

def on_message(client, userdata, msg):
    global latest_data
    try:
        raw = json.loads(msg.payload.decode())

        voltage = float(raw.get("voltage", 0))
        current = float(raw.get("current", 0))
        power   = float(raw.get("power",   0))

        # Compute missing fields from V, I, P
        apparent = round(voltage * current, 2)
        reactive = round(math.sqrt(max(0.0, apparent**2 - power**2)), 2) if apparent >= abs(power) else 0.0
        true_pf  = round(max(0.0, min(1.0, power / apparent)), 4) if apparent > 1e-6 else 0.0
        phi_deg  = round(math.acos(max(-1.0, min(1.0, true_pf))) * 180.0 / math.pi, 2) if true_pf > 0 else 0.0
        load_pct = round((power / MAX_LOAD) * 100.0, 1) if power > 0 else 0.0

        d = {
            "voltage":         voltage,
            "current":         current,
            "power":           power,
            # Use ESP32 value if non-zero, otherwise use computed
            "apparent_power":  float(raw.get("apparent_power",  0)) or apparent,
            "reactive_power":  float(raw.get("reactive_power",  0)) or reactive,
            "power_factor":    float(raw.get("power_factor",    0)) or true_pf,
            "displacement_pf": float(raw.get("displacement_pf", 0)) or true_pf,
            "phi_degrees":     float(raw.get("phi_degrees",     0)) or phi_deg,
            "pf_type":         raw.get("pf_type", "Unknown"),
            "thd_v":           float(raw.get("thd_v", 0)),
            "thd_i":           float(raw.get("thd_i", 0)),
            "frequency":       float(raw.get("frequency", 50)),
            "energy_kwh":      float(raw.get("energy_kwh", 0)),
            "peak_demand_kw":  float(raw.get("peak_demand_kw", 0)),
            "load_pct":        float(raw.get("load_pct", 0)) or load_pct,
        }

        latest_data = d
        save_reading(d)

        print("RX: V={:.1f}V  I={:.3f}A  P={:.1f}W  S={:.1f}VA  Q={:.1f}VAR  PF={:.4f}  phi={:.1f}°  Load={:.1f}%".format(
            d["voltage"], d["current"], d["power"],
            d["apparent_power"], d["reactive_power"],
            d["power_factor"], d["phi_degrees"], d["load_pct"]))

    except Exception as e:
        print("MQTT parse error:", e)

def mqtt_thread():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.subscribe(TOPIC)
    print("MQTT listening:", TOPIC)
    client.loop_forever()

def time_filter(r):
    now = datetime.now()
    if r=="today":  return now.replace(hour=0,minute=0,second=0).strftime("%Y-%m-%d %H:%M:%S"),"Today"
    if r=="week":   return (now-timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),"Last 7 Days"
    if r=="month":  return (now-timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"),"Last 30 Days"
    if r=="all":    return "2000-01-01 00:00:00","All Time"
    return (now-timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),"Last Hour"

def greeting():
    h=datetime.now().hour
    return "Morning" if h<12 else ("Afternoon" if h<17 else "Evening")

def volt_status(v):
    if 210<=v<=250: return "Normal","ok"
    return ("High","err") if v>250 else ("Low","warn")

def pf_status(pf):
    if pf>=0.95: return "Excellent","ok"
    if pf>=0.85: return "Good","ok"
    if pf>=0.70: return "Fair","warn"
    return "Poor","err"

def thd_status(t):
    if t<5:  return "Excellent","ok"
    if t<8:  return "Good","ok"
    if t<15: return "Fair","warn"
    return "Poor","err"

def load_status(p):
    if p<60:  return "Normal","ok"
    if p<80:  return "High","warn"
    return "Critical","err"

app = Flask(__name__)

@app.route("/stream")
def stream():
    def gen():
        import time
        while True:
            if latest_data:
                yield f"data: {json.dumps(latest_data)}\n\n"
            time.sleep(1)
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/api/latest")
def api_latest():
    with db_lock:
        conn=get_db()
        row=conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
    return jsonify(dict(row)) if row else jsonify({})

@app.route("/api/history")
def api_history():
    r=request.args.get("range","live")
    since,_=time_filter(r)
    limit=int(request.args.get("limit",200))
    with db_lock:
        conn=get_db()
        rows=conn.execute("SELECT * FROM readings WHERE timestamp>=? ORDER BY id ASC LIMIT ?",(since,limit)).fetchall()
        conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/stats")
def api_stats():
    r=request.args.get("range","today"); since,label=time_filter(r)
    with db_lock:
        conn=get_db()
        s=conn.execute("""SELECT COUNT(*) as cnt,
          MIN(voltage) as min_v,MAX(voltage) as max_v,AVG(voltage) as avg_v,
          MIN(current) as min_i,MAX(current) as max_i,
          MIN(power) as min_p,MAX(power) as max_p,AVG(power) as avg_p,
          AVG(power_factor) as avg_pf,AVG(thd_v) as avg_thd,
          MAX(peak_demand_kw) as peak_demand,
          MAX(energy_kwh) as max_e,MIN(energy_kwh) as min_e
          FROM readings WHERE timestamp>=?""",(since,)).fetchone()
        conn.close()
    d=dict(s); d["range"]=label
    d["energy_period"]=round((d["max_e"] or 0)-(d["min_e"] or 0),4)
    d["cost_period"]=calc_slab_cost(d["energy_period"])
    return jsonify(d)

@app.route("/api/export")
def api_export():
    r=request.args.get("range","today"); since,_=time_filter(r)
    with db_lock:
        conn=get_db()
        rows=conn.execute("SELECT * FROM readings WHERE timestamp>=? ORDER BY id ASC",(since,)).fetchall()
        conn.close()
    lines=["id,voltage,current,power,reactive_power,apparent_power,power_factor,thd_v,frequency,energy_kwh,peak_demand_kw,load_pct,timestamp"]
    for row in rows:
        lines.append(",".join(str(row[k]) for k in row.keys()))
    return Response("\n".join(lines),mimetype="text/csv",
                    headers={"Content-Disposition":f"attachment;filename=energy_{r}.csv"})

@app.route("/")
def dashboard():
    r=request.args.get("range","live"); since,range_label=time_filter(r)
    with db_lock:
        conn=get_db()
        rows=conn.execute("SELECT * FROM readings WHERE timestamp>=? ORDER BY id ASC LIMIT 200",(since,)).fetchall()
        latest=conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1").fetchone()
        total_cnt=conn.execute("SELECT COUNT(*) as c FROM readings").fetchone()["c"]
        stats=conn.execute("""SELECT COUNT(*) as cnt,
          MIN(voltage) as min_v,MAX(voltage) as max_v,AVG(voltage) as avg_v,
          MIN(current) as min_i,MAX(current) as max_i,
          MIN(power) as min_p,MAX(power) as max_p,AVG(power) as avg_p,
          AVG(power_factor) as avg_pf,AVG(thd_v) as avg_thd,
          MAX(peak_demand_kw) as peak_demand,
          MAX(energy_kwh) as max_e,MIN(energy_kwh) as min_e
          FROM readings WHERE timestamp>=?""",(since,)).fetchone()
        yest_start=(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d 00:00:00")
        yest_end=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d 23:59:59")
        yest=conn.execute("SELECT AVG(power) as avg_p,MAX(energy_kwh)-MIN(energy_kwh) as energy FROM readings WHERE timestamp BETWEEN ? AND ?",(yest_start,yest_end)).fetchone()
        demand_rows=conn.execute("""SELECT strftime('%H:%M',timestamp) as slot, AVG(power)/1000.0 as avg_kw
          FROM readings WHERE timestamp>=datetime('now','-3 hours')
          GROUP BY strftime('%Y-%m-%d %H:',timestamp)||printf('%02d',(cast(strftime('%M',timestamp) as int)/15)*15)
          ORDER BY slot ASC LIMIT 12""").fetchall()
        conn.close()
    rows=[dict(rw) for rw in rows]
    lv=round(latest["voltage"],2) if latest else 0
    li=round(latest["current"],3) if latest else 0
    lp=round(latest["power"],2) if latest else 0
    lq=round(latest["reactive_power"],2) if latest else 0
    ls_=round(latest["apparent_power"],2) if latest else 0
    lpf=round(latest["power_factor"],3) if latest else 0
    lt=round(latest["thd_v"],2) if latest else 0
    le=round(latest["energy_kwh"],4) if latest else 0
    lpd=round(latest["peak_demand_kw"],3) if latest else 0
    llp=round(latest["load_pct"],1) if latest else 0
    vs_txt,vs_cls=volt_status(lv)
    pfs_txt,pfs_cls=pf_status(lpf)
    thds_txt,thds_cls=thd_status(lt)
    lss_txt,lss_cls=load_status(llp)
    period_e=round((stats["max_e"] or 0)-(stats["min_e"] or 0),4)
    period_cost=calc_slab_cost(period_e)
    today_str=datetime.now().strftime("%Y-%m-%d")
    with db_lock:
        conn=get_db()
        te=conn.execute("SELECT MIN(energy_kwh) as mn,MAX(energy_kwh) as mx FROM readings WHERE timestamp LIKE ?",(f"{today_str}%",)).fetchone()
        conn.close()
    energy_today=round((te["mx"] or 0)-(te["mn"] or 0),4) if te["mx"] else 0
    cost_today=calc_slab_cost(energy_today)
    monthly_kwh=round(((stats["avg_p"] or 0)*24*30)/1000,2)
    monthly_cost=calc_slab_cost(monthly_kwh)
    co2=round(le*0.82,3)
    yest_p=round(yest["avg_p"] or 0,2); yest_e=round(yest["energy"] or 0,4)
    power_delta=round(lp-yest_p,2) if yest_p else 0
    power_delta_pct=round((power_delta/yest_p*100),1) if yest_p>0 else 0
    step=max(1,len(rows)//100); cr=rows[::step]
    c_ts=[r["timestamp"][-8:] for r in cr]
    c_v=[r["voltage"] for r in cr]; c_i=[r["current"] for r in cr]
    c_p=[r["power"] for r in cr]; c_q=[r["reactive_power"] for r in cr]
    c_s=[r["apparent_power"] for r in cr]; c_pf=[r["power_factor"] for r in cr]
    c_thd=[r["thd_v"] for r in cr]; c_e=[r["energy_kwh"] for r in cr]
    pf_angle=math.acos(max(-1,min(1,lpf)))*180/math.pi if lpf!=0 else 0
    load_bars=[]
    for rw in rows[-8:]:
        pct=round(rw["power"]/MAX_LOAD*100,1)
        color="#22c55e" if pct<60 else ("#f5c842" if pct<80 else "#ef4444")
        load_bars.append({"pct":pct,"h":max(4,int(pct)),"color":color,"ts":rw["timestamp"][-5:]})
    demand_labels=[dict(d)["slot"] for d in demand_rows]
    demand_values=[round(dict(d)["avg_kw"],3) for d in demand_rows]
    avg_v=round(stats["avg_v"] or 0,2); min_v=round(stats["min_v"] or 0,2); max_v=round(stats["max_v"] or 0,2)
    avg_p=round(stats["avg_p"] or 0,2); max_p=round(stats["max_p"] or 0,2); min_p=round(stats["min_p"] or 0,2)
    avg_pf=round(stats["avg_pf"] or 0,3); avg_thd=round(stats["avg_thd"] or 0,2)
    peak_d=round(stats["peak_demand"] or 0,3); max_i=round(stats["max_i"] or 0,3)
    alerts=[]
    def alert(cls,icon,msg): alerts.append({"cls":cls,"icon":icon,"msg":msg})
    if vs_cls=="ok":     alert("ok","✓",f"Voltage normal at {lv} V (210–250V range)")
    elif vs_cls=="err":  alert("err","✗",f"HIGH voltage: {lv} V — check supply")
    else:                alert("warn","!",f"Low voltage: {lv} V — possible brownout")
    if pfs_cls=="ok":    alert("ok","✓",f"Power factor {lpf} — {pfs_txt}")
    elif pfs_cls=="warn":alert("warn","!",f"Fair PF {lpf} — consider power factor correction")
    else:                alert("err","✗",f"Poor PF {lpf} — high reactive losses")
    if thds_cls=="ok":   alert("ok","✓",f"THD {lt}% — {thds_txt} waveform quality")
    elif thds_cls=="warn":alert("warn","!",f"THD {lt}% — non-linear loads present")
    else:                alert("err","✗",f"THD {lt}% — significant harmonic distortion")
    if lss_cls=="ok":    alert("ok","✓",f"Load normal at {llp}%")
    elif lss_cls=="warn":alert("warn","!",f"High load {llp}% — approaching capacity")
    else:                alert("err","✗",f"CRITICAL load {llp}% — risk of overload")
    table_rows=[]
    for rw in reversed(rows[-12:]):
        v=rw["voltage"]; _,vc=volt_status(v)
        table_rows.append({"ts":rw["timestamp"],"v":round(v,2),"i":round(rw["current"],3),
            "p":round(rw["power"],2),"q":round(rw["reactive_power"],2),"s":round(rw["apparent_power"],2),
            "pf":round(rw["power_factor"],3),"thd":round(rw["thd_v"],2),
            "e":round(rw["energy_kwh"],4),"lp":round(rw["load_pct"],1),
            "pill":"pill-ok" if vc=="ok" else ("pill-warn" if vc=="warn" else "pill-err"),
            "status":"Normal" if vc=="ok" else ("Low V" if lv<210 else "High V")})
    return render_template_string(HTML_TEMPLATE,
        current_time=datetime.now().strftime("%A, %d %B %Y · %H:%M:%S"),
        greeting=greeting(), range=r, range_label=range_label,
        total_readings=total_cnt, range_count=len(rows), topic=TOPIC,
        lv=lv,li=li,lp=lp,lq=lq,ls=ls_,lpf=lpf,lt=lt,le=le,lpd=lpd,llp=llp,freq=FREQUENCY,
        vs_txt=vs_txt,vs_cls=vs_cls,pfs_txt=pfs_txt,pfs_cls=pfs_cls,
        thds_txt=thds_txt,thds_cls=thds_cls,ls_txt=lss_txt,ls_cls=lss_cls,
        efficiency=round(lpf*100,1),pf_pct=round(lpf*100),
        pf_dashoffset=round(157*(1-lpf),1),pf_angle=round(pf_angle,1),
        energy_today=energy_today,cost_today=cost_today,
        monthly_kwh=monthly_kwh,monthly_cost=monthly_cost,
        co2=co2,rate=RATE,period_e=period_e,period_cost=period_cost,
        yest_p=yest_p,yest_e=yest_e,power_delta=power_delta,power_delta_pct=power_delta_pct,
        avg_v=avg_v,min_v=min_v,max_v=max_v,avg_p=avg_p,max_p=max_p,min_p=min_p,
        avg_pf=avg_pf,avg_thd=avg_thd,peak_demand=peak_d,max_i=max_i,
        c_ts=c_ts,c_v=c_v,c_i=c_i,c_p=c_p,c_q=c_q,c_s=c_s,c_pf=c_pf,c_thd=c_thd,c_e=c_e,
        demand_labels=demand_labels,demand_values=demand_values,
        load_bars=load_bars,alerts=alerts,table_rows=table_rows,max_load=MAX_LOAD)

if __name__ == "__main__":
    init_db()
    Thread(target=mqtt_thread, daemon=True).start()
    import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=False)
