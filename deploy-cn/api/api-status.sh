#!/usr/bin/env bash
# api-status.sh — AI 服务健康与错误观测（使用者执行；默认零消耗，只读状态与日志）。
# 用法: bash api-status.sh [service-name] [port] [--probe]
#   --probe 才会发起一次真实解读调用（消耗极少量余额），用于主动验证上游连通/余额/密钥。
set -uo pipefail
SVC="${1:-gsgp-api}"; PORT="${2:-8787}"; PROBE="${3:-}"
echo "== 服务状态"
systemctl is-active "$SVC"
systemctl show "$SVC" -p NRestarts -p ActiveEnterTimestamp
echo "== watchdog 下次触发"
systemctl list-timers "$SVC-watchdog.timer" --no-pager 2>/dev/null | head -3
echo "== 近 24h 错误分类计数"
for cls in balance auth rate timeout connect upstream; do
  n=$(journalctl -u "$SVC" --since "-24h" -o cat --no-pager 2>/dev/null | grep -c "class=$cls")
  echo "  $cls: ${n:-0}"
done
echo "== 最近错误（末 8 条，含上游状态与原文摘要）"
journalctl -u "$SVC" --since "-24h" -o cat --no-pager 2>/dev/null | grep -E "upstream_error|failed|empty_response" | tail -8
echo "== 最近成功与耗时（末 3 条）"
journalctl -u "$SVC" --since "-24h" -o cat --no-pager 2>/dev/null | grep " ok ms=" | tail -3
if [ "$PROBE" = "--probe" ]; then
  echo "== 真实探针（消耗一次解读调用）"
  curl -s -m 75 -X POST "http://127.0.0.1:$PORT/api/analyze" -H "Content-Type: application/json" \
    -d '{"metric":"Pearson r","selection":{"algorithms":["GBLUP"],"datasets":["sim1000g"]},"cells":[{"algorithm":"GBLUP","dataset":"sim1000g","status":"探索EXP","value":0.52,"sd":0.04}]}' \
    | python3 -c "import json,sys; d=json.load(sys.stdin); e=d.get('error'); print('ERROR', e['code'], e['message']) if e else print('OK model=', d.get('model'), 'chars=', len(d.get('text','')))"
fi