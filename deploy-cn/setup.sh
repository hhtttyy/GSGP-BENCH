#!/usr/bin/env bash
# setup.sh — ECS 一键配置（由使用者本人在服务器运行；运行前聊天指引已公告安装/下载内容）。
# 用法: bash /root/gsgp-pkg/setup.sh
# 行为公告: dnf 安装 nginx；从 npmmirror（备 jsdelivr）下载 three.js r160 三文件；
#           替换 nginx 主配置（原配置备份）；创建 /etc/gsgp-bench.env（密钥静默粘贴、chmod 600）；
#           安装并启动 gsgp-api systemd 服务与 nginx；条件放行 firewalld http；最后本地验收。
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "请以 root 运行（Workbench 默认 root）。" >&2; exit 1; }
PKG=$(cd "$(dirname "$0")" && pwd)
SITE=/www/wwwroot/gsgp

echo "== 0/7 前置检查"
if ss -ltn 2>/dev/null | grep -q ':80 '; then
  echo "80 端口已被占用（可能是宝塔自带 nginx）。请先在宝塔停用其 nginx，或改用面板路径（README 3A）。" >&2
  exit 1
fi
[ -f "$PKG/www/index.html" ] || { echo "包不完整：缺 www/index.html" >&2; exit 1; }

echo "== 1/7 安装 nginx（dnf，唯一安装项；--disableexcludes 绕过镜像预置的 exclude 过滤）"
if ! command -v nginx >/dev/null 2>&1; then
  dnf install -y --disableexcludes=all nginx
fi
nginx -v

echo "== 2/7 站点文件"
mkdir -p "$SITE"
cp -a "$PKG/www/." "$SITE/"

echo "== 3/7 本地化 three.js（npmmirror 主源 / jsdelivr 备源）"
bash "$PKG/fetch-vendor.sh" "$SITE"

echo "== 4/7 nginx 配置（原主配置备份为 nginx.conf.bak-gsgp）"
[ -f /etc/nginx/nginx.conf.bak-gsgp ] || cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak-gsgp
cp "$PKG/nginx-main.conf" /etc/nginx/nginx.conf
if [ -f /etc/nginx/conf.d/default.conf ]; then mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak-gsgp; fi
mkdir -p /etc/nginx/conf.d/sites
cp "$PKG/nginx-gsgp.conf" /etc/nginx/conf.d/gsgp.conf
nginx -t

echo "== 5/7 AI 代理与密钥"
mkdir -p /opt/gsgp-api
cp "$PKG/api/server.py" /opt/gsgp-api/server.py
if [ ! -f /etc/gsgp-bench.env ]; then cp "$PKG/api/env.template" /etc/gsgp-bench.env; fi
if grep -q "__在服务器上填入你的密钥__" /etc/gsgp-bench.env; then
  read -r -s -p "粘贴 OPENAI_API_KEY（输入不回显，回车结束）: " KEY
  echo
  [ -n "$KEY" ] || { echo "密钥为空，中止。可重跑本脚本补填。" >&2; exit 1; }
  sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${KEY}|" /etc/gsgp-bench.env
  unset KEY
fi
chmod 600 /etc/gsgp-bench.env
cp "$PKG/api/gsgp-api.service" /etc/systemd/system/gsgp-api.service
systemctl daemon-reload
systemctl enable --now gsgp-api

echo "== 6/7 启动 nginx 与防火墙"
systemctl enable --now nginx
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --add-service=http >/dev/null
  firewall-cmd --reload >/dev/null
  echo "firewalld 已放行 http"
fi

echo "== 7/7 本地验收"
if bash "$PKG/verify-cn.sh" http://127.0.0.1 --with-ai; then
  echo
  echo "配置完成。下一步："
  echo "  1) 本机 Mac 运行: bash <repo>/deploy-cn/verify-cn.sh http://101.200.149.60 --with-ai"
  echo "  2) 浏览器打开 http://101.200.149.60/gsgp/ 与 /gsgp/bench/ 目检（根路径 / 会 301 到 /gsgp/）"
  echo "  3) 可选加固: fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab"
else
  echo "存在失败项：把上方输出贴给助手排查。" >&2
  exit 1
fi