#!/usr/bin/env bash
# 腾讯云 / 任意 Linux 一键部署脚本
# 用法:  bash deploy/deploy.sh            # 仅视频(SSR, 轻量)
#        bash deploy/deploy.sh --with-browser   # 额外装 Playwright(支持图文, 较重)
set -e
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ"
echo ">> project: $PROJ"

# root 或无 sudo 时不用 sudo
if [ "$(id -u)" = "0" ]; then SUDO=""; elif command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else SUDO=""; fi

# 1) 系统依赖
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update -y
  $SUDO apt-get install -y python3 python3-venv python3-pip
elif command -v yum >/dev/null 2>&1; then
  $SUDO yum install -y python3 python3-pip
elif command -v dnf >/dev/null 2>&1; then
  $SUDO dnf install -y python3 python3-pip
else
  echo "!! 未识别的包管理器，请手动安装 python3"; exit 1
fi

# 2) 虚拟环境 + 依赖
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 3) 可选: 无头浏览器(图文作品需要)
if [ "$1" = "--with-browser" ]; then
  .venv/bin/python -m playwright install --with-deps chromium \
    || echo "!! playwright 安装失败：图文解析不可用，视频不受影响"
fi

# 4) systemd 服务(用真实路径生成)
cat > /tmp/douyin-nowm.service <<EOF
[Unit]
Description=Douyin watermark-free downloader (personal)
After=network.target

[Service]
WorkingDirectory=$PROJ
ExecStart=$PROJ/.venv/bin/gunicorn -w 2 --threads 4 --timeout 300 -b 0.0.0.0:8765 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
$SUDO cp /tmp/douyin-nowm.service /etc/systemd/system/douyin-nowm.service
$SUDO systemctl daemon-reload
$SUDO systemctl enable douyin-nowm
$SUDO systemctl restart douyin-nowm

# 5) 放行系统防火墙(若启用)
if command -v ufw >/dev/null 2>&1 && $SUDO ufw status | grep -q active; then
  $SUDO ufw allow 8765/tcp || true
elif command -v firewall-cmd >/dev/null 2>&1; then
  $SUDO firewall-cmd --permanent --add-port=8765/tcp || true
  $SUDO firewall-cmd --reload || true
fi

echo ""
echo "================ 部署完成 ================"
echo "  还需在腾讯云控制台【安全组】放行 TCP 8765"
echo "  然后手机/电脑访问:  http://<你的公网IP>:8765"
echo "  查看日志: journalctl -u douyin-nowm -f"
echo "=========================================="
