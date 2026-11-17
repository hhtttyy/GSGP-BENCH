#!/usr/bin/env bash
# add-site.sh — 未来新增网站脚手架（使用者本人运行；无域名场景按路径前缀区分站点，共用 80）。
# 用法: bash add-site.sh <site-name> [api-port]
# 例:   bash add-site.sh course-site          # 纯静态站 → http://IP/course-site/
#       bash add-site.sh lab-site 8789       # 静态 + 独立 AI 代理 → http://IP/lab-site/
# 行为公告: 创建 /www/wwwroot/<name>/；由模板生成 /etc/nginx/conf.d/sites/<name>.conf
#           （/name/ 前缀 location，被 gsgp.conf 的 server include）；若给 api-port：复制
#           server.py 到 /opt/<name>-api/、生成 /etc/<name>-bench.env（静默粘贴密钥、600）、
#           安装 <name>-api systemd 服务；nginx -t 后 reload；追加登记 /www/wwwroot/SITES.md。
#           不下载任何东西；不需要新开安全组端口（共用 80）；内容文件由你 SFTP 上传。
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "请以 root 运行。" >&2; exit 1; }
PKG=$(cd "$(dirname "$0")" && pwd)
NAME="${1:-}"; API_PORT="${2:-}"
[[ "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "用法: bash add-site.sh <site-name> [api-port]" >&2; exit 2; }
[ "$NAME" != "gsgp" ] || { echo "gsgp 为本站保留名。" >&2; exit 2; }
if [ -n "$API_PORT" ] && ss -ltn 2>/dev/null | grep -q ":$API_PORT "; then echo "端口 $API_PORT 已被占用" >&2; exit 1; fi
ROOT="/www/wwwroot/$NAME"
mkdir -p "$ROOT" /etc/nginx/conf.d/sites

API_BLOCK=""
if [ -n "$API_PORT" ]; then
  API_BLOCK=$(cat <<EOF
location /$NAME/api/ {
    proxy_pass http://127.0.0.1:$API_PORT/api/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Connection "";
    proxy_read_timeout 75s;
    proxy_send_timeout 75s;
    client_max_body_size 32k;
}
EOF
)
fi
sed "s|__NAME__|$NAME|g" "$PKG/nginx-site-template.conf" > /etc/nginx/conf.d/sites/"$NAME".conf
if [ -n "$API_BLOCK" ]; then
  python3 - "$NAME" "$API_BLOCK" <<'PY'
import sys, pathlib
name, block = sys.argv[1], sys.argv[2]
p = pathlib.Path(f"/etc/nginx/conf.d/sites/{name}.conf")
p.write_text(p.read_text().replace("__API_BLOCK__", block), encoding="utf-8")
PY
else
  sed -i '/__API_BLOCK__/d' /etc/nginx/conf.d/sites/"$NAME".conf
fi

if [ -n "$API_PORT" ]; then
  mkdir -p /opt/"$NAME"-api
  cp "$PKG/api/server.py" /opt/"$NAME"-api/server.py
  ENVF=/etc/"$NAME"-bench.env
  if [ ! -f "$ENVF" ]; then
    sed "s|^SITE_ROOT=.*|SITE_ROOT=$ROOT|" "$PKG/api/env.template" > "$ENVF"
  fi
  if grep -q "__在服务器上填入你的密钥__" "$ENVF"; then
    read -r -s -p "粘贴 $NAME 的 OPENAI_API_KEY（不回显）: " KEY; echo
    [ -n "$KEY" ] || { echo "密钥为空，中止。" >&2; exit 1; }
    sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${KEY}|" "$ENVF"; unset KEY
  fi
  chmod 600 "$ENVF"
  sed -e "s|__NAME__|$NAME|g" -e "s|__API_PORT__|$API_PORT|g" "$PKG/api/gsgp-api-template.service" > /etc/systemd/system/"$NAME"-api.service
  systemctl daemon-reload
  systemctl enable --now "$NAME"-api
fi

nginx -t
systemctl reload nginx
echo "| $NAME | /$NAME/ | ${API_PORT:-—} | $ROOT | $(date +%F) |" >> /www/wwwroot/SITES.md
echo
echo "站点 $NAME 脚手架完成："
echo "  1) SFTP 上传该站内容到 $ROOT/（index.html 在根）"
echo "  2) 无需新开安全组端口（共用 80）"
echo "  3) 验收: curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1/$NAME/"
echo "  4) 浏览器: http://101.200.149.60/$NAME/"
[ -n "$API_PORT" ] && echo "  AI: systemctl status $NAME-api --no-pager | head -3"