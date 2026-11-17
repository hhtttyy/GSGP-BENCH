# GSGP-BENCH 国内部署包（ECS · IP 直连 · 无域名）

目标机器：阿里云 ECS ecs.e-c1m1.large（2vCPU 2GiB · 3M 固定带宽 · 40G ESSD Entry · Alibaba Cloud Linux 4 LTS），公网 IP `101.200.149.60`。
包内容：`www/`（最新版站点，importmap 已指向站内 `vendor/`）、`fetch-vendor.sh`（three.js 本地化，**由你执行**）、`nginx-gsgp.conf`（无面板完整配置）、`nginx-gsgp-snippet.conf`（宝塔粘贴片段）、`verify-cn.sh`（验收脚本）。

红线提醒：本包不替你下载任何东西。`fetch-vendor.sh` 与 nginx 安装命令都由你本人运行；主源为 registry.npmmirror.com（阿里国内镜像，2026-11-17 实测 200 且无跨域跳转），备源 cdn.jsdelivr.net。

## 0. 安全组（控制台 → 网络与安全组）

1. 入方向放行 TCP 80（源 0.0.0.0/0）与 TCP 22（源尽量填你的出口 IP/32）。验证：规则列表可见两条。
2. 若走宝塔路径：初始化期间临时放行面板端口（默认 8888，安装后宝塔会提示改端口），完成后删除该公网放行。验证：外网无法再连面板端口。
3. 不要放行 3306/6379/888/21 等无关端口。

## 1. 上传站点文件

1. 把 `deploy-cn.zip` 上传到服务器（宝塔文件管理或 scp），解压到 `/root/gsgp-pkg`。验证：`ls /root/gsgp-pkg` 见 www、fetch-vendor.sh 等。
2. 建立站点根目录并拷入网页：`mkdir -p /www/wwwroot/gsgp && cp -a /root/gsgp-pkg/www/. /www/wwwroot/gsgp/`（宝塔路径也可在文件管理里全选复制）。验证：`ls /www/wwwroot/gsgp` 见 index.html、bench、resources、css、data。

## 2. 本地化 three.js（你执行，约 1.3MB）

命令：`bash /root/gsgp-pkg/fetch-vendor.sh /www/wwwroot/gsgp`
验证：输出三行 ok 与「完成」；`ls -l /www/wwwroot/gsgp/vendor` 见 three.module.js 与 addons 两文件。此步完成前首页会显示「三维模型暂不可用」静态降级卡，属预期。

## 3. Web 服务（二选一）

> 推荐一键路径：完成第 1、2 步后直接 `bash /root/gsgp-pkg/setup.sh`（安装/下载内容已在聊天指引公告；含密钥静默粘贴、nginx 主配置替换备份、systemd 服务、firewalld 条件放行、本地验收）。以下手动路径保留供排查与宝塔面板场景。

### A. 宝塔面板路径（镜像已带面板时）

1. 浏览器 `http://101.200.149.60:8888` 登录面板（首次按初始化提示设置账号/改端口）。验证：面板首页可见。
2. 软件商店只安装 **Nginx**（不装 MySQL/PHP/FTP，2G 内存留给系统）。验证：已安装列表仅 Nginx。
3. 网站 → 添加站点：域名栏填 `101.200.149.60`，根目录 `/www/wwwroot`（gsgp 的父目录，前缀由 snippet 提供），不建数据库/FTP。验证：站点列表出现条目。
4. 站点设置 → 配置文件：把 `nginx-gsgp-snippet.conf` 内容粘贴进 server{} 内（若与宝塔已有 gzip/charset 重复则只保留两个 location）。保存后面板会自动 reload。验证：配置页无报错提示。

### B. 无面板路径（纯系统）

1. 安装：`dnf install -y nginx`（你执行）。验证：`nginx -v` 有版本输出。
2. 配置：`cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak-gsgp && cp /root/gsgp-pkg/nginx-main.conf /etc/nginx/nginx.conf`（保证 gsgp 为 80 唯一 server）；若存在 `/etc/nginx/conf.d/default.conf` 先移走备份；`cp /root/gsgp-pkg/nginx-gsgp.conf /etc/nginx/conf.d/gsgp.conf`。验证：`nginx -t` 输出 syntax ok / test successful。
3. 启动：`systemctl enable --now nginx`。验证：`systemctl is-active nginx` = active。

## 4. 验收（你执行）

1. 脚本：`bash /root/gsgp-pkg/verify-cn.sh http://101.200.149.60`。验证：全部 PASS（gzip 一项 WARN 不阻塞）。
2. 浏览器（国内网络）：`http://101.200.149.60/gsgp/` 首屏渲染缓慢自转的三维双螺旋、无降级卡；`/gsgp/bench/` 进入评测台且表格/弹窗可用；`/gsgp/resources/introduce/index.html` 页头与评测页同构。验证：三页截图留档。
3. 重复刷新与拖拽页面滚动 10 次无报错、无白屏（浏览器控制台应无红色错误）。

## 5. 可选加固

1. 2G 内存防 OOM（控制台已提示「内存优化」）：`fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab`（你执行）。验证：`free -h` 见 Swap 2G。
2. 宝塔路径：面板设置里关闭面板 SSL 自签告警无关项、开启「面板入口安全码」；Nginx 免费防火墙可选。
3. 更新站点：重新打包 `site/`（排除 `.gate/`）覆盖 `/www/wwwroot/gsgp`，再跑一次 fetch-vendor.sh 与 verify-cn.sh 即可；vendor 已存在时脚本会覆盖为同版本文件，安全。

## 6. 启用国内 AI 解读与预审（可选但推荐，零第三方依赖）

包内 `api/server.py` 为纯 Python 标准库服务，行为与 Cloudflare Worker 的 `/api/analyze`、`/api/prospective` 对齐（聚合数字-only、允许清单预审、待认证标注、失败回退模板）。仅监听 127.0.0.1:8787，由 nginx 反代，密钥只存服务器 env 文件。

1. 放置代码：`mkdir -p /opt/gsgp-api && cp /root/gsgp-pkg/api/server.py /opt/gsgp-api/`。验证：`python3 -m py_compile /opt/gsgp-api/server.py` 无输出。
2. 创建密钥文件（**你本人在服务器上填写密钥**）：`cp /root/gsgp-pkg/api/env.template /etc/gsgp-bench.env && chmod 600 /etc/gsgp-bench.env`，编辑填入 `OPENAI_API_KEY`；其余默认即你的配置（Base URL `https://maas.qianwenaiapi.com/compatible-mode/v1`、模型 `qwen3.8-flash`、`AI_DISABLE_THINKING=1` 对应 `enable_thinking: false`）。验证：`stat -c %a /etc/gsgp-bench.env` = 600。
3. 安装服务：`cp /root/gsgp-pkg/api/gsgp-api.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now gsgp-api`。验证：`systemctl is-active gsgp-api` = active；`journalctl -u gsgp-api -n 5` 见 listening 行且无密钥字样。
4. nginx 增加反代：无面板路径已含于 `nginx-gsgp.conf` 的 `location /api/`；宝塔路径把片段中同段粘贴进站点配置。重载后验证：`curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1/api/analyze` = 400（空体被拒，说明反代通了）。
5. 验收：`bash /root/gsgp-pkg/verify-cn.sh http://101.200.149.60 --with-ai`。验证：analyze 200 且 model 为 qwen3.8-flash、prospective 200 且为待认证预览、GET 405。
6. 浏览器：评测台点「AI 解读」应出现真实中文解读（带「仅供参考」徽标）；提交弹窗生成待认证预览不再报「服务未配置」。

安全与运维提醒：该密钥现存在于三处（本地 .dev.vars、Worker Secret、ECS env），方便时轮换并同步三处；服务只读站点允许清单文件、不写任何数据；`AI_MOCK=1` 可临时切回无密钥版式测试；上游失败时预审自动回退允许清单模板并如实标注，解读返回 502 设计态提示。

## 8. 多站点扩展（无域名 ⇒ 按路径前缀区分，共用 80）

本站对外为 `http://IP/gsgp/`，根路径 `/` 与 `/index.html` 301 到 `/gsgp/`。目录约定：每站一个根目录 `/www/wwwroot/<name>/`（index.html 在根）；nginx 单 server（:80，root /www/wwwroot）内以 `location /<name>/` 区分站点，未来站点的 location 由 add-site.sh 生成到 `/etc/nginx/conf.d/sites/<name>.conf` 并被主 server include；AI 代理每站独立 `/opt/<name>-api/` + `/etc/<name>-bench.env`(600) + `<name>-api.service`（仅回环端口，预留 8788–8797）。登记表 `/www/wwwroot/SITES.md`（站点/前缀/AI端口/根目录/日期）。

新增站三步（使用者执行）：
1. SFTP 上传该站内容到 `/www/wwwroot/<name>/`。
2. `bash /root/deploy-cn/add-site.sh <name> [api-port]`（公告：建目录、生成前缀 location、可选复制 server.py 并静默粘贴该站密钥、装 systemd 服务、nginx -t 后 reload、追加登记；不下载任何东西；**无需新开安全组端口**）。
3. 验收 `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/<name>/` 与浏览器 `http://101.200.149.60/<name>/`。

说明：bench 前端以 `../api/` 相对站点根调用 AI（根部署解析为 /api/、前缀部署解析为 /gsgp/api/），各站 nginx 只反代自己的回环 AI 端口，天然隔离，无需改前端；将来购域名并备案后，可加 server_name 与 443 证书，前缀方案平滑过渡。架构图见包内 `architecture.html`。

## 9. 内部 API 稳定性与多项目共享

稳定性机制（三层）：① systemd `Restart=always` + `RestartSec=2`——任何退出（含崩溃、OOM kill）2 秒内拉起；② 存活 watchdog：`gsgp-api-watchdog.timer` 每 60s 调 `watchdog.sh gsgp-api 8787`，以 `GET /api/analyze` 应得 405 判活，异常即 `systemctl restart` 并写 journal；③ 服务自身：ThreadingHTTPServer 并发、上游 60s 超时防线程挂死、仅回环监听无外部攻击面。检查：`systemctl show gsgp-api -p NRestarts -p ActiveEnterTimestamp`（NRestarts=0 即从未崩溃）、`systemctl list-timers gsgp-api-watchdog.timer --no-pager`。

共享边界：`/api/analyze` 无状态、只回显请求里的聚合数字 ⇒ 服务器上任何项目都可直调 `127.0.0.1:8787/api/analyze`（或把该站 nginx 的 `location /api/` proxy_pass 指向 8787）；`/api/prospective` 读取 `SITE_ROOT` 下 gsgp 允许清单 ⇒ 语义属 gsgp，其他项目需要预审时用 `add-site.sh <name> <port> <api-port>` 起独立实例（独立 env/清单/端口，约 30MB/实例）。回环意味着机内进程互信（单主人服务器可接受）；Origin 校验只约束经 nginx 的浏览器请求。

### 9.1 超时 / 余额不足等错误在哪里看（三层）

1. **页面**：bench「AI 解读」面板红字直接给原因（余额不足 / 密钥无效 / 限流 / 超时 / 连接失败 / 上游错误）；提交弹窗显示「AI 预审失败（原因），已回退到允许清单模板」，记录仍为待认证。
2. **日志**（Termius）：实时 `journalctl -u gsgp-api -f`；回溯 `journalctl -u gsgp-api --since "-24h" -o cat --no-pager | grep -E "upstream_error|failed"`。每条 `upstream_error` 行含 `status=`（上游 HTTP 码）、`class=`（分类）、`detail=`（上游原文前 200 字符，**不含密钥**）；成功行含 `ok ms=` 耗时，可观察超时趋势。
3. **汇总脚本**：`bash /opt/gsgp-api/api-status.sh`（或包内 `api/api-status.sh`）——服务 active/NRestarts/存活起点、watchdog 下次触发、近 24h 六类错误计数、最近错误与成功耗时；加 `--probe` 才发起一次真实调用主动验证上游（消耗极少量余额），默认零消耗。

错误码对照：`AI_BALANCE_INSUFFICIENT`（402 或原文含 arrearage/余额/欠费 → 充值 MaaS）；`AI_AUTH_INVALID`（401/密钥无效 → 查 env 密钥）；`AI_RATE_LIMITED`（429/quota → 稍后或提配额）；`AI_TIMEOUT`（超过 `AI_TIMEOUT_SEC`，默认 60，可在 env 调）；`AI_CONNECT_FAILED`（出站网络/Base URL）；`AI_UPSTREAM_ERROR`（其他上游码）；`AI_EMPTY_RESPONSE`（上游空文本）。watchdog 只判进程存活（405），**不会**自动发起付费调用；上游故障靠上述三层发现，进程故障靠 watchdog 自愈。

## 10. 开屏混合策略（阿里云版：移动静态秒开 / 桌面 three.js 慢旋）

基层为**同一 three.js 场景的静止渲染帧**：`assets/dna-desktop.webp`（1600×1000，54KB）与 `assets/dna-mobile.webp`（780×1688，55KB），另附 png 兜底（仅不支持 webp 的老浏览器加载）。帧由无头浏览器对真实场景单帧渲染（reduced-motion、旋转角 0.55）导出，**非 AI 生成图**；所有设备先秒开静态帧。

桌面渐进增强：视口 >900px 且非 reduced-motion 且 WebGL 可用时，动态 import 本地 `vendor/` three.js（gzip 后约 160KB 传输，不碰 CDN），首帧渲染后隐藏静态帧、进入慢旋；import 失败或 WebGL 不可用则**保持静态帧**（静态帧即兜底，无需降级卡）；视口缩回 ≤900px 时停循环并换回静态帧。移动端（≤900px，含竖屏平板）与 reduced-motion 永远不加载 three.js：实测首屏图像传输 55KB、DOMContentLoaded 60–86ms（本地）、零 CDN 请求。bench/resources 与 AI 链路不受影响（实测解读/预审仍真实可用）。

GitHub 线（`site/` 与 workers.dev）按用户指示暂不动（仍 CDN 全动画）；服务器 `vendor/` 为桌面升级所必需，保留。验收：`verify-cn.sh` 查静态帧标记 + importmap 混合标记；桌面升级与移动静态以部署后双端目检闭环。

## 11. 版本更新标准流程（每次改包后必走四步）

1. SFTP 上传新 `deploy-cn.zip` 到 `/root/` 覆盖；`stat -c %s /root/deploy-cn.zip` 与发布说明字节数核对。
2. `cd /root && unzip -o deploy-cn.zip >/dev/null`（只更新 /root/deploy-cn，**不会**自动影响线上）。
3. **同步到站点根**：`\cp -a /root/deploy-cn/www/. /www/wwwroot/gsgp/`（漏此步＝线上仍是旧前端；纯静态覆盖，无需 reload/restart）。
4. 验收：`bash /root/deploy-cn/verify-cn.sh http://127.0.0.1 --with-ai` 全 PASS + 浏览器目检。
多站点同理：同步到对应 `/www/wwwroot/<name>/`。nginx/systemd 配置类改动才需要 `nginx -t && systemctl reload nginx` / `daemon-reload + restart`。

## 已知边界（设计态，非缺陷）

- 未启用第 6 节时，AI 解读与在线预审依赖你的 Cloudflare Worker（`/api/analyze`、`/api/prospective`），workers.dev 国内不通，纯静态部署下这两处显示「服务未配置/不可用」的设计提示，主比较流程不受影响；启用第 6 节后由 ECS 本地代理提供同配置服务（qwen3.8-flash · enable_thinking=false）。
- 无域名即无 ICP 备案需求（备案约束的是域名解析）；IP 直连 80 端口如被接入商拦截，可改 listen 8080 并在安全组放行 8080，访问加端口号。
- 站点为纯静态 + 本地 three.js，无数据库、无上传入口，攻击面仅 nginx 与 SSH。