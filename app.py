# -*- coding: utf-8 -*-
"""
抖音无水印视频解析工具（仅供个人学习使用，请勿传播/商用）
启动后：电脑访问 http://127.0.0.1:8765
        手机(同一WiFi)访问 http://<电脑IP>:8765
"""
import json
import re
import socket
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

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
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
    background: linear-gradient(90deg,#25f4ee,#4a7cff); color: #06121a; cursor: pointer;
  }
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
  <button class="btn" id="parseBtn" onclick="parse()">解析视频</button>
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
    const b1 = document.createElement('a');
    b1.className = 'btn pink'; b1.style.marginTop = '12px'; b1.textContent = '⬇ 保存无水印视频';
    b1.href = '/api/download?url=' + encodeURIComponent(d.play) + '&name=' + encodeURIComponent(d.desc || 'douyin');
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
    tip.textContent = 'iPhone：点「保存无水印视频」会开始下载，完成后到 Safari 下载项 / 「文件」App 里查看；也可直接在上方视频播放器里全屏播放后 AirDrop。';
    acts.appendChild(tip);
  } else {
    const div = document.createElement('div'); div.className = 'imgs';
    (d.images || []).forEach(u => {
      const a = document.createElement('a');
      a.href = '/api/file?url=' + encodeURIComponent(u); a.target = '_blank';
      const img = document.createElement('img'); img.src = a.href; img.loading = 'lazy';
      a.appendChild(img); div.appendChild(a);
    });
    media.appendChild(div);
    const tip = document.createElement('p');
    tip.style.cssText = 'margin-top:10px;font-size:12px;color:#777';
    tip.textContent = '图文作品：点开大图后长按保存，或用 Safari 分享按钮存储到照片。';
    acts.appendChild(tip);
  }
  $('card').style.display = 'block';
}

$('input').addEventListener('paste', () => setTimeout(() => { if ($('input').value.trim()) parse(); }, 100));

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
    """跟随短链跳转，拿到 aweme_id"""
    r = requests.get(url, headers={'User-Agent': MOBILE_UA},
                     allow_redirects=True, timeout=15)
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
    """从分享页 / 旧接口获取作品数据"""
    headers = {'User-Agent': MOBILE_UA, 'Referer': 'https://www.douyin.com/'}
    for path in (f'https://www.iesdouyin.com/share/video/{aid}/',
                 f'https://www.iesdouyin.com/share/slides/{aid}/',
                 f'https://www.iesdouyin.com/share/note/{aid}/'):
        try:
            r = requests.get(path, headers=headers, timeout=15)
            m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>', r.text, re.S)
            if not m:
                continue
            data = json.loads(m.group(1))
            items = find_item_list(data)
            if items:
                return items[0]
        except Exception:
            continue
    # 兜底：旧版 iteminfo 接口
    try:
        r = requests.get('https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/',
                         params={'item_ids': aid}, headers=headers, timeout=15)
        items = (r.json() or {}).get('item_list')
        if items:
            return items[0]
    except Exception:
        pass
    return None


def build_result(item):
    desc = (item.get('desc') or '').strip() or 'douyin_video'
    author = ((item.get('author') or {}).get('nickname') or '').strip()
    video = item.get('video') or {}

    images = []
    for im in item.get('images') or []:
        ul = (im or {}).get('url_list') or []
        if ul:
            images.append(ul[0])

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
        'type': 'video' if play else 'images',
        'desc': desc,
        'author': author,
        'duration': duration,
        'play': play,
        'images': images,
    }


def check_host(url):
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or '').lower()
    return any(host == d or host.endswith('.' + d) for d in ALLOWED_HOSTS)


@app.route('/')
def index():
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

    item = fetch_item(aid)
    if not item:
        return jsonify({'ok': False, 'error': '未获取到作品数据，视频可能已删除、设为私密或接口失效'})
    result = build_result(item)
    if not result:
        return jsonify({'ok': False, 'error': '该作品没有可下载的视频/图片'})
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
    resp.headers['Content-Disposition'] = (
        f"attachment; filename=video.mp4; filename*=UTF-8''{quote(name)}.mp4")
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
