# Design

## Theme

editorial-ink（frontend-rails）— picked 2026-11-17, re-tuned to the GSGP-Bench brand. Why: 项目已有学术期刊式淡白视觉（纸白 / 苔绿 / 衬线中文），开屏页必须延续它而不是另起一套；editorial-ink 的 token 结构最接近。Light-only：产品要求整体淡白主题，tokens.css 只声明 `color-scheme: light`，无 dark 块。

页面分工：`site/index.html` 为开屏页（landing.css）：three.js 真实 B-DNA 三维舞台（被动慢旋动画，无控制面板）→ 「我们为您服务」三类用户 → 「为『认真比较』而设计的每个细节。」功能 Bento，仅此三段；`site/bench/index.html` 为评测工作台（沿用其内联期刊风格）；`site/resources/**` 为文档页。三者共享 `css/tokens.css` 的色板命名。全站品牌字样统一 `GSGP-BENCH`（无斜线）；开屏页 title 固定为「基因组预测方案智能评估平台--GSGP-Bench」（h1 不带「--」，逐字串仅存于 <title>）。

## Changed tokens

- `--bg: #f1f2ee` / `--surface: #fbfbf8` / `--surface-2: #e9eee7` — 工作台 paper / plate / moss-soft
- `--text: #1b2621` / `--text-muted: #4f5c56` / `--border: #d2d7ce` — 工作台 ink / ink-2 / rule
- `--accent: #3d5a47` / `--accent-hover: #2e4636` — 工作台 moss
- `--danger: #8f5338` — 原 rust #985a3f 在 danger-subtle 上对比度 4.49 < 4.5，gate R09 要求加深
- `--info: #4a607c` / `--clay: #8b5a43` / `--olive: #7b794d` / `--plum: #715c6e` — 证据阶梯六色中的四色，靠图案 + 明度区分
- `--font-display / --font-body / --font-mono` — 项目系统字体栈（宋体衬线 + PingFang + SF Mono），不下载 webfont
- `--fs-hero: clamp(1.5rem, 3.4vw, 2.625rem)` — h1 为「基因组预测方案智能评估平台」+「GSGP-BENCH」两行，14 个汉字须在 38rem 文案栏内单行放下，390 不产生孤字
- `--dur-reveal: 400ms` — gate R16 上限 400ms
- `--nav-h: 64px`（≤600px 56px）— 固定导航高度，锚点 scroll-margin 依赖它

## Rejected

Things the user said no to. Don't bring them back.

- 2026-11 深色模式 — 「开屏页仍保持我们整体淡白色主题」
- 2026-11 外部字体下载 — 用户红线：任何下载/安装由用户执行；字体用系统栈
- 2026-11 页面声音 — 科研平台，刻意不加音乐/音效
- 2026-10 隐藏预设算法 — 「预设的算法被严重隐藏 应该是留出足够空间给我们预设的算法」（工作台）
- 2026-10 内联大表单占据算法栏 — 「暂无MCP文件应该点击后在页面中心弹出卡片…(支持关闭)」
- 2026-10 AI 解读硬换行 — 「不要硬换行，长度自动匹配界面来伸缩」（.analysis-lead 不设 max-width）
- 长期 在线托管算法/MCP — 「我完全不准备托管在线MCP服务」；站点只展示公开聚合结果
- 2026-11 2D canvas 双螺旋开屏 — 「你现在做的根本不是DNA」；改为 three.js 按真实 B-DNA 参数建模（10.5 bp/圈、rise 0.34 nm、糖苷键夹角 140° 形成大/小沟、A=T 两氢键 / G≡C 三氢键、磷酸珠、反平行骨架）
- 2026-11 ImageGen 开屏配图 — 「不使用你生成的图片了」；helix-studio.jpg 已删除，开屏视觉全部由代码渲染
- 2026-11 斜线品牌 GSGP/BENCH — 「统一用GSGP-BENCH而不是中间用斜线」；全站 wordmark 已去掉斜线 span
- 2026-11 「论文里的 r = 0.62…」statement 段及其后除功能 Bento 外的所有小节 — 用户要求删除；statement 位置改为「我们为您服务」（面向哪些用户、解决什么问题），其后仅保留「为『认真比较』而设计的每个细节。」
- 2026-11 DNA 控制坞 / 双指缩放 / 操作提示 — 「我不需要调节双螺旋动画的控制面板 也不需要双指放大以及相关提示」；OrbitControls 整体移除，hero 为被动慢旋动画；参数固定为用户截图配置：speed 1.5（内部系数 0.07 ≈ 6°/s）、bp 24、radius 0.9、motes 350、glow 0.25、fog 0、light 270°、靛蓝×梅紫
- 2026-11 首屏眉题 / h1「--」/ 首屏 CTA 与统计行 / serve 眉题 / 导航段链接 — 用户逐元素标注「去除」；首屏仅余 h1 + lead，导航仅余品牌 + 进入评测台；hero 保持专业清爽
- 2026-11 冗长 lead（含 GBLUP/IFAM/SBayesRC/BayesR 模型名与协议细节）— 「字数太多了，把细节模型名这些精简掉」；随后用户给出逐字终稿（含 Skill/MCP 赋能句）：「把论文里的预测结果，放到你的数据上同条件验真，证据分级、可追溯、数据不出本机，实测汇入公开账本。GSGP-BENCH赋能将论文转化为Skill、MCP，为能力持续沉淀落地。」（measure 52ch，桌面三行）
- 2026-11 中点品牌变体 GSGP·Bench 与_off-palette_ 中性色 #c7cfc4 — 全站统一审计清除：12 个页面标题/正文改 GSGP-BENCH；bench .value-dot 与 generate .kit-dot 改 var(--rule)

## Accepted

- 开屏页终稿截图：/tmp/dna-shots/{hero,full,serve,features}-{1440,768,390}.png + hero-1376x572.png + fallback-1440.png（2026-11-17 被动慢旋·右栏平衡版，42/42 断言通过）
- 工作台期刊风格与居中可关闭预审弹窗（commit fd5fad8，已上线验证）
- 证据词汇：演示 / 探索EXP / 复现L1 / 跨协议L2 / 论文值L3 / 流程测试STUB / 主观估计，绝不混入主榜

## Gate

Rules for `gate/run.mjs`. `ignore: <rule> [selector]` skips a rule; `ban: <css-property>` makes any use of that property an error.

```gate
ignore: R12 .lp-hero-inner    # padding-top = calc(var(--nav-h) + var(--space-6)) 是固定导航偏移，故意不在 --space 刻度上
```

gate 结果（2026-11-17，被动慢旋版）：landing 0 errors 0 warnings（R12 按上述 ignore 跳过）。
Playwright 实测（系统 Chrome，/tmp/verify-dna.mjs，42/42）：__dnaReady、画布实际着色 + readPixels 采样确认螺旋在画面内（1440、390 与用户同比例 1376×572）、螺旋屏幕位置恒定（NDC x 0.560）且慢速原地自转（+0.157 rad/1.5s）、桌面 scale > 1 填满右栏、lead 逐字等于用户终稿且三行、无控制坞/提示/OrbitControls、拖拽不轨道旋转（被动）、滚轮与 CDP 单指滑动均正常翻页、离屏停帧回屏续帧、1200↔1440 resize 稳定且仍右锚、短宽窗口文案与螺旋左右分离无重叠、1440/768/390 零横向溢出零报错、reduced-motion 全静止、CDN 被断时静态示意图降级且首屏文案与正文完好。npm test 26/26。
全站风格统一审计（/tmp/unity-check.mjs，8/8）：/、/bench/、introduce、generate、gblup-baseline、submit、sbayesrc-estimate、ifam-paper 的 body 背景均 #f1f2ee、顶栏均 #fbfbf8、品牌字样均 GSGP-BENCH（无斜线/中点）、标题无旧变体；证据徽章色（exp #394d66 / stub #8d887b / spec #9a7b2f / paper rust / repro moss）bench 与 introduce 完全一致；reader.css 与 tokens.css 主色同名同值。
页头统一（2026-11-17 追加）：介绍/生成/提交三页的 reader-top（斜线 crumbs）替换为与 bench 同源的 masthead——品牌衬线 24px + 副题「基因组预测 · 证据库」、右对齐无斜线导航（首页/评测/介绍/生成/提交/GitHub↗）、当前页 moss 下划线、78px 高与 1180/1080/920/680 断点行为逐条镜像 bench；样式以新增类写入 reader.css（.masthead/.brand/.wordmark/.brand-sub/.mast-nav/.nav-link/.nav-github），其余 reader 页不受影响；print 同步隐藏。generate/submit 补 data-URI favicon（消除 /favicon.ico 404）。/tmp/header-check.mjs 4 页 × 1440/390 全断言通过，截图与 bench 页头逐像素同构。
页头字号（2026-11-17 追加）：用户要求「除 GSGP-BENCH 下的小字外，页头中文与『进入评测台』按钮中文同大小」——按钮为 --fs-base 16px/500；masthead .nav-link 与首页 .lp-brand-sub 统一 16px、weight 500、letter-spacing 0.02em；移除 bench 尾部 Readability pass 残留的 .nav-link 11px 覆盖；GSGP-BENCH 下副题保持小字（9.5/10.5px）。390 下导航单行可容、零溢出。
构图与真实感细则：桌面相机 (11.2,3.4,15.6) + setViewOffset(-0.28w) 把螺旋锚定右栏（NDC x 0.56 ≈ 0.78w，用户要求「再靠右、不要在中间」），并按视口高度自适应放大 dnaGroup.scale（(h-128)/螺旋像素高，上限 1.2）使右栏与左侧文案视觉平衡、且始终避开导航与地面；移动 (12.5,4.2,17.4)、scale 1、dnaGroup.y -1.6 保证整条螺旋入画；骨架 TubeGeometry 收在首末磷酸珠之间（管口藏珠内，无开放截面）；碱基为 RoundedBox 平板（芳香环面）+ propeller 倾斜；光照按用户指定 270°：暖 key 背顶高角度 (cos·7, 9, sin·7) 产生轮廓光、靛蓝 fill 前顶保证形体可读、陶土 rim 侧低角度；投影阴影移除（避免地面灰色拖影），改为烘焙接触阴影椭圆盘 + pedestal 光盘，二者随 dnaGroup 对齐螺旋正下方；降级卡固定于 DNA 展示区（右侧宽度自适应、移动端底部带）并隐藏 scrim（scrim 只服务于 3D 背景）。「我们为您服务」三卡为用户明确要求的三类用户，接受其三联结构（首卡加宽 + 苔绿底打破均质）。
three.js motion：importmap 引 jsdelivr three@0.160.0（dynamic import，失败/超时 9s → 静态 SVG 降级卡）；单一 rAF 循环、无 OrbitControls（被动动画），DPR cap 1.75，PMREM RoomEnvironment 环境光一次烘焙 + ACES 色调映射，氢键辉光脉动、漂移尘埃粒子；canvas 不拦截任何指针/滚轮/触摸事件，页面滚动全区域自然。reduced-motion 下不自转、按需只渲染脏帧；离屏/hidden 停 rAF。