<template>
  <div class="lc-scale" :style="scaleStyle">
    <div class="lc-frame" :class="{ 'lc-frame-float': isFloatMode }">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
// 根组件:只挂 router-view，页面由 src/views 下的 SFC 提供
// 第 71 批（口径升级）:产物视口等比缩放 —— 由「固定基准宽无条件缩」改为「内容固有需求驱动」。
//  触发源:挂载 / 路由切换 / 字体就绪时，在未缩放态实测内容固有尺寸 (needW, needH) 并累进全局最大（只增不减）;
//  resize 只做一条除法:s = min(1, 可用宽 / needW, 可用高 / needH)，clamp 到 0.5 —— 零重排、零迭代、零抖动。
//  手段:transform:scale（规范明确不影响布局）+ 窄窗容器 fixed 脱离文档流（反补占位不进文档滚动区）。
//  口径:可用空间 ≥ 内容固有需求 → 系数 1（不写任何行内样式，宽窗零回归）;任一轴不足 → 取更紧的那个，缩到刚好。
//  反补宽高:缩放时容器宽高改为 (100 / 系数)%，抵消 transform 不缩布局的特性，缩放后仍严丝合缝铺满视口。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CSSProperties } from 'vue'
import { useRoute } from 'vue-router'

/** 兜底基准宽（px）:内容探测失败（0 / NaN / 异常）时回退该值，保证任何环境下都有可用基准（C9 单一数据源） */
const FALLBACK_BASE_WIDTH = 1280

/** 缩放系数下限:极小窗口下最多缩到该值（第 71 批由 0.2 提升到 0.5），避免整页缩成一个不可操作的点 */
const MIN_SCALE = 0.5

/** 读取视口可用宽:优先 documentElement.clientWidth（已扣文档纵向滚动条宽）——
 *  用 window.innerWidth 会出现「出滚动条 → 系数变小 → 又不出 → 系数变回」的抖动回路。 */
function resolveViewportWidth(): number {
  return document.documentElement.clientWidth || window.innerWidth
}

/** 读取视口可用高:同上（clientHeight 已扣文档横向滚动条高）—— 两轴同源，避免口径分叉 */
function resolveViewportHeight(): number {
  return document.documentElement.clientHeight || window.innerHeight
}

/** 当前视口可用宽（resize 时同步更新，驱动下方 scale 重算） */
const viewportWidth = ref(resolveViewportWidth())

/** 当前视口可用高（resize 时同步更新，驱动下方 scale 重算） */
const viewportHeight = ref(resolveViewportHeight())

/** 内容固有宽的全局极限（全项目一个最大极限，只增不减 —— 第 71 批口径 ②a） */
const needW = ref(0)

/** 内容固有高的全局极限（同上;成对自洽:needH 是在 needW 这个宽度下量到的高） */
const needH = ref(0)

/** 在「未缩放态」实测当前页内容的固有尺寸（同步块内量完即恢复，用户不可见）——
 *  临时把 .lc-scale 置为 transform:none + width:min-content + height:auto，
 *  量到的是「内容不被挤压所需的最小外接矩形」(needW, needH)
 *  （flex 的 min-content 正是「按钮不被压扁 / 文字不换行」所需的最小宽）;
 *  量完立刻恢复原行内样式 —— 全程同一同步块，不闪烁、不残留副作用。 */
function measureContent(): void {
  // 无 document 环境（SSR / 测试 / 极端宿主）首行守卫，缺失即跳过
  if (typeof document === 'undefined') return
  const el = document.querySelector('.lc-scale') as HTMLElement | null
  if (!el) return
  // 暂存当前行内样式（宽窗下为 null;窄窗下为 scaleStyle 写下的那一串）
  const savedStyle = el.getAttribute('style')
  // 置为「未缩放 + 按内容最小宽排布」的临时态（量内容固有尺寸，而不是量被挤压后的尺寸）
  el.style.transform = 'none'
  el.style.position = 'static'
  el.style.width = 'min-content'
  el.style.height = 'auto'
  el.style.overflow = 'visible'
  // 同步读取（读取即强制布局，量到的就是本刻真实值 —— 同一同步块内量完即恢复，无可见中间态）
  // 点2（治根）:候选尺寸钳制到视口可用上限 ——
  //   长不可断 token（长路径/长函数名）在单文件 layout 阶段仍可能把 min-content 撑大，
  //   一旦入账 needW（只增不减）就再难回落；钳制到视口宽高后，
  //   任何页面的长 token 假象都不再污染 needW，内容宽超视口时改由内部滚动（.lc-scale overflow:auto）承载。
  const candidateW = Math.min(el.scrollWidth, resolveViewportWidth())
  const candidateH = Math.min(el.scrollHeight, resolveViewportHeight())
  // 恢复原行内样式（有则还原、无则清空）
  if (savedStyle === null) el.removeAttribute('style')
  else el.setAttribute('style', savedStyle)
  // 兜底:异常值（0 / NaN / 负数）不入账，避免把系数算崩;合法值才累进全局最大（只增不减）
  if (Number.isFinite(candidateW) && candidateW > 0) needW.value = Math.max(needW.value, candidateW)
  if (Number.isFinite(candidateH) && candidateH > 0) needH.value = Math.max(needH.value, candidateH)
}

/** 下一帧测量（挂载 / 路由切换 / 字体就绪三处统一入口 —— 等浏览器完成布局后再量，量到的是稳定值） */
function scheduleMeasure(): void {
  if (typeof window === 'undefined') return
  window.requestAnimationFrame(() => measureContent())
}

/** 窗口尺寸变化:只更新可用宽高，重算交给 computed（**不测量、不碰布局** —— 零重排、零抖动） */
function onResize(): void {
  viewportWidth.value = resolveViewportWidth()
  viewportHeight.value = resolveViewportHeight()
}

// 路由实例:产物是 SPA，切到另一页内容就变了 → 必须重测（第 71 批测量时机 2/3）
const route = useRoute()
/** 悬浮窗模式:URL 带 ?mode=float 时命中（与 PageO0x2f.vue 判定同源同写法，仅用于悬浮窗外边距归零） */
const isFloatMode = computed<boolean>(() => route.query.mode === 'float')
watch(() => route.fullPath, () => scheduleMeasure())

onMounted(() => {
  window.addEventListener('resize', onResize)
  // 时机 1:挂载后下一帧首测（rAF 保证浏览器已完成首屏布局，量到的是稳定值）
  scheduleMeasure()
  // 时机 3:字体就绪后补测一次（防自定义字体的异步字重差异引起高度失准）
  const fonts = (document as unknown as { fonts?: { ready?: Promise<unknown> } }).fonts
  if (fonts && fonts.ready) fonts.ready.then(() => scheduleMeasure()).catch(() => {})
})

onBeforeUnmount(() => window.removeEventListener('resize', onResize))

/** 缩放系数（第 71 批口径）:可用空间 ≥ 内容固有需求 → 1（**不写任何行内样式**，零回归）;
 *  任一轴不足 → 取两轴比值里更紧的那个（谁更紧听谁的），缩到「刚好」;
 *  下限 MIN_SCALE（缩不动时转 .lc-scale 容器内滚动，内容永远可达）;
 *  探测失败（needW / needH 仍为 0）→ 回落兜底基准宽（等价第 70 批兜底，空产物 / 异常环境不崩）。 */
const scale = computed(() => {
  const vw = viewportWidth.value
  // 宽轴极限:未测到（0）时取兜底基准宽
  const limitW = needW.value > 0 ? needW.value : FALLBACK_BASE_WIDTH
  const s = vw < limitW ? vw / limitW : 1
  // 第 73 批（修复「对话后整页等比缩小」）:高度轴不再参与缩放系数 ——
  //   原实现把「内容固有高 needH（只增不减）」当分母，对话消息越堆越高 → 系数越算越小 → 整页被压成一小条；
  //   现口径:缩放只由「视口可用宽 vs 内容固有宽」决定，缩到贴合即停（宽窗系数恒为 1，零回归）；
  //   内容高度超出视口时，由 .lc-scale（fixed + overflow:auto）/ .lc-frame（overflow:auto）转「内部滚动」，内容永远可达。
  return Math.max(Math.min(s, 1), MIN_SCALE)
})

/** 缩放样式:系数 === 1 时返回 undefined（不写任何行内样式，宽窗零回归）;
 *  否则给 transform:scale + 反补宽高 + 脱离文档流的 fixed 定位 ——
 *  反补保证铺满（渲染宽 = 占位宽 × 系数 = 视口宽），fixed + overflow:auto 保证不溢出、内容可达。 */
const scaleStyle = computed<CSSProperties | undefined>(() => {
  const s = scale.value
  if (s === 1) return undefined
  return {
    position: 'fixed',
    top: '0',
    left: '0',
    transformOrigin: '0 0',
    transform: `scale(${s})`,
    width: `${100 / s}%`,
    height: `${100 / s}%`,
    overflow: 'auto',
  }
})
</script>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
}

/* 第 70 批（方案 A · 实测修正）:产物视口缩放的容器（与根组件里的 .lc-scale 一一对应）——
 *  默认铺满视口（系数 === 1 的宽窗环境下不写任何行内样式，走本规则，零回归）;
 *  窗口窄于基准宽时，行内 :style 改走 position:fixed + transform:scale + 反补宽高（(100 / 系数)%），
 *  此时本规则被行内覆盖，只作为「行内未命中」时的基础铺满链存在，不必再改。
 *  高度链:.lc-scale 是 #app 的直接子元素，#app 已是 height:100%，因此这里写 100% 即可;
 *  overflow 只在窄窗行内给（fixed 容器自身内滚，保证内容永远可达）—— 宽窗时本层不得加
 *  overflow:auto，否则会把整页内容锁进内滚层（与第 67 批 P6 同一道坎）。 */
.lc-scale {
  width: 100%;
  height: 100%;
}
/* 第 69 批（A）:按钮通用按下反馈 —— 产物内所有 button 开箱即有 hover / active（无需配置） */
#app button {
  cursor: pointer;
  transition: filter 0.12s ease;
}
/* 排除导航高亮按钮:高亮态由下方方案 B 承载，避免两条 filter 互相覆盖 */
#app button:not(:disabled):not([class*="lc-nav-active"]):hover {
  filter: brightness(0.96);
}
#app button:not(:disabled):not([class*="lc-nav-active"]):active {
  filter: brightness(0.9);
}

/* 第 69 批（B）:导航「当前页」高亮 —— 形态由出码侧静态择一（core/theme.ts 唯一判定） */
#app .lc-nav-active {
  background-color: #ecf2ff;
  color: var(--primary);
}
#app .lc-nav-active-dim {
  filter: brightness(0.9);
}
#app .lc-nav-active-bright {
  filter: brightness(1.18);
}
/* 第 72 批:滚动条轻量化（去箭头 + 8px 细条 + 圆角 + 悬停加深）——
 *  一处规则修全产物（文档级 + 元素级滚动条一网打尽）;
 *  常量取自 core/defaults.ts 配置中心，此处只插值、不硬编码（C9 单一数据源）。 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
/* 取消上下两端箭头按钮（用户核心诉求）——宽高归零 + display:none 双保险 */
::-webkit-scrollbar-button {
  display: none;
  width: 0;
  height: 0;
}
::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.18);
  border-radius: 4px;
  border: 2px solid transparent;
  background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.32);
}
/* 轨道 / 转角透明 —— 去掉那条「长灰带」，观感简洁 */
::-webkit-scrollbar-track,
::-webkit-scrollbar-corner {
  background: transparent;
}
body {
  background-color: #f2f3f5;
}
.lc-frame {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 100%;
  height: 100%;
  overflow: auto;
  margin: 0 auto;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
/* 悬浮窗模式:仅归零内边距（保留圆角/阴影/白底外观）—— 仅 ?mode=float 命中，主窗零影响 */
.lc-frame.lc-frame-float {
  padding: 0;
}
#app .lc-frame > :first-child {
  flex: 1;
  min-height: 0;
  height: 100%;
}
/* 第 68 批:全链一把尺 · 页面根盒子（含子页嵌套层）—— 与首页同一条尺 */
#app .box-div-8ouzx,
#app .box-div-nbrvi,
#app .box-div-q7ahd,
#app .box-div-7uzrx,
#app .box-div-u3i2k,
#app .box-div-k4i3m,
#app .box-div-y3bin,
#app .box-div-605ld,
#app .box-div-6hjel,
#app .box-div-u6w0e,
#app .box-div-2jblc,
#app .box-div-9d0z0,
#app .box-div-w1p0i,
#app .box-div-i2abp,
#app .box-div-jbx6e,
#app .box-div-m2ub7,
#app .box-div-37fh7,
#app .box-div-mxi8c,
#app .box-div-lb5y8,
#app .box-div-iuj5a,
#app .box-div-yfq54,
#app .box-div-0iorg,
#app .box-div-2ut7h,
#app .box-div-vjfg5,
#app .box-div-nqpe4,
#app .box-div-xgnk3,
#app .box-div-kv2jk,
#app .box-div-gtt7h,
#app .box-div-zvafx,
#app .box-div-spooa,
#app .box-div-xtkpb,
#app .box-div-4ct2h,
#app .box-div-rz7cb,
#app .box-div-crmav {
  flex: 1;
  min-height: 0;
  height: 100%;
}
/* 第 68 批:全链一把尺 · 内容出口盒子 —— 把剩余高度让给 slot 里的下一层 */
#app .box-div-35526,
#app .box-div-zutir,
#app .box-div-qe0xj,
#app .box-div-xvg97,
#app .box-div-gvzko,
#app .box-div-x74l9 {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

/* 阶段5-1:任务卡总列表（/1 底部 + 次级观察窗顶部共用；非 scoped → 一处改 9 页共用） */
#app .box-div-tasklist {
  margin-top: 12px;
  padding: 12px;
  background-color: #ffffff;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
#app .box-div-tasklist-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  margin-bottom: 8px;
}
#app .box-div-taskcard {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-bottom: 1px solid #f0f1f3;
  font-size: 13px;
  color: #1f2329;
}
#app .box-div-taskcard:last-child {
  border-bottom: none;
}
#app .task-id {
  font-family: Consolas, Monaco, monospace;
  color: var(--primary);
  font-weight: 600;
}
/* 6 态色标:待派发 / 开发中 / 待审查 / 审查中 / 待裁决 / 已闭环 */
#app .task-state {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  background-color: #f2f3f5;
  color: #4e5969;
}
#app .task-state.st-0 {
  background-color: #f2f3f5;
  color: #4e5969;
}
#app .task-state.st-1 {
  background-color: #e8f3ff;
  color: var(--primary);
}
#app .task-state.st-2 {
  background-color: #fff7e8;
  color: #d25f00;
}
#app .task-state.st-3 {
  background-color: #f5e8ff;
  color: #7d3cff;
}
#app .task-state.st-4 {
  background-color: #ffece8;
  color: #d4380d;
}
#app .task-state.st-5 {
  background-color: #e8ffea;
  color: #00a854;
}
#app .task-rework {
  font-size: 12px;
  color: #d25f00;
}
#app .btn-task-abort {
  margin-left: auto;
  padding: 2px 10px;
  font-size: 12px;
  color: #d4380d;
  background-color: #ffffff;
  border: 1px solid #ffccc7;
  border-radius: 4px;
}
/* 次级对话页消息正文:长不可断 token（长路径/长函数名/长URL）在气泡内换行，
   避免撑大 App.vue measureContent 的 min-content 固有宽 → 触发整页等比缩小。
   4 个类名为 8 个次级对话页（/1、/1-2 ~ /7-2）共用的消息正文 span；
   全局一处改，8 页全部生效（不侵入各页 scoped 样式）。 */
#app .box-span-qexcn,
#app .box-span-3jrmj,
#app .box-span-8pxmq,
#app .box-span-7ak7e {
  word-break: break-word;
  overflow-wrap: anywhere;
}
</style>
