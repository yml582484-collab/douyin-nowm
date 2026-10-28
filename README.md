# 抖音去水印下载工具（个人自用）

粘贴抖音分享链接/口令 → 解析出**无水印原视频**，手机上直接保存。支持视频作品与图文作品。

> ⚠️ 仅供个人学习使用，请勿传播、勿商用。下载内容版权归原作者所有。

---

## 一键部署到 Render（免费）

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yml582484-collab/douyin-nowm)

1. 点上面按钮，用 **GitHub 账号**登录 Render。
2. 选择本仓库，实例类型选 **Free**，点 **Create / Deploy**。
3. 等 1~3 分钟构建完成，会得到一个网址，形如 `https://douyin-nowm-xxxx.onrender.com`。
4. 手机浏览器打开该网址即可使用（首次打开免费版可能有 ~30 秒冷启动，耐心等一下）。

> **重要提醒**：Render 服务器在国外，抖音**有可能**屏蔽国外机房 IP，导致解析失败。
> 若部署后解析不出来，说明被 IP 限制，请改用下面的「本地 + 内网穿透」方案（用你家的中国 IP，最稳）。

---

## 本地运行（最稳，抖音不会封中国家用 IP）

```bash
pip install -r requirements.txt
python app.py
```

- 电脑访问：<http://127.0.0.1:8765>
- 手机访问（同一 WiFi）：启动时终端会打印 `http://<你的电脑IP>:8765`

Windows 直接双击 `启动工具.bat` 即可。

---

## 手机在外面也能用（Cloudflare 内网穿透，免费）

本地跑着 `python app.py`，再用 Cloudflare Tunnel 把本机端口暴露成公网网址：

```bash
# 安装 cloudflared 后执行（无需账号，快速隧道）
cloudflared tunnel --url http://127.0.0.1:8765
```

它会给出一个 `https://xxxx.trycloudflare.com` 网址，手机在任何网络下都能打开。
缺点：家里电脑需保持开机 + 联网 + 运行本工具。

---

## 工作原理

1. 从分享口令里用正则提取短链，跟随跳转拿到视频 `aweme_id`。
2. 请求 `iesdouyin.com` 分享页，解析页面里的 `_ROUTER_DATA` JSON。
3. 取 `video.play_addr`，把地址里的 `playwm` 换成 `play` → 得到无水印原视频。
4. 后端代理下载（带正确 Referer/UA），绕过抖音 CDN 防盗链，转发给手机保存。

## 接口

| 路由 | 说明 |
|------|------|
| `POST /api/parse` | 传入 `{text}`，返回解析结果 |
| `GET /api/file?url=` | 代理预览视频/图片 |
| `GET /api/download?url=&name=` | 以附件形式下载无水印视频 |
