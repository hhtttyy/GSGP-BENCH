#!/usr/bin/env bash
# fetch-vendor.sh — 由使用者本人执行（红线：不自动下载）。
# 用法: bash fetch-vendor.sh /www/wwwroot/gsgp
# 作用: 把 three.js r160 的三个模块文件拉进站点 vendor/ 目录，供开屏页本地加载。
# 源审计: 主源 registry.npmmirror.com（阿里国内镜像，2026-11-17 实测 200、无跨域跳转）；
#         备源 cdn.jsdelivr.net（同日实测 200）。两个 addon 仅 import 裸 'three'，无其它相对依赖。
set -euo pipefail

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "用法: bash fetch-vendor.sh <站点根目录>" >&2
  exit 2
fi
if [ ! -f "$TARGET/index.html" ]; then
  echo "错误: $TARGET 下没有 index.html，请确认站点根目录。" >&2
  exit 2
fi

V="$TARGET/vendor"
mkdir -p "$V/addons/environments" "$V/addons/geometries"

fetch() { # fetch <相对路径> <主源URL> <备源URL>
  local rel="$1" primary="$2" fallback="$3" out="$V/$1"
  if curl -fL --retry 2 --connect-timeout 15 --max-time 120 -o "$out" "$primary"; then
    echo "ok  npmmirror  $rel"
  elif curl -fL --retry 2 --connect-timeout 15 --max-time 120 -o "$out" "$fallback"; then
    echo "ok  jsdelivr   $rel"
  else
    echo "失败: $rel 两个源均不可达" >&2
    exit 1
  fi
  [ -s "$out" ] || { echo "失败: $rel 为空文件" >&2; exit 1; }
}

fetch "three.module.js" \
  "https://registry.npmmirror.com/three/0.160.0/files/build/three.module.js" \
  "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
fetch "addons/environments/RoomEnvironment.js" \
  "https://registry.npmmirror.com/three/0.160.0/files/examples/jsm/environments/RoomEnvironment.js" \
  "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/environments/RoomEnvironment.js"
fetch "addons/geometries/RoundedBoxGeometry.js" \
  "https://registry.npmmirror.com/three/0.160.0/files/examples/jsm/geometries/RoundedBoxGeometry.js" \
  "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/geometries/RoundedBoxGeometry.js"

grep -q "REVISION" "$V/three.module.js" || { echo "失败: three.module.js 内容异常" >&2; exit 1; }
grep -q "RoomEnvironment" "$V/addons/environments/RoomEnvironment.js" || { echo "失败: RoomEnvironment.js 内容异常" >&2; exit 1; }
grep -q "RoundedBoxGeometry" "$V/addons/geometries/RoundedBoxGeometry.js" || { echo "失败: RoundedBoxGeometry.js 内容异常" >&2; exit 1; }

echo "完成: vendor/ 三个文件就绪（$(du -sh "$V" | cut -f1)）。刷新首页应渲染三维双螺旋。"