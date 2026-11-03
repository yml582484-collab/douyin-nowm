<div align="center">

# 抖音去水印下载工具

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![Platform](https://img.shields.io/badge/平台-PC%20%7C%20Android%20%7C%20iOS-lightgrey)](#部署方式)

粘贴抖音分享链接 → **无水印原视频 / 高清图集**，手机电脑直接保存。

</div>

---

## ✨ 功能

- 🎬 **视频作品**：无水印原视频（MP4），后端代理下载绕过 CDN 防盗链
- 🖼️ **图集/图文作品**：高清 JPEG 原图翻页浏览 + 勾选批量保存
- 📱 **iPhone 直存相册**：Web Share API 调起系统分享面板，一步进相册
- 🖼️ **动图友好**：动画 webp 自动转 GIF，保存不丢动效
- 🧭 **图集翻页器**：逐张预加载、勾选批量、左右翻页
- 🔖 **主屏幕图标**：PWA manifest + apple-touch-icon，可添加到手机桌面当 App 用
- 🛡️ **抗风控**：短链解析 4 次重试 + 动态 ttwid；SSR 失败自动切 Playwright 无头浏览器兜底
- 🔒 **防滥用**：媒体代理仅放行抖音系域名

> ⚠️ **仅供个人学习使用**，请勿传播、勿商用。下载内容版权归原作者所有。

## 🚀 部署方式

### 方式一：腾讯云 CloudBase 云托管（推荐，正在使用）

仓库自带 `Dockerfile`（含 Playwright/Chromium 与 Pillow），可直接在
[腾讯云 CloudBase](https://tencentcloud.com/product/tcb) 云托管里「新建服务 → 从代码库/上传代码构建」。
无需服务器、无需备案，默认域名公网可直接访问，支持缩容到零。

### 方式二：轻量应用服务器 / CVM（Lighthouse）

```bash
# 服务器上执行，自动装环境 + systemd 常驻 + 放行防火墙
git clone https://github.com/yml582484-collab/douyin-nowm.git /opt/douyin-nowm
cd /opt/douyin-nowm && bash deploy/deploy.sh            # 仅视频（轻量）
# bash deploy/deploy.sh --with-browser                  # 含 Chromium（支持图文兜底）
```

记得在云控制台安全组放行 `TCP 8765`，详见 [腾讯云部署文档](腾讯云部署文档.md)。

### 方式三：本地运行

```bash
pip install -r requirements.txt
python app.py          # Windows 可直接双击 启动工具.bat
```

- 电脑访问：<http://127.0.0.1:8765>
- 手机（同一 WiFi）：终端会打印局域网地址
- 手机在外面：`cloudflared tunnel --url http://127.0.0.1:8765` 免费内网穿透

### 方式四：Render 一键部署（海外备用）

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yml582484-collab/douyin-nowm)

> ⚠️ Render 机房在国外，可能被抖音 IP 限制导致解析失败，国内环境建议方式一/二/三。

## 📖 使用

1. 在抖音 App 分享作品，复制链接
2. 打开工具网页（首次打开会提示读取剪贴板，允许后自动填入）
3. 点「解析作品」→ 视频直接保存 / 图集翻页勾选后批量保存
4. iPhone 保存时系统分享面板弹出 → 「存储视频 / 存储到相册」

## 🔧 工作原理

```
分享口令 ──正则──▶ 短链 ──跟随跳转──▶ aweme_id
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼ 快速路径（SSR）                                ▼ 兜底路径
   iesdouyin.com 分享页 + ttwid cookie            Playwright 无头浏览器（反检测）
   解析 _ROUTER_DATA.item_list                    拦截带 a_bogus 签名的接口响应
              └───────────────────────┬───────────────────────┘
                                      ▼
              play_addr.playwm → play = 无水印直链 / images.url_list 最高画质变体
                                      ▼
              后端代理下载（正确 Referer/UA 绕过防盗链），支持 Range/附件下载
```

**画质策略**：图集自动从 `url_list` 多变体中选最高画质（优先 `aweme-images` JPEG 变体，
2160~2818px）；动画 webp 自动转 GIF 保留动效；实况（Live Photo）动态部分仅存在于
抖音 App 签名接口，网页渠道不可得，保存为静态高清图。

## 📡 接口

| 路由 | 说明 |
|------|------|
| `POST /api/parse` | 传入 `{text}` 解析；`{"raw": true}` 返回原始 item 数据 |
| `GET /api/file?url=` | 代理预览视频/图片（绕过防盗链） |
| `GET /api/download?url=&name=` | 附件下载，扩展名按媒体类型自动识别 |
| `GET /api/info` | 服务信息 |

## 📁 结构

```
├── app.py               # 单文件 Flask 应用（含前端页面与图标）
├── requirements.txt     # flask / requests / gunicorn / playwright / Pillow
├── Dockerfile           # CloudBase 云托管 / 任意容器环境构建
├── deploy/deploy.sh     # Lighthouse/CVM 一键部署脚本（systemd + gunicorn）
├── render.yaml          # Render 平台配置
└── 腾讯云部署文档.md     # Lighthouse 部署运行手册 + 云托管部署记录
```

## ⚠️ 已知限制

- 实况（Live Photo）动态视频仅存在于抖音 App 签名接口，所有网页工具均只能保存静态高清图
- 抖音接口随时可能变更，解析失败多为上游变动，重试或更新代码即可
- 本工具无鉴权，公网部署时注意不要广泛传播地址

## 📄 License

[MIT](LICENSE) © 2026 yml582484-collab

---
<div align="center">

**仅供个人学习研究 · 请支持正版，尊重创作者**

</div>
