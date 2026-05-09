#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════╗
║   🏔️  藏语→中文 实时翻译  桌面版 v2.1    ║
║                                          ║
║   双击运行 · 自动开浏览器 · Ctrl+C 退出   ║
╚══════════════════════════════════════════╝

功能:
  - 🎙️ 语音输入: 麦克风实时采集藏语语音 → 翻译为中文
  - ⌨️ 键盘输入: 手动输入/粘贴藏文文本 → 翻译
  - 📷 图片OCR: 上传含藏文的图片 → 识别 → 翻译

依赖: Python 3.8+ (无需安装任何第三方库)
系统: Windows / macOS / Linux

v2.1 更新:
  - 修复 TCPServer allow_reuse_address 时序 bug (端口复用)
  - 修复翻译队列并发 bug (ti 标志未正确设置)
  - 移除 MyMemory 翻译引擎 (藏语返回垃圾数据)
  - Tesseract.js 延迟加载 (仅首次使用 OCR 时加载)
  - 添加 fetch 超时控制 (10 秒)
  - 添加 favicon.ico 1x1 透明像素 (避免 404)
  - 添加翻译队列版本号 (切换标签页时取消旧翻译)
  - OCR 错误信息展示具体原因
  - 修复 index.html 同步所有修复
"""

import http.server
import socketserver
import webbrowser
import threading
import signal
import sys
import os
import socket
import time
import subprocess
import base64

# ============================================================
#  藏语→中文 实时翻译 — 完整网页 (内嵌)
# ============================================================

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>藏语→中文 实时翻译</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏔️</text></svg>">
<style>
:root{--bg:#0a0a12;--s1:#12121e;--s2:#1a1a2e;--bd:rgba(255,255,255,.06);--ac:#7c6aef;--ac2:rgba(124,106,239,.15);--ac3:rgba(124,106,239,.4);--tx:#eae8f4;--tx2:#7a7890;--dg:#ef4444;--dg2:rgba(239,68,68,.15);--sg:#22c55e;--sg2:rgba(34,197,94,.15);--r:14px;--rs:8px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"SF Pro Display","PingFang SC","Microsoft YaHei","Noto Sans Tibetan",sans-serif;background:var(--bg);color:var(--tx);min-height:100dvh;display:flex;flex-direction:column;overflow:hidden}

.hd{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid var(--bd);background:rgba(10,10,18,.85);backdrop-filter:blur(16px);flex-shrink:0;z-index:100}
.logo{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:700}
.logo i{font-size:26px;font-style:normal}
.sp{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:500;background:var(--s2);color:var(--tx2);transition:all .3s}
.sp.on{background:var(--sg2);color:var(--sg)}
.sp.err{background:var(--dg2);color:var(--dg)}
.sp b{width:7px;height:7px;border-radius:50%;background:currentColor;display:block}
.sp.on b{animation:bl 1.4s infinite}
@keyframes bl{0%,100%{opacity:1}50%{opacity:.35}}

.tb{display:flex;gap:2px;padding:6px 20px 0;border-bottom:1px solid var(--bd);background:var(--bg);flex-shrink:0}
.t{padding:10px 18px;font-size:13px;font-weight:500;color:var(--tx2);border:none;background:none;cursor:pointer;border-bottom:2px solid transparent;transition:all .2s;display:flex;align-items:center;gap:6px;position:relative;bottom:-1px}
.t:hover{color:var(--tx)}.t.at{color:var(--ac);border-bottom-color:var(--ac)}
.t i{font-size:16px;font-style:normal}

.mn{flex:1;display:flex;flex-direction:column;overflow:hidden}
.pn{display:none;flex:1;flex-direction:column;overflow:hidden}.pn.at{display:flex}

.sa{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:10px;scroll-behavior:smooth}
.sa::-webkit-scrollbar{width:5px}.sa::-webkit-scrollbar-track{background:transparent}.sa::-webkit-scrollbar-thumb{background:var(--ac);border-radius:3px}

.se{padding:14px 18px;border-radius:10px;animation:fu .25s ease-out;max-width:100%}
@keyframes fu{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.st{background:#161628;border-left:3px solid var(--ac);font-size:18px;line-height:1.9;font-family:"Noto Sans Tibetan","Microsoft Himalaya","Qomolangma-Uchen Sarchen",serif;word-break:break-word}
.sc{background:#0f1f35;border-left:3px solid var(--sg);font-size:19px;line-height:1.7;font-weight:500;word-break:break-word}
.sl{font-size:10px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:5px;display:flex;align-items:center;gap:5px}
.st .sl{color:var(--ac)}.sc .sl{color:var(--sg)}
.sm{font-size:10px;color:var(--tx2);margin-top:6px;display:flex;justify-content:space-between}
.se.lv{position:relative}.se.lv::after{content:'';position:absolute;top:10px;right:10px;width:6px;height:6px;background:var(--dg);border-radius:50%;animation:bl 1s infinite}

.emp{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;color:var(--tx2);text-align:center;padding:40px}
.emp .ic{font-size:52px;opacity:.45}.emp p{font-size:14px;line-height:1.7}
.emp .ht{font-size:12px;background:var(--s2);padding:8px 16px;border-radius:8px;margin-top:4px}

.ib{display:flex;align-items:center;gap:12px;padding:14px 20px;border-top:1px solid var(--bd);background:var(--s1);flex-shrink:0}
.mb{width:54px;height:54px;border-radius:50%;border:2px solid var(--ac);background:transparent;color:var(--ac);font-size:22px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .25s;flex-shrink:0}
.mb:hover{background:var(--ac);color:#fff;box-shadow:0 0 24px var(--ac3)}
.mb.rc{background:var(--dg);border-color:var(--dg);color:#fff;animation:mp 1.4s infinite}
@keyframes mp{0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.35)}50%{box-shadow:0 0 0 14px rgba(239,68,68,0)}}
.mi{flex:1;min-width:0}.mi .l1{font-size:12px;color:var(--tx2);margin-bottom:3px}.mi .l2{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-height:20px}
.bc{padding:8px 14px;border-radius:var(--rs);border:1px solid var(--bd);background:transparent;color:var(--tx2);font-size:12px;cursor:pointer;transition:all .2s;flex-shrink:0}
.bc:hover{border-color:var(--tx2);color:var(--tx)}

.kw{flex-shrink:0;padding:16px 20px;border-top:1px solid var(--bd);background:var(--s1)}
.kt{width:100%;min-height:80px;max-height:160px;padding:12px 14px;border-radius:var(--rs);border:1px solid var(--bd);background:var(--bg);color:var(--tx);font-size:16px;font-family:"Noto Sans Tibetan","Microsoft Himalaya",serif;line-height:1.8;resize:vertical;outline:none;transition:border-color .2s}
.kt:focus{border-color:var(--ac)}.kt::placeholder{color:var(--tx2);font-family:inherit}
.ka{display:flex;justify-content:space-between;align-items:center;margin-top:10px}
.ka .lt{font-size:12px;color:var(--tx2)}
.bm{padding:10px 28px;border-radius:var(--rs);border:none;background:var(--ac);color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:all .2s}
.bm:hover{box-shadow:0 0 20px var(--ac3)}.bm:disabled{opacity:.4;cursor:default}

.ow{flex-shrink:0;padding:16px 20px;border-top:1px solid var(--bd);background:var(--s1);display:flex;flex-direction:column;gap:12px}
.uz{border:2px dashed var(--bd);border-radius:var(--r);padding:30px 20px;text-align:center;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.uz:hover,.uz.drag{border-color:var(--ac);background:var(--ac2)}
.uz .ic{font-size:36px;margin-bottom:8px}.uz p{font-size:13px;color:var(--tx2)}
.uz input{position:absolute;inset:0;opacity:0;cursor:pointer}
.opv{max-height:200px;border-radius:var(--rs);object-fit:contain;display:none;margin:0 auto;border:1px solid var(--bd)}
.oa{display:flex;gap:10px;justify-content:flex-end}
.bo{padding:10px 24px;border-radius:var(--rs);border:none;background:var(--ac);color:#fff;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s}
.bo:hover{box-shadow:0 0 16px var(--ac3)}.bo:disabled{opacity:.4;cursor:default}
.bo.bs{background:transparent;border:1px solid var(--bd);color:var(--tx2)}
.bo.bs:hover{border-color:var(--tx2);color:var(--tx)}
.opr{display:none;align-items:center;gap:10px;font-size:13px;color:var(--tx2)}.opr.sh{display:flex}
.spn{width:18px;height:18px;border:2px solid var(--bd);border-top-color:var(--ac);border-radius:50%;animation:rn .7s linear infinite}
@keyframes rn{to{transform:rotate(360deg)}}

.tst{position:fixed;bottom:90px;left:50%;transform:translateX(-50%) translateY(16px);background:var(--s2);border:1px solid var(--bd);padding:10px 20px;border-radius:10px;font-size:13px;opacity:0;transition:all .25s;pointer-events:none;z-index:200;white-space:nowrap}
.tst.sh{opacity:1;transform:translateX(-50%) translateY(0)}

.ft{text-align:center;padding:6px;font-size:11px;color:var(--tx2);opacity:.5;flex-shrink:0}

@media(max-width:600px){.hd{padding:10px 14px}.logo{font-size:15px}.t{padding:8px 12px;font-size:12px}.st{font-size:16px}.sc{font-size:17px}.mb{width:48px;height:48px;font-size:20px}}
</style>
</head>
<body>

<div class="hd">
  <div class="logo"><i>🏔️</i><span>藏语→中文 实时翻译</span></div>
  <div class="sp" id="sp"><b></b><span id="st">就绪</span></div>
</div>

<div class="tb">
  <button class="t at" data-t="v"><i>🎙️</i> 语音</button>
  <button class="t" data-t="k"><i>⌨️</i> 键盘</button>
  <button class="t" data-t="o"><i>📷</i> 图片OCR</button>
</div>

<div class="mn">
  <div class="pn at" id="pv">
    <div class="sa" id="vs"><div class="emp"><div class="ic">🎙️</div><p>点击下方麦克风按钮<br>开始说藏语，实时显示中文字幕</p><div class="ht">💡 空格键快速开始/停止</div></div></div>
    <div class="ib">
      <button class="mb" id="mb" title="开始/停止录音">🎤</button>
      <div class="mi"><div class="l1">藏语语音 → 中文字幕</div><div class="l2" id="lt"></div></div>
      <button class="bc" onclick="clr('v')">清空</button>
    </div>
  </div>

  <div class="pn" id="pk">
    <div class="sa" id="ks"><div class="emp"><div class="ic">⌨️</div><p>在下方输入藏文，点击翻译<br>支持粘贴大段藏语文本</p><div class="ht">💡 Ctrl+Enter 快速翻译</div></div></div>
    <div class="kw">
      <textarea class="kt" id="ki" placeholder="在此输入或粘贴藏文…" rows="3"></textarea>
      <div class="ka"><span class="lt" id="kc">0 字</span><button class="bm" id="kb" onclick="doK()">翻译</button></div>
    </div>
  </div>

  <div class="pn" id="po">
    <div class="sa" id="os"><div class="emp"><div class="ic">📷</div><p>上传含有藏文的图片<br>自动识别藏文并翻译为中文</p><div class="ht">💡 支持拍照、截图、扫描件</div></div></div>
    <div class="ow">
      <div class="uz" id="uz"><input type="file" id="fi" accept="image/*" onchange="hf(event)"><div class="ic">📤</div><p>点击上传或拖拽图片到此处</p></div>
      <img class="opv" id="opv">
      <div class="opr" id="opr"><div class="spn"></div><span id="opt">正在识别藏文…</span></div>
      <div class="oa">
        <button class="bo bs" id="ocb" onclick="clrO()" style="display:none">清除图片</button>
        <button class="bo" id="ob" onclick="doO()" disabled>识别并翻译</button>
      </div>
    </div>
  </div>
</div>

<div class="ft">藏语→中文实时翻译 · 桌面版 v2.1</div>
<div class="tst" id="tst"></div>

<script>
// ============================================================
//  State & Config
// ============================================================
const $ = id => document.getElementById(id);
let rec = false, RC = null;
let tq = [], ti = false, ois = null;
const tc = new Map();
let qVersion = 0; // 翻译队列版本号，切换标签页时递增取消旧任务
let tesseractLoaded = false; // Tesseract.js 延迟加载标志

// ============================================================
//  Toast & Status
// ============================================================
function ts(m, n = 2500) {
  const t = $('tst');
  t.textContent = m;
  t.classList.add('sh');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('sh'), n);
}
function ss(s, t) {
  const p = $('sp');
  p.className = 'sp' + (s === 'on' ? ' on' : s === 'err' ? ' err' : '');
  $('st').textContent = t;
}

// ============================================================
//  Tabs — 切换时递增 qVersion 取消旧翻译
// ============================================================
document.querySelectorAll('.t').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.t').forEach(x => x.classList.remove('at'));
    document.querySelectorAll('.pn').forEach(x => x.classList.remove('at'));
    b.classList.add('at');
    $('p' + b.dataset.t).classList.add('at');
    // 切换标签页时取消队列中旧的翻译任务
    qVersion++;
    tq.length = 0;
    ti = false;
  });
});

// ============================================================
//  Subtitle Rendering
// ============================================================
function ad(c, tb, cn, s) {
  const a = $(c + 's'), e = a.querySelector('.emp');
  if (e) e.remove();
  a.querySelectorAll('.se.lv').forEach(x => x.classList.remove('lv'));
  const n = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const sl = { google: 'Google', cache: '缓存' }[s] || s;
  const td = document.createElement('div');
  td.className = 'se st lv';
  td.innerHTML = `<div class="sl">🗣️ 藏语原文</div><div>${esc(tb)}</div><div class="sm"><span>${n}</span></div>`;
  a.appendChild(td);
  const cd = document.createElement('div');
  cd.className = 'se sc';
  cd.innerHTML = `<div class="sl">📝 中文翻译</div><div>${esc(cn)}</div><div class="sm"><span>来源: ${sl}</span></div>`;
  a.appendChild(cd);
  a.scrollTop = a.scrollHeight;
}
function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function clr(c) {
  const a = $(c + 's');
  if (!a) return;
  const ic = { v: '🎙️', k: '⌨️', o: '📷' };
  const tx = {
    v: '点击下方麦克风按钮<br>开始说藏语，实时显示中文字幕',
    k: '在下方输入藏文，点击翻译<br>支持粘贴大段藏语文本',
    o: '上传含有藏文的图片<br>自动识别藏文并翻译为中文'
  };
  a.innerHTML = `<div class="emp"><div class="ic">${ic[c]}</div><p>${tx[c]}</p></div>`;
  ts('已清空');
}

// ============================================================
//  Translation Engine (Google only — MyMemory removed)
//  v2.1: 添加 10s 超时，移除不可靠的 MyMemory
// ============================================================
async function translateGoogle(text, timeout = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const r = await fetch(
      `https://translate.googleapis.com/translate_a/single?client=gtx&sl=bo&tl=zh-CN&dt=t&q=${encodeURIComponent(text)}`,
      { signal: controller.signal }
    );
    if (!r.ok) throw new Error('Google HTTP ' + r.status);
    const d = await r.json();
    if (d?.[0]) return d[0].map(s => s[0]).join('');
    throw new Error('Google empty response');
  } finally {
    clearTimeout(timer);
  }
}

async function translate(text) {
  if (!text.trim()) return { text: '', src: 'none' };
  const key = text.trim();
  if (tc.has(key)) return { text: tc.get(key), src: 'cache' };

  try {
    const t = await translateGoogle(text);
    tc.set(key, t);
    return { text: t, src: 'google' };
  } catch (e) {
    console.warn('Google failed:', e.message);
  }

  return { text: '[翻译失败] ' + text, src: 'none' };
}

// v2.1: 修复并发 bug — 正确设置 ti 标志 + 版本号检查
async function pq() {
  if (ti || !tq.length) return;
  ti = true;
  const ver = qVersion;
  while (tq.length) {
    // 版本号变了（标签页切换），丢弃剩余队列
    if (ver !== qVersion) break;
    const { text, container } = tq.shift();
    const r = await translate(text);
    if (ver !== qVersion) break; // 翻译完成后再次检查
    ad(container, text, r.text, r.src);
  }
  ti = false;
}
function qt(t, c = 'v') {
  tq.push({ text: t, container: c });
  pq();
}

// ============================================================
//  Panel 1: VOICE
// ============================================================
function initRec() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { ts('⚠️ 浏览器不支持语音识别，请用 Chrome'); return null; }
  const r = new SR();
  r.lang = 'bo';
  r.continuous = true;
  r.interimResults = true;
  r.maxAlternatives = 1;

  r.onstart = () => { ss('on', '正在聆听藏语…'); $('mb').classList.add('rc'); };
  r.onresult = (e) => {
    let interim = '', final = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t; else interim += t;
    }
    $('lt').textContent = interim || final;
    if (final) { $('lt').textContent = ''; qt(final); }
  };
  r.onerror = (e) => {
    if (e.error === 'not-allowed') { ts('❌ 请允许麦克风权限'); ss('err', '麦克风被拒绝'); stopRec(); }
    else if (e.error === 'network') { ts('⚠️ 网络错误'); ss('err', '网络错误'); }
  };
  r.onend = () => { if (rec) { try { r.start(); } catch (e) { stopRec(); } } };
  return r;
}

function startRec() {
  if (rec) return;
  RC = initRec();
  if (!RC) return;
  rec = true;
  try { RC.start(); ts('🎙️ 开始监听藏语语音'); } catch (e) { rec = false; ss('err', '启动失败'); }
}
function stopRec() {
  rec = false;
  if (RC) { RC.onend = null; try { RC.stop(); } catch (e) { } RC = null; }
  $('mb').classList.remove('rc');
  $('lt').textContent = '';
  ss('', '就绪');
  ts('⏹️ 已停止录音');
}
function toggleRec() { rec ? stopRec() : startRec(); }

$('mb').addEventListener('click', toggleRec);
document.addEventListener('keydown', e => {
  if (e.code === 'Space' && !e.repeat && e.target === document.body) { e.preventDefault(); toggleRec(); }
});

// ============================================================
//  Panel 2: KEYBOARD
// ============================================================
const ki = $('ki');
ki.addEventListener('input', () => { $('kc').textContent = ki.value.length + ' 字'; });
$('kb').addEventListener('click', doK);
ki.addEventListener('keydown', e => { if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); doK(); } });

async function doK() {
  const t = ki.value.trim();
  if (!t) { ts('请输入藏文'); return; }
  const b = $('kb');
  b.disabled = true; b.textContent = '翻译中…';
  try {
    const r = await translate(t);
    ad('k', t, r.text, r.src);
    ki.value = '';
    $('kc').textContent = '0 字';
  } catch (e) { ts('翻译失败'); }
  finally { b.disabled = false; b.textContent = '翻译'; }
}

// ============================================================
//  Panel 3: OCR — Tesseract.js 延迟加载
// ============================================================
const uz = $('uz'), opv = $('opv'), ob = $('ob'), ocb = $('ocb'), opr = $('opr'), opt = $('opt');

// Tesseract.js 延迟加载：仅首次使用 OCR 时加载
async function ensureTesseract() {
  if (tesseractLoaded && typeof Tesseract !== 'undefined') return true;
  opt.textContent = '正在加载 OCR 引擎（约 1MB）…';
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';
    script.onload = () => { tesseractLoaded = true; resolve(true); };
    script.onerror = () => reject(new Error('OCR 引擎加载失败，请检查网络'));
    document.head.appendChild(script);
  });
}

uz.addEventListener('dragover', e => { e.preventDefault(); uz.classList.add('drag'); });
uz.addEventListener('dragleave', () => uz.classList.remove('drag'));
uz.addEventListener('drop', e => {
  e.preventDefault(); uz.classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('image/')) lI(f);
});
function hf(e) { const f = e.target.files[0]; if (f) lI(f); }

function lI(f) {
  const r = new FileReader();
  r.onload = e => {
    ois = e.target.result;
    opv.src = ois;
    opv.style.display = 'block';
    uz.style.display = 'none';
    ocb.style.display = 'inline-block';
    ob.disabled = false;
  };
  r.readAsDataURL(f);
}
function clrO() {
  ois = null;
  opv.style.display = 'none';
  uz.style.display = 'block';
  ocb.style.display = 'none';
  ob.disabled = true;
  $('fi').value = '';
}

async function doO() {
  if (!ois) return;
  ob.disabled = true;
  opr.classList.add('sh');

  try {
    // 延迟加载 Tesseract.js
    await ensureTesseract();

    opt.textContent = '正在识别藏文（可能需要 10-30 秒）…';
    const result = await Tesseract.recognize(ois, 'bod', {
      logger: m => {
        if (m.status === 'recognizing text') opt.textContent = `正在识别藏文… ${Math.round(m.progress * 100)}%`;
      }
    });
    const text = result.data.text.trim();
    if (!text) {
      ts('⚠️ 未识别到文字，请确保图片中藏文清晰');
      opr.classList.remove('sh');
      ob.disabled = false;
      return;
    }

    opt.textContent = '正在翻译…';
    const r = await translate(text);
    ad('o', text, r.text, r.src);
    ts('✅ 识别并翻译完成');
  } catch (e) {
    console.error('OCR error:', e);
    ts('❌ OCR 失败：' + (e.message || '未知错误'));
  } finally {
    opr.classList.remove('sh');
    ob.disabled = false;
  }
}

// ============================================================
//  Init
// ============================================================
(function () {
  const ok = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  if (!ok) { ss('err', '浏览器不支持语音识别'); $('mb').style.opacity = '.3'; $('mb').style.pointerEvents = 'none'; }
})();
</script>
</body>
</html>'''

# ============================================================
#  HTTP 服务器 — v2.1: 修复 allow_reuse_address 时序
# ============================================================

class ReusableTCPServer(socketserver.TCPServer):
    """在 bind 之前设置 allow_reuse_address，修复端口复用 bug"""
    allow_reuse_address = True
    allow_reuse_port = False


# 预生成 1x1 透明 favicon (避免每次请求返回完整 HTML)
FAVICON_ICO = (
    b'\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00'
    b'\x30\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00'
    b'\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
)


class Handler(http.server.BaseHTTPRequestHandler):
    """HTTP Handler — favicon.ico 返回 1x1 透明像素，其他返回内嵌 HTML"""

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(200)
            self.send_header('Content-Type', 'image/x-icon')
            self.send_header('Content-Length', len(FAVICON_ICO))
            self.send_header('Cache-Control', 'max-age=86400')
            self.end_headers()
            self.wfile.write(FAVICON_ICO)
            return

        body = HTML.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        """支持 HEAD 请求（健康检查等场景）"""
        body = HTML.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()

    def log_message(self, fmt, *args):
        pass  # 静默


def find_port(start=9090):
    """找一个可用端口"""
    for p in range(start, start + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    return start


def main():
    port = find_port()
    url = f'http://127.0.0.1:{port}'

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║  🏔️  藏语→中文 实时翻译  桌面版 v2.1 ║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  地址: {url:<28s} ║")
    print("  ║  状态: ✅ 运行中                      ║")
    print("  ║  退出: Ctrl+C                        ║")
    print("  ╚══════════════════════════════════════╝")
    print()

    # 启动服务 — 使用 ReusableTCPServer 修复端口复用
    with ReusableTCPServer(('127.0.0.1', port), Handler) as server:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        # 等待服务器就绪（最多 2 秒）
        for _ in range(20):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.1)

        # 打开浏览器（检查返回值 + 多种回退方式）
        opened = False
        try:
            opened = webbrowser.open(url)
        except Exception:
            pass

        if not opened:
            # 回退：尝试系统命令直接打开
            try:
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    opened = True
                elif sys.platform == 'win32':
                    os.startfile(url)
                    opened = True
                elif sys.platform.startswith('linux'):
                    subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    opened = True
            except Exception:
                pass

        if opened:
            print("  ✅ 已在浏览器中打开翻译页面")
        else:
            print(f"  ⚠️  浏览器未自动打开，请手动访问: {url}")

        print()
        print("  功能:")
        print("    🎙️  语音  — 麦克风实时采集藏语，翻译为中文字幕")
        print("    ⌨️  键盘  — 输入/粘贴藏文文本，点击翻译")
        print("    📷  OCR  — 上传含藏文图片，识别+翻译")
        print()
        print("  v2.1 优化:")
        print("    ✅ 端口复用修复")
        print("    ✅ 翻译队列并发修复")
        print("    ✅ 移除不可靠的 MyMemory 引擎")
        print("    ✅ Tesseract.js 延迟加载")
        print("    ✅ 翻译超时控制 (10s)")
        print()

        # 优雅退出
        def stop(sig=None, frame=None):
            print("\n  ⏹️  正在关闭服务...")
            server.shutdown()
            print("  👋 已退出，再见！\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        try:
            threading.Event().wait()  # 永久等待
        except (KeyboardInterrupt, SystemExit):
            stop()


if __name__ == '__main__':
    main()
