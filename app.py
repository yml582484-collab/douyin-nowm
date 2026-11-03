# -*- coding: utf-8 -*-
"""
抖音无水印视频解析工具（仅供个人学习使用，请勿传播/商用）
启动后：电脑访问 http://127.0.0.1:8765
        手机(同一WiFi)访问 http://<电脑IP>:8765
"""
import json
import re
import socket
import threading
from urllib.parse import quote

import requests
from flask import Flask, request, jsonify, Response, abort

app = Flask(__name__)

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
PC_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

URL_RE = re.compile(r'https?://[^\s，。、""\'<>【】（）\(\)]+')
ID_PATTERNS = [
    re.compile(r'(?:video|slides|note)/(\d{15,25})'),
    re.compile(r'modal_id=(\d{15,25})'),
    re.compile(r'\b(\d{19})\b'),
]

# 只允许代理抖音系域名，防止接口被滥用
ALLOWED_HOSTS = ('douyin.com', 'douyinpic.com', 'iesdouyin.com', 'zjcdn.com',
                 'snssdk.com', 'bytecdn.cn', 'byteimg.com', 'amemv.com', 'pstatp.com')

# 主屏幕图标（Pillow 生成，base64 内嵌）
ICON_180_B64 = "iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAADtUlEQVR4nO3dMW4TURiFURvRUZgoiAZRUrIJFsEiWQSboIMS0SAksoNBLsaMQ4Jje2bee/edU00kF6Po09Vf2dvd7nbYQIhnpV8A5iRoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgidJt0K9/fDv6++7u1+H599sPBd6IOXQb9Bj1NOx91GPY+6iF3Z6ug35srbdfPh2eRd2W7W53O2w6dD/iry9uHvzc8P7j4fnm++fF34vrWOgTrHVbLPSJhZ6y1vUT9BlBj4RdLyfHBZwh9bLQFyz0lLWui4W+krWui4W+cqGnrHV5gp4x6JGwy3FyLMAZUo6FXmChp6z1uiz0wqz1uiz0wgs9Za2XJ+gVgx4JezlOjgKcIcux0AUWespaz8tCF2at52WhCy/0lLW+nqArCnok7Ms5OSrkDLmcha5woaes9XksdOWs9XksdOULPWWtTxN0Q0GPhP04J0eDnCGPs9ANLvSUtT5moRtnrY9Z6MYXemrwtWWCTgp61HPYTo5A246/PdXJEbjQPa+1hQ637WytLXT4Qve21oLuKOgewnZydGgbfIZY6A4XOnmtLXTntmFrbaE7X+i0tX5e+gUobwgIeeTk6NwQFPOehe7UEBbySNCdGUJDHjk5OjKEx7xnoTswdBDyyEKHGzqKec9Chxo6C3kk6DBDpyGPnBxBhs5j3rPQAYT8l6AbJuR/OTkaJeaHWejGCPn/BN0IIT+Nk6MBYn46C10xIZ9P0BUS8uWcHJUR83UsdCWEPA8LXQExz8dCFyTk+Qm6ACEvx8mxMjEvy0KvRMjrEPTChLwuJ8eCxLw+C70AIZcj6BkJuTwnx0zEXAcLfSUh10XQFxJynZwcFxBzvSz0GYRcPwv9RGJug4U+QchtEfQjhNwmJ8dms/n55t3RP0XM7ep6oe+H/PLlq8Pv9fX6ZYet6/Z3Csnk5CCKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogmaT5A+nsWjnOb4dqQAAAABJRU5ErkJggg=="
ICON_512_B64 = "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"

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="去水印">
<meta name="theme-color" content="#0f0f13">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" href="/icon-180.png">
<link rel="manifest" href="/manifest.webmanifest">
<title>抖音去水印 · 个人工具</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  body {
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0f0f13; color: #eee; min-height: 100vh;
    display: flex; justify-content: center; padding: 24px 16px 60px;
  }
  .wrap { width: 100%; max-width: 560px; }
  h1 { font-size: 22px; text-align: center; margin-bottom: 4px; }
  h1 span { background: linear-gradient(90deg,#25f4ee,#fe2c55); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .sub { text-align: center; color: #888; font-size: 13px; margin-bottom: 24px; }
  textarea {
    width: 100%; min-height: 96px; resize: vertical; padding: 14px;
    background: #1a1a22; border: 1px solid #2e2e3a; border-radius: 12px;
    color: #eee; font-size: 15px; outline: none;
  }
  textarea:focus { border-color: #25f4ee; }
  .btn {
    display: block; width: 100%; margin-top: 12px; padding: 14px;
    border: none; border-radius: 12px; font-size: 16px; font-weight: 600;
    line-height: 1.2; text-align: center;
    background: linear-gradient(90deg,#25f4ee,#4a7cff); color: #06121a; cursor: pointer;
  }
  a.btn { text-decoration: none; display: flex; align-items: center; justify-content: center; }
  .btn-row2 { display: flex; gap: 10px; margin-top: 12px; }
  .btn-row2 .btn { margin-top: 0; flex: 1; }
  .btn-row2 .btn.ghost { flex: 0 0 92px; }
  .btn:disabled { opacity: .5; }
  .btn.pink { background: linear-gradient(90deg,#fe2c55,#ff7a45); color: #fff; }
  .btn.ghost { background: #1a1a22; color: #ccc; border: 1px solid #2e2e3a; font-weight: 400; }
  #msg { margin-top: 14px; font-size: 14px; text-align: center; min-height: 20px; }
  #msg.err { color: #ff6b81; } #msg.ok { color: #25f4ee; }
  .card { display: none; margin-top: 20px; background: #16161d; border: 1px solid #26262f; border-radius: 16px; padding: 16px; }
  .card video, .card img.cover { width: 100%; border-radius: 10px; background: #000; max-height: 60vh; }
  .title { margin-top: 12px; font-size: 14px; line-height: 1.5; color: #ddd; word-break: break-all; }
  .author { margin-top: 6px; font-size: 13px; color: #888; }
  .imgs { display: grid; grid-template-columns: repeat(2,1fr); gap: 8px; margin-top: 12px; }
  .imgs img { width: 100%; border-radius: 8px; aspect-ratio: 3/4; object-fit: cover; }
  .pager { margin-top: 12px; }
  .pager-img { width: 100%; border-radius: 10px; background: #000; max-height: 62vh; object-fit: contain; display: block; min-height: 200px; }
  .pager-bar { display: flex; align-items: center; justify-content: center; gap: 14px; margin-top: 10px; }
  .pgbtn { width: 46px; height: 38px; border-radius: 8px; border: 1px solid #2e2e3a; background: #1a1a22; color: #eee; font-size: 18px; cursor: pointer; }
  .pgbtn:active { opacity: .7; }
  .pgcnt { font-size: 14px; color: #ccc; min-width: 48px; text-align: center; }
  .pgchk { display: flex; align-items: center; justify-content: center; margin-top: 8px; font-size: 13px; color: #ccc; cursor: pointer; }
  .pgchk input { width: 16px; height: 16px; margin-right: 6px; accent-color: #fe2c55; }
  .pager { position: relative; }
  video.pager-img { display: none; }
  .live-chip { position: absolute; top: 10px; left: 10px; background: rgba(254,44,85,.92); color: #fff; font-size: 12px; padding: 3px 10px; border-radius: 10px; display: none; }
  .foot { margin-top: 30px; text-align: center; color: #555; font-size: 12px; line-height: 1.8; }
  .spin { display:inline-block; width:14px; height:14px; border:2px solid #999; border-top-color:transparent; border-radius:50%; animation: r .8s linear infinite; vertical-align:-2px; margin-right:6px;}
  @keyframes r { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="wrap">
  <h1>抖音<span>去水印</span>下载</h1>
  <p class="sub">粘贴抖音分享链接或整段口令，解析无水印原视频 · 仅个人使用</p>

  <textarea id="input" placeholder="例如：8.88 abc:/ 复制打开抖音，看看【xxx】https://v.douyin.com/xxxxxx/"></textarea>
  <div class="btn-row2">
    <button class="btn" id="parseBtn" onclick="parse()">解析作品</button>
    <button class="btn ghost" id="pasteBtn" onclick="pasteLink()">📋 粘贴</button>
    <button class="btn ghost" id="clearBtn" onclick="clearAll()">🗑 清空</button>
  </div>
  <div id="msg"></div>

  <div class="card" id="card">
    <div id="media"></div>
    <div class="title" id="title"></div>
    <div class="author" id="author"></div>
    <div id="actions"></div>
  </div>

  <p class="foot" id="foot"></p>
</div>

<script>
const $ = id => document.getElementById(id);
function setMsg(t, cls) { const m = $('msg'); m.className = cls || ''; m.innerHTML = t; }

async function parse() {
  const text = $('input').value.trim();
  if (!text) { setMsg('请先粘贴抖音分享链接或口令', 'err'); return; }
  $('parseBtn').disabled = true;
  setMsg('<span class="spin"></span>解析中…');
  $('card').style.display = 'none';
  try {
    const r = await fetch('/api/parse', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const d = await r.json();
    if (!d.ok) throw new Error(d.error || '解析失败');
    render(d);
    setMsg('解析成功 ✓', 'ok');
  } catch (e) {
    setMsg('✗ ' + e.message, 'err');
  } finally {
    $('parseBtn').disabled = false;
  }
}

function render(d) {
  const media = $('media'), acts = $('actions');
  media.innerHTML = ''; acts.innerHTML = '';
  $('title').textContent = d.desc || '(无标题)';
  $('author').textContent = d.author ? '@' + d.author + (d.duration ? ' · ' + d.duration + 's' : '') : '';

  if (d.type === 'video') {
    const v = document.createElement('video');
    v.src = '/api/file?url=' + encodeURIComponent(d.play);
    v.controls = true; v.playsInline = true; v.setAttribute('playsinline','');
    v.preload = 'metadata';
    media.appendChild(v);
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent)
      || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const b1 = document.createElement('a');
    b1.className = 'btn pink'; b1.style.marginTop = '12px';
    const fileUrl = '/api/file?url=' + encodeURIComponent(d.play);
    const blobCache = {};
    const doShareFile = (file, okMsg) => {
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        return navigator.share({ files: [file], title: (d.desc || 'douyin').slice(0, 40) })
          .then(() => { setMsg('✓ 已保存到相册', 'ok'); })
          .catch(e => {
            if (e && e.name === 'AbortError') { setMsg('✓ 分享面板已关闭 · 已选「存储视频」的已进相册', 'ok'); return; }
            setMsg('✗ 分享失败: ' + e.message, 'err');
          });
      }
      return Promise.reject(new Error('unsupported'));
    };
    if (isIOS) {
      b1.textContent = '📲 保存到相册';
      b1.href = 'javascript:void(0)';
      b1.onclick = async (ev) => {
        ev.preventDefault();
        if (blobCache[d.play]) {
          try { await doShareFile(blobCache[d.play]); } catch (e) { /* unsupported */ }
          return;
        }
        b1.textContent = '⏳ 正在获取视频...';
        try {
          const resp = await fetch(fileUrl);
          if (!resp.ok) throw new Error('获取视频失败 ' + resp.status);
          const blob = await resp.blob();
          const file = new File([blob], 'douyin.mp4', { type: 'video/mp4' });
          blobCache[d.play] = file;
          b1.textContent = '📲 保存到相册';
          try { await doShareFile(file); }
          catch (e) {
            setMsg('此设备不支持直存相册，改用下载方式', 'err');
            window.location.href = '/api/download?url=' + encodeURIComponent(d.play) + '&name=' + encodeURIComponent(d.desc || 'douyin');
          }
        } catch (e) {
          b1.textContent = '📲 保存到相册';
          setMsg('✗ ' + e.message + '，改用下载方式', 'err');
          window.location.href = '/api/download?url=' + encodeURIComponent(d.play) + '&name=' + encodeURIComponent(d.desc || 'douyin');
        }
      };
    } else {
      b1.textContent = '⬇ 保存无水印视频';
      b1.href = '/api/download?url=' + encodeURIComponent(d.play) + '&name=' + encodeURIComponent(d.desc || 'douyin');
    }
    acts.appendChild(b1);
    const b2 = document.createElement('button');
    b2.className = 'btn ghost'; b2.textContent = '复制无水印直链';
    b2.onclick = async () => {
      try { await navigator.clipboard.writeText('/api/file?url=' + location.origin + ''); } catch(e){}
      const full = location.origin + '/api/file?url=' + encodeURIComponent(d.play);
      try { await navigator.clipboard.writeText(full); b2.textContent = '已复制 ✓'; }
      catch(e) { prompt('手动复制链接：', full); }
      setTimeout(() => b2.textContent = '复制无水印直链', 1500);
    };
    acts.appendChild(b2);
    const tip = document.createElement('p');
    tip.style.cssText = 'margin-top:10px;font-size:12px;color:#777;line-height:1.6';
    tip.textContent = isIOS
      ? 'iPhone/iPad：点「保存到相册」→ 系统分享面板弹出 → 选「存储视频/存储到相册」即完成。若提示不支持，会自动改用下载方式。'
      : '点「保存无水印视频」开始下载；iPhone 也可以在视频播放器里长按画面选择存储。';
    acts.appendChild(tip);
  } else {
    const imgs = d.images || [];
    const ivs = d.image_videos || [];
    const isLive = i => !!(ivs[i]);
    const mediaOf = i => isLive(i) ? ivs[i] : imgs[i];
    if (!imgs.length) {
      const tip = document.createElement('p');
      tip.style.cssText = 'margin-top:10px;font-size:12px;color:#777';
      tip.textContent = '未获取到图片内容';
      acts.appendChild(tip);
    } else {
      const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent)
        || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
      let idx = 0;
      const checked = imgs.map(() => true);
      const proxy = u => '/api/file?url=' + encodeURIComponent(u);
      const objCache = {};
      const loadInto = i => {
        const key = mediaOf(i);
        if (objCache[key]) return Promise.resolve(objCache[key]);
        return fetch(proxy(key)).then(r => { if (!r.ok) throw new Error(r.status); return r.blob(); })
          .then(b => { objCache[key] = URL.createObjectURL(b); return objCache[key]; });
      };
      const stage = document.createElement('div'); stage.className = 'pager';
      const imgEl = document.createElement('img'); imgEl.className = 'pager-img';
      imgEl.src = proxy(imgs[0]);
      const vidEl = document.createElement('video'); vidEl.className = 'pager-img';
      vidEl.setAttribute('playsinline', ''); vidEl.muted = true; vidEl.loop = true;
      const liveChip = document.createElement('div');
      liveChip.className = 'live-chip'; liveChip.textContent = '实况 · 动态版';
      stage.appendChild(imgEl); stage.appendChild(vidEl); stage.appendChild(liveChip);
      const bar = document.createElement('div'); bar.className = 'pager-bar';
      const prev = document.createElement('button'); prev.className = 'pgbtn'; prev.textContent = '‹';
      const counter = document.createElement('span'); counter.className = 'pgcnt';
      const next = document.createElement('button'); next.className = 'pgbtn'; next.textContent = '›';
      const chk = document.createElement('label'); chk.className = 'pgchk';
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = true;
      const cbText = document.createTextNode('保存这一张');
      chk.appendChild(cb); chk.appendChild(cbText);
      counter.textContent = '1/' + imgs.length;
      const show = () => {
        cb.checked = checked[idx];
        counter.textContent = '加载中 ' + (idx + 1) + '/' + imgs.length;
        liveChip.style.display = 'none';
        loadInto(idx).then(u => {
          if (isLive(idx)) {
            imgEl.style.display = 'none';
            vidEl.style.display = 'block';
            if (vidEl.getAttribute('src') !== u) vidEl.src = u;
            vidEl.play().catch(() => {});
            liveChip.style.display = 'block';
            cbText.textContent = '保存实况动态视频';
          } else {
            vidEl.pause();
            vidEl.style.display = 'none';
            imgEl.style.display = 'block';
            imgEl.src = u;
            cbText.textContent = '保存这一张';
          }
          counter.textContent = (idx + 1) + '/' + imgs.length;
        }).catch(() => { counter.textContent = (idx + 1) + '/' + imgs.length + ' 加载失败'; });
      };
      prev.onclick = () => { idx = (idx - 1 + imgs.length) % imgs.length; show(); };
      next.onclick = () => { idx = (idx + 1) % imgs.length; show(); };
      cb.onchange = () => { checked[idx] = cb.checked; updateSave(); };
      bar.appendChild(prev); bar.appendChild(counter); bar.appendChild(next);
      stage.appendChild(bar); stage.appendChild(chk);
      media.appendChild(stage);
      imgs.forEach((_, i) => setTimeout(() => loadInto(i).catch(() => {}), 400 * i));

      const save = document.createElement('button');
      save.className = 'btn pink'; save.style.marginTop = '12px';
      const updateSave = () => {
        const n = checked.filter(Boolean).length;
        save.textContent = '💾 保存选中的 ' + n + ' 张图片';
        save.disabled = !n;
      };
      updateSave();
      save.onclick = () => {
        const sel = [];
        imgs.forEach((u, i) => { if (checked[i]) sel.push({ url: mediaOf(i), live: isLive(i), n: i + 1 }); });
        const openAggregatePage = () => {
          const w = window.open('', '_blank');
          if (!w) { alert('浏览器拦截了新标签页，请允许弹窗后重试'); return; }
          w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8">'
            + '<meta name="viewport" content="width=device-width,initial-scale=1">'
            + '<title>逐张长按保存到相册</title><style>body{background:#111;color:#eee;'
            + 'font-family:-apple-system,sans-serif;margin:0;padding:16px}'
            + '.back{position:fixed;top:10px;right:14px;z-index:9;background:#1a1a22;border:1px solid #2e2e3a;'
            + 'border-radius:8px;padding:8px 12px;color:#4a9eff;text-decoration:none;font-size:13px}'
            + 'p{font-size:13px;color:#aaa;line-height:1.7}'
            + 'img{width:100%;margin:12px 0;border-radius:8px;display:block}'
            + '.tag{font-size:11px;color:#fe2c55}</style></head><body>'
            + '<a class="back" href="/">← 返回工具</a>'
            + '<p style="margin-top:48px">共 ' + sel.length + ' 张：逐张<b>长按图片 → 存储到相册</b>。标「实况」的保存的是动态视频。</p>'
            + sel.map(it => '<div><span class="tag">' + (it.live ? '实况·动态' : '图片') + ' #' + it.n + '</span>'
                + '<img src="' + '/api/file?url=' + encodeURIComponent(it.url) + '"></div>').join('')
            + '</body></html>');
          w.document.close();
        };
        if (isIOS) {
          (async () => {
            const origText = save.textContent;
            save.disabled = true;
            try {
              const files = [];
              for (let i = 0; i < sel.length; i++) {
                const it = sel[i];
                save.textContent = '⏳ 获取第 ' + (i + 1) + '/' + sel.length + ' 个' + (it.live ? '（实况）' : '...');
                const r = await fetch('/api/file?url=' + encodeURIComponent(it.url));
                if (!r.ok) throw new Error('获取失败 ' + r.status);
                const b = await r.blob();
                if (it.live) {
                  files.push(new File([b], 'live-' + it.n + '.mp4', { type: 'video/mp4' }));
                } else {
                  const m = (it.url.match(/\.(jpe?g|png|webp|gif|heic)/i) || [null, 'jpg']);
                  files.push(new File([b], 'img-' + it.n + '.' + m[1].toLowerCase(), { type: b.type || 'image/jpeg' }));
                }
              }
              if (navigator.canShare && navigator.canShare({ files })) {
                await navigator.share({ files, title: (d.desc || 'douyin').slice(0, 40) });
                setMsg('✓ 已保存到相册', 'ok');
              } else {
                openAggregatePage();
              }
            } catch (e) {
              if (e && e.name === 'AbortError') {
                setMsg('✓ 分享面板已关闭 · 已选「存储图像/视频」的已进相册', 'ok');
              } else {
                openAggregatePage();
              }
            }
            save.textContent = origText; save.disabled = false;
          })();
        } else {
          sel.forEach((it, i) => {
            setTimeout(() => {
              const a = document.createElement('a');
              a.href = '/api/download?url=' + encodeURIComponent(it.url) + '&name=' + encodeURIComponent((d.desc || 'douyin').slice(0, 30) + '-' + it.n + (it.live ? '-实况' : ''));
              document.body.appendChild(a); a.click(); a.remove();
            }, i * 900);
          });
          setMsg('开始下载选中的 ' + sel.length + ' 张，浏览器若询问「允许下载多个文件」请选允许', 'ok');
        }
      };
      acts.appendChild(save);
      const tip = document.createElement('p');
      tip.style.cssText = 'margin-top:10px;font-size:12px;color:#777;line-height:1.6';
      tip.textContent = '左右箭头翻页查看每一张，不想要的取消勾选再保存。';
      acts.appendChild(tip);
    }
  }
  $('card').style.display = 'block';
}

$('input').addEventListener('paste', () => setTimeout(() => { if ($('input').value.trim() && !$('card').style.display) setMsg('已粘贴，点「解析作品」开始', 'ok'); }, 100));

function clearAll() {
  $('input').value = '';
  $('card').style.display = 'none';
  setMsg('', '');
}

async function pasteLink() {
  try {
    const t = await navigator.clipboard.readText();
    const s = String(t || '').trim();
    if (!s) { setMsg('剪贴板是空的', 'err'); return; }
    $('input').value = s;
    setMsg(/douyin/i.test(s) ? '已粘贴 ✓ 点「解析作品」开始' : '已粘贴（未识别到抖音链接，检查一下）', 'ok');
  } catch (e) {
    setMsg('读取剪贴板被拒绝，请长按输入框手动粘贴', 'err');
  }
}

// 打开页面时自动识别剪贴板中的抖音链接并填入（Safari 会请求粘贴权限，拒绝则静默跳过）
(async () => {
  try {
    const t = await navigator.clipboard.readText();
    if (t && /v\.douyin\.com|douyin\.com|iesdouyin/i.test(t)) {
      $('input').value = t.trim();
      setMsg('已识别剪贴板中的链接 ✓ 点「解析作品」开始', 'ok');
    }
  } catch (e) { /* 无权限或非链接，忽略 */ }
})();

fetch('/api/info').then(r => r.json()).then(d => {
  const local = /^(localhost|127\.|192\.168\.|10\.|172\.)/.test(location.hostname);
  const urls = local ? d.urls : d.urls.slice(0, 1);
  $('foot').innerHTML = '访问地址：' + urls.map(u => '<b>' + u + '</b>').join('　') +
    '<br>仅供个人学习使用 · 请勿传播 · 下载内容版权归原作者所有';
});
</script>
</body>
</html>
"""


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('223.5.5.5', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def extract_url(text):
    m = URL_RE.search(text)
    return m.group(0) if m else None


def resolve_aweme_id(url):
    """跟随短链跳转，拿到 aweme_id（风控会弹回主页，需带 ttwid + 多次重试）"""
    for attempt in range(4):
        headers = {'User-Agent': MOBILE_UA}
        ttwid = get_ttwid()
        if ttwid:
            headers['Cookie'] = f'ttwid={ttwid}'
        try:
            r = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        except requests.RequestException:
            continue
        candidates = [r.url] + [h.headers.get('Location', '') for h in r.history]
        for u in candidates:
            for p in ID_PATTERNS:
                m = p.search(u)
                if m:
                    return m.group(1)
        # 页面内容里再找一次
        for p in ID_PATTERNS:
            m = p.search(r.text[:200000])
            if m:
                return m.group(1)
    return None


def find_item_list(obj):
    """在 JSON 里递归找第一个非空 item_list"""
    if isinstance(obj, dict):
        il = obj.get('item_list')
        if isinstance(il, list) and il:
            return il
        for v in obj.values():
            r = find_item_list(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_item_list(v)
            if r:
                return r
    return None


def fetch_item(aid):
    """从分享页 / 旧接口获取作品数据（带 ttwid cookie 才能拿到 SSR 数据）
    返回 (item, kind)；kind 用于判断作品类型（note/slides 需要浏览器兜底取实况视频）"""
    headers = {'User-Agent': MOBILE_UA, 'Referer': 'https://www.douyin.com/'}
    ttwid = get_ttwid()
    if ttwid:
        headers['Cookie'] = f'ttwid={ttwid}'
    for path in (f'https://www.iesdouyin.com/share/video/{aid}/',
                 f'https://www.iesdouyin.com/share/slides/{aid}/',
                 f'https://www.iesdouyin.com/share/note/{aid}/'):
        kind = path.rsplit('/', 2)[-2]
        try:
            r = requests.get(path, headers=headers, timeout=15)
            m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>', r.text, re.S)
            if not m:
                continue
            data = json.loads(m.group(1))
            items = find_item_list(data)
            if items:
                return items[0], kind
        except Exception:
            continue
    # 兜底：旧版 iteminfo 接口
    try:
        r = requests.get('https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/',
                         params={'item_ids': aid}, headers=headers, timeout=15)
        items = (r.json() or {}).get('item_list')
        if items:
            return items[0], 'video'
    except Exception:
        pass
    return None, None




def _best_img_url(urls):
    """从 url_list 里挑最高画质：优先 jpeg 变体，其次 shrink 最大宽度，最后第 0 条"""
    if not urls:
        return None
    for u in urls:
        if 'aweme-images' in u and '.jpeg' in u:
            return u
    best, best_w = None, -1
    for u in urls:
        m = re.search(r'shrink:(\d+)', u)
        w = int(m.group(1)) if m else 0
        if '.webp' not in u:
            w += 5000
        if w > best_w:
            best_w, best = w, u
    return best or urls[0]


def build_result(item):
    desc = (item.get('desc') or '').strip() or 'douyin_video'
    author = ((item.get('author') or {}).get('nickname') or '').strip()
    video = item.get('video') or {}

    images = []
    image_videos = []
    for im in item.get('images') or []:
        ul = (im or {}).get('url_list') or []
        if ul:
            images.append(_best_img_url(ul))
            # 实况图：每张图可能关联一段动态视频（Live Photo 的动效部分）
            iv = (((im or {}).get('video') or {}).get('play_addr') or {}).get('url_list') or []
            image_videos.append(iv[0].replace('playwm', 'play') if iv else '')

    play = ''
    if video:
        ul = ((video.get('play_addr') or {}).get('url_list') or [])
        if ul:
            # playwm -> play 即无水印原视频
            play = ul[0].replace('playwm', 'play')
    duration = int(video.get('duration') or 0) // 1000 or None

    if not play and not images:
        return None
    return {
        'ok': True,
        'type': 'images' if images else 'video',
        'desc': desc,
        'author': author,
        'duration': duration,
        'play': play,
        'images': images,
        'image_videos': image_videos,
    }


_TTWID = {'v': None}


def get_ttwid():
    """获取抖音 ttwid cookie（突破分享页登录墙的关键）"""
    if _TTWID['v']:
        return _TTWID['v']
    try:
        s = requests.Session()
        s.headers.update({'User-Agent': MOBILE_UA})
        s.post('https://ttwid.bytedance.com/ttwid/union/register/',
               json={'region': 'cn', 'aid': 1768, 'needFid': False,
                     'service': 'www.ixigua.com',
                     'migrate_info': {'ticket': '', 'source': 'node'},
                     'cbUrlProtocol': 'https', 'union': True},
               timeout=15)
        _TTWID['v'] = s.cookies.get('ttwid')
    except Exception:
        pass
    return _TTWID['v']


STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = { runtime: {} };
const oq = window.navigator.permissions.query;
window.navigator.permissions.query = (p) => (p.name === 'notifications'
  ? Promise.resolve({state: Notification.permission}) : oq(p));
"""

_PW_LOCK = threading.Lock()


def _clean_note_images(urls):
    """从抓到的图片 URL 里筛出真正的图文内容，去掉头像/封面/相关推荐缩略图。"""
    out, seen = [], set()
    for u in urls:
        if not u:
            continue
        if 'aweme-avatar' in u or '/100x100/' in u or 'cropcenter' in u:
            continue
        if 'biz_tag=aweme_images' not in u:
            continue
        if 'sc=cover' in u:
            continue
        oid = re.search(r'/(o[A-Za-z0-9_\-]+)~', u)
        key = oid.group(1) if oid else u.split('?')[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(u)
    return out


def _pick_videos(urls):
    out = []
    for u in urls:
        if not u:
            continue
        if 'douyinvod' in u or (u.split('?')[0].endswith('.mp4')):
            if u not in out:
                out.append(u)
    return out


def fetch_item_browser(aid, kind='video'):
    """无头浏览器渲染 + 网络抓包：拦截前端自己发起的带签名接口和真实媒体直链。
    绕过 a_bogus 签名与登录墙。返回 item 结构 dict 或 None。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    box = {'api': None, 'imgs': set(), 'vids': set(), 'desc': '', 'author': ''}
    ttwid = get_ttwid()

    def on_response(resp):
        u = resp.url
        # 1) 媒体直链
        try:
            if any(d in u for d in ('douyinpic', 'byteimg', 'zjcdn')):
                box['imgs'].add(u)
            elif 'douyinvod' in u or u.split('?')[0].endswith('.mp4'):
                box['vids'].add(u)
        except Exception:
            pass
        # 2) 接口 JSON（匹配本作品 id，取元数据 + 视频直链）
        if 'aweme' not in u:
            return
        try:
            j = resp.json()
        except Exception:
            return
        if not isinstance(j, dict):
            return
        items = []
        if isinstance(j.get('aweme_detail'), dict):
            items.append(j['aweme_detail'])
        for k in ('aweme_list', 'item_list'):
            if isinstance(j.get(k), list):
                items += [x for x in j[k] if isinstance(x, dict)]
        for it in items:
            if str(it.get('aweme_id')) == str(aid) and not box['api']:
                box['api'] = it
                box['desc'] = it.get('desc') or ''
                box['author'] = ((it.get('author') or {}).get('nickname')) or ''

    with _PW_LOCK:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=[
                    '--no-sandbox', '--disable-blink-features=AutomationControlled'])
                ctx = browser.new_context(
                    user_agent=MOBILE_UA, viewport={'width': 390, 'height': 844},
                    is_mobile=True, locale='zh-CN', device_scale_factor=2)
                ctx.add_init_script(STEALTH_JS)
                if ttwid:
                    for dom in ('.douyin.com', '.iesdouyin.com'):
                        ctx.add_cookies([{'name': 'ttwid', 'value': ttwid,
                                          'domain': dom, 'path': '/'}])
                page = ctx.new_page()
                page.on('response', on_response)
                try:
                    page.goto((f'https://www.iesdouyin.com/share/{kind}/{aid}/' if kind in ('note', 'slides') else f'https://www.douyin.com/{kind}/{aid}'),
                              wait_until='domcontentloaded', timeout=45000)
                    page.wait_for_load_state('networkidle', timeout=12000)
                except Exception:
                    pass
                # 图文作品需要等图片渲染；顺便滚一下触发懒加载
                try:
                    page.wait_for_timeout(2500)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                    page.wait_for_timeout(1200)
                except Exception:
                    pass
                # 解析页面内嵌 _ROUTER_DATA（PC note 页可能带实况视频字段）
                try:
                    html2 = page.content()
                    m2 = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>', html2, re.S)
                    if m2:
                        ritems = find_item_list(json.loads(m2.group(1)))
                        if ritems:
                            box['router'] = ritems[0]
                except Exception:
                    pass
                # DOM 兜底补图片
                try:
                    dom_imgs = page.evaluate("""() => [...document.querySelectorAll('img')]
                        .map(i=>i.currentSrc||i.src)
                        .filter(u=>/douyinpic|byteimg|zjcdn/.test(u))""")
                    for u in dom_imgs:
                        box['imgs'].add(u)
                    if not box['desc']:
                        box['desc'] = page.evaluate(
                            "() => (document.querySelector('[data-e2e=\"video-desc\"],.title,h1')||{}).innerText || ''") or ''
                except Exception:
                    pass
                browser.close()
        except Exception:
            pass

    api = box['api'] or {}
    # 视频：优先接口里的 play_addr（无水印），其次网络抓到的 mp4
    play = ''
    video = api.get('video') or {}
    ul = ((video.get('play_addr') or {}).get('url_list') or [])
    if ul:
        play = ul[0].replace('playwm', 'play')
    net_vids = _pick_videos(box['vids'])
    if not play and net_vids:
        play = net_vids[0]

    # 图文：优先接口 images，其次页面内嵌路由数据（含 jpeg 高清变体），再次网络抓包过滤
    images = []
    for im in api.get('images') or []:
        iul = (im or {}).get('url_list') or []
        if iul:
            images.append(_best_img_url(iul))
    if not images:
        rimgs = (box.get('router') or {}).get('images') or []
        for im in rimgs:
            iul = (im or {}).get('url_list') or []
            if iul:
                images.append(_best_img_url(iul))
    if not images:
        images = _clean_note_images(box['imgs'])

    if not play and not images:
        return None

    net_vid_list = _pick_videos(box['vids'])
    rtr = box.get('router') or {}
    item = {
        '_vids': net_vid_list[:20],
        '_router_images': [((im.get('video') or {}).get('play_addr') or {}).get('url_list', [None])[0] for im in (rtr.get('images') or [])],
        'desc': box['desc'] or (api.get('desc') or ''),
        'author': {'nickname': box['author']},
        'video': {'play_addr': {'url_list': [play]}, 'duration': video.get('duration', 0)} if play else {},
        'images': [{'url_list': [u]} for u in images],
    }
    return item



def check_host(url):
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or '').lower()
    return any(host == d or host.endswith('.' + d) for d in ALLOWED_HOSTS)


@app.route('/')
def index():
    return Response(INDEX_HTML, mimetype='text/html')


@app.route('/favicon.ico')
def favicon():
    return Response(status=204)

import base64 as _b64


def _icon_response(which):
    data = _b64.b64decode(ICON_180_B64 if which == '180' else ICON_512_B64)
    return Response(data, mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=604800'})


@app.route('/apple-touch-icon.png')
@app.route('/icon-180.png')
def icon_180():
    return _icon_response('180')


@app.route('/icon-512.png')
def icon_512():
    return _icon_response('512')


@app.route('/manifest.webmanifest')
def webmanifest():
    import json
    m = {
        'name': '抖音去水印', 'short_name': '去水印',
        'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#0f0f13', 'theme_color': '#0f0f13',
        'icons': [
            {'src': '/icon-180.png', 'sizes': '180x180', 'type': 'image/png', 'purpose': 'any'},
            {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    }
    return Response(json.dumps(m, ensure_ascii=False), mimetype='application/manifest+json')


@app.errorhandler(404)
def fallback_any_path(e):
    # 任何未知路径（误输入、带多余字符的链接）一律回落到首页，避免整页 404
    return Response(INDEX_HTML, mimetype='text/html')


@app.route('/api/info')
def info():
    ip = lan_ip()
    urls = [request.host_url.rstrip('/')]
    lan = f'http://{ip}:{request.host.split(":")[-1]}'
    if lan not in urls:
        urls.append(lan)
    return jsonify({'urls': urls})


@app.route('/api/parse', methods=['POST'])
def api_parse():
    text = (request.get_json(silent=True) or {}).get('text', '').strip()
    if not text:
        return jsonify({'ok': False, 'error': '内容为空'})

    # 直接粘贴纯数字 id 也支持
    aid = text if re.fullmatch(r'\d{15,25}', text) else None
    if not aid:
        url = extract_url(text)
        if not url:
            return jsonify({'ok': False, 'error': '没有找到链接，请粘贴完整的抖音分享内容'})
        try:
            aid = resolve_aweme_id(url)
        except requests.RequestException as e:
            return jsonify({'ok': False, 'error': f'链接访问失败：{e.__class__.__name__}'})
        if not aid:
            return jsonify({'ok': False, 'error': '无法从链接中识别视频 ID（可能是直播/主页/合集链接）'})

    item, kind = fetch_item(aid)
    has_media = item and (item.get('images') or ((item.get('video') or {}).get('play_addr') or {}).get('url_list'))
    # 图集/图文作品（note/slides）的实况视频只在 App/PC 接口里：
    # SSR 数据只有静态图，必须用无头浏览器按 note 页面拦截接口补全（代价是多花几秒）
    is_image_work = bool(item and item.get('images'))
    browser_kind = 'note' if is_image_work else 'video'
    if has_media and is_image_work:
        try:
            item2 = fetch_item_browser(aid, browser_kind)
            if item2 and item2.get('images'):
                ssr_imgs = (item or {}).get('images') or []
                for i, bim in enumerate(item2['images']):
                    if i < len(ssr_imgs):
                        merged = list((bim.get('url_list') or [])) + list((ssr_imgs[i] or {}).get('url_list') or [])
                        seen, uniq = set(), []
                        for u in merged:
                            if u and u not in seen:
                                seen.add(u); uniq.append(u)
                        bim['url_list'] = uniq
                item = item2
        except Exception:
            pass
    if not has_media:
        # SSR 拿不到/空壳（图文作品/反爬），回退到无头浏览器渲染拦截
        item2 = fetch_item_browser(aid, browser_kind)
        if item2:
            item = item2
    if not item:
        return jsonify({'ok': False, 'error': '未获取到作品数据：视频可能已删除/设为私密，或该作品需要登录、抖音风控拦截'})
    raw_mode = (request.get_json(silent=True) or {}).get('raw') or request.args.get('raw')
    if raw_mode:
        if str(raw_mode) == '2':
            ssr_item, _ = fetch_item(aid)
            browser_item = fetch_item_browser(aid, browser_kind)
            return jsonify({'ok': True, 'ssr': ssr_item, 'browser': browser_item})
        return jsonify({'ok': True, 'raw': item})
    result = build_result(item)
    if not result:
        return jsonify({'ok': False, 'error': '未获取到作品数据：视频可能已删除/设为私密，或该作品需要登录、抖音风控拦截'})
    result['aweme_id'] = aid
    return jsonify(result)


@app.route('/api/file')
def api_file():
    """代理抖音资源（视频预览 / 图片），绕过 Referer 限制"""
    url = request.args.get('url', '')
    if not url or not check_host(url):
        abort(403)
    try:
        r = requests.get(url, headers={'User-Agent': MOBILE_UA, 'Referer': 'https://www.douyin.com/'},
                         stream=True, timeout=(10, 60))
        r.raise_for_status()
    except requests.RequestException:
        abort(502)

    def gen():
        try:
            for chunk in r.iter_content(1024 * 256):
                if chunk:
                    yield chunk
        finally:
            r.close()

    ctype = r.headers.get('Content-Type', 'application/octet-stream')

    # 动图 webp 转为 GIF：iOS 相册不支持动画 webp，长按保存会变静态；GIF 可保留动效
    if 'webp' in ctype.lower() or re.search(r'\.webp(?:[?#]|$)', url, re.I):
        try:
            from io import BytesIO
            from PIL import Image
            im = Image.open(BytesIO(r.content))
            if getattr(im, 'is_animated', False):
                out = BytesIO()
                durs = im.info.get('duration')
                duration = int(sum(durs) / len(durs)) if isinstance(durs, list) and durs else int(durs or 100)
                im.save(out, format='GIF', save_all=True, duration=duration, loop=0)
                return Response(out.getvalue(), content_type='image/gif')
        except Exception:
            pass  # 转换失败则按原图流式返回

    resp = Response(gen(), content_type=ctype)
    if r.headers.get('Content-Length'):
        resp.headers['Content-Length'] = r.headers['Content-Length']
    return resp


@app.route('/api/download')
def api_download():
    """以附件形式下载无水印视频（iPhone Safari 会存到「文件」）"""
    url = request.args.get('url', '')
    name = request.args.get('name', 'douyin')
    if not url or not check_host(url):
        abort(403)
    name = re.sub(r'[\\/:*?"<>|\r\n#【】@].*', '', name).strip()[:60] or 'douyin'
    try:
        r = requests.get(url, headers={'User-Agent': MOBILE_UA, 'Referer': 'https://www.douyin.com/'},
                         stream=True, timeout=(10, 120))
        r.raise_for_status()
    except requests.RequestException:
        abort(502)

    def gen():
        try:
            for chunk in r.iter_content(1024 * 256):
                if chunk:
                    yield chunk
        finally:
            r.close()

    resp = Response(gen(), content_type='video/mp4')
    m_ext = re.search(r'\.(jpe?g|png|webp|heic|gif)(?:[?#]|$)', url, re.I)
    ext = ('.' + m_ext.group(1).lower()) if m_ext else '.mp4'
    resp.headers['Content-Disposition'] = (
        f"attachment; filename=media{ext}; filename*=UTF-8''{quote(name)}{ext}")
    if r.headers.get('Content-Length'):
        resp.headers['Content-Length'] = r.headers['Content-Length']
    return resp


if __name__ == '__main__':
    import os
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    port = int(os.environ.get('PORT', 8765))
    ip = lan_ip()
    print('=' * 52)
    print('  抖音去水印工具已启动（仅供个人使用）')
    print(f'  电脑访问:  http://127.0.0.1:{port}')
    print(f'  手机访问:  http://{ip}:{port}   (需与电脑同一WiFi)')
    print('  按 Ctrl+C 停止')
    print('=' * 52)
    app.run(host='0.0.0.0', port=port, debug=False)
