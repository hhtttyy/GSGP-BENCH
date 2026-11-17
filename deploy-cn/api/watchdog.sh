#!/usr/bin/env bash
# watchdog.sh — 回环 AI 服务存活检查（systemd timer 每分钟调用）。
# 用法: watchdog.sh <service-name> <port>   例: watchdog.sh gsgp-api 8787
# 判活: GET /api/analyze 应返回 405（方法拒绝=进程活着且路由正常）；
#       连接失败/超时/其他码 => systemctl restart 并记日志。无 systemctl 时仅提示（本地 dry-run）。
set -uo pipefail
SVC="${1:?usage: watchdog.sh <service> <port>}"
PORT="${2:?usage: watchdog.sh <service> <port>}"
code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 -X GET "http://127.0.0.1:$PORT/api/analyze" 2>/dev/null)
code=${code:-000}
if [ "$code" = "405" ]; then
  exit 0
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl restart "$SVC"
  logger -t gsgp-watchdog "restart $SVC (health code=$code)"
else
  echo "[dry] would restart $SVC (health code=$code)"
fi
exit 0