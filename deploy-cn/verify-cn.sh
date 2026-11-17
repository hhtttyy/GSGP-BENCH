#!/usr/bin/env bash
# verify-cn.sh — 部署后验收（使用者执行）。站点前缀 /gsgp/。
# 用法: bash verify-cn.sh http://101.200.149.60 [--with-ai]
set -uo pipefail
BASE="${1:-http://101.200.149.60}"
WITH_AI="${2:-}"
fail=0
check() { # check <路径> <期望码>
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 "$BASE$1")
  if [ "$code" = "$2" ]; then echo "PASS $code $1"; else echo "FAIL $code $1 (期望 $2)"; fail=1; fi
}
check / 301
check /bench/ 301
check /gsgp/ 200
check /gsgp/index.html 200
check /gsgp/bench/ 200
check /gsgp/bench/index.html 200
check /gsgp/resources/introduce/index.html 200
check /gsgp/resources/generate/index.html 200
check /gsgp/resources/submit/index.html 200
check /gsgp/css/landing.css 200
check /gsgp/css/tokens.css 200
check /gsgp/data/catalog/allowed-methods.json 200
check /gsgp/vendor/three.module.js 200
check /gsgp/vendor/addons/environments/RoomEnvironment.js 200
check /gsgp/vendor/addons/geometries/RoundedBoxGeometry.js 200

if curl -s --max-time 20 "$BASE/gsgp/" | grep -q 'assets/dna-mobile.webp'; then
  echo "PASS 开屏含静态帧基层（webp，移动端免 three.js/WebGL）"
else
  echo "FAIL 开屏静态帧标记缺失"; fail=1
fi
if curl -s --max-time 20 "$BASE/gsgp/" | grep -q 'type="importmap"'; then
  echo "PASS 混合标记：桌面渐进升级 importmap 存在"
else
  echo "FAIL 混合 importmap 缺失（线上仍为纯静态或旧版）"; fail=1
fi
enc=$(curl -s -o /dev/null -D - -H "Accept-Encoding: gzip" --max-time 20 "$BASE/gsgp/css/landing.css" | tr -d '\r' | awk -F': ' 'tolower($1)=="content-encoding"{print $2}')
if [ "$enc" = "gzip" ]; then echo "PASS gzip 生效"; else echo "WARN gzip 未生效（检查 nginx 配置）"; fi

if [ "$WITH_AI" = "--with-ai" ]; then
  code=$(curl -s -o /tmp/gsgp-analyze.json -w "%{http_code}" --max-time 75 -X POST "$BASE/gsgp/api/analyze" \
    -H "Content-Type: application/json" -H "Origin: $BASE" \
    -d '{"metric":"Pearson r","selection":{"algorithms":["GBLUP"],"datasets":["sim1000g"]},"cells":[{"algorithm":"GBLUP","dataset":"sim1000g","status":"探索EXP","value":0.52,"sd":0.04}]}')
  if [ "$code" = 200 ] && grep -q '"text"' /tmp/gsgp-analyze.json; then
    echo "PASS /gsgp/api/analyze 200（$(python3 -c "import json;print(json.load(open('/tmp/gsgp-analyze.json')).get('model'))" 2>/dev/null)）"
  else
    echo "FAIL /gsgp/api/analyze $code（检查 gsgp-api 服务与 /etc/gsgp-bench.env）"; fail=1
  fi
  code=$(curl -s -o /tmp/gsgp-prospective.json -w "%{http_code}" --max-time 75 -X POST "$BASE/gsgp/api/prospective" \
    -H "Content-Type: application/json" -H "Origin: $BASE" \
    -d '{"method_name":"BayesR","paper_url":"https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1004969","repo_url":"https://github.com/example/bayesr"}')
  if [ "$code" = 200 ] && grep -q 'gsgp.prospective-preview.v1' /tmp/gsgp-prospective.json; then
    echo "PASS /gsgp/api/prospective 200（待认证预览，5 数据集模板）"
  else
    echo "FAIL /gsgp/api/prospective $code"; fail=1
  fi
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$BASE/gsgp/api/analyze")
  [ "$code" = 405 ] && echo "PASS GET /gsgp/api/analyze 405" || { echo "FAIL GET 应 405 实 $code"; fail=1; }
fi
echo
[ "$fail" = 0 ] && echo "验收通过：浏览器打开 $BASE/gsgp/ 应见三维双螺旋；/gsgp/bench/ 为评测台。" || { echo "存在失败项，先修复再验收。"; exit 1; }