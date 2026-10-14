<!--
  页面《1》　路由:/1（1）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-nbrvi">
    <div class="box-div-kwru5">
      <div class="box-div-s0rn6">
        <span class="box-span-45g0b"></span>
        <span class="box-span-8d74b">次级对话</span>
        <button class="box-button-bk35h" type="button" @click="goPage1()" :class="{ 'lc-nav-active': route.path === '/1' }">模型2</button>
        <button class="box-button-ehg1m" type="button" @click="goPage12()" :class="{ 'lc-nav-active': route.path === '/1-2' }">模型3</button>
        <button class="box-button-2ke2s" type="button" @click="goPage22()" :class="{ 'lc-nav-active': route.path === '/2-2' }">模型4</button>
        <button class="box-button-jy07j" type="button" @click="goPage32()" :class="{ 'lc-nav-active': route.path === '/3-2' }">模型5</button>
        <button class="box-button-92cbv" type="button" @click="goPage42()" :class="{ 'lc-nav-active': route.path === '/4-2' }">模型6</button>
        <button class="box-button-3yza8" type="button" @click="goPage52()" :class="{ 'lc-nav-active': route.path === '/5-2' }">模型7</button>
        <button class="box-button-u5t27" type="button" @click="goPage62()" :class="{ 'lc-nav-active': route.path === '/6-2' }">模型8</button>
        <button class="box-button-1m6p4" type="button" @click="goPage72()" :class="{ 'lc-nav-active': route.path === '/7-2' }">模型9</button>
      </div>
      <div class="box-div-zutir">
        <div class="box-div-u5vtw">
          <div class="box-div-8vbro">
            <div class="box-div-jieyo">
              <span class="box-span-curproj">当前项目:{{ curProjectName }}</span>
              <span class="box-span-role">{{ secRoleLabel }}</span>
            </div>
            <div class="box-div-qty03">
              <span class="box-span-iklzd">AI思考模式</span>
              <!-- 【阶段5-2·T1】点击改走 toggleThinkMode():
                   原内联取反写法只改本地 ref，刷新/重启工作台必回默认 true（无持久化）。
                   新函数 = 本地取反（即时响应）+ 异步 POST /api/config/set 落盘（与主对话页共用 show_think_mode 字段）。 -->
              <div class="box-div-r9cdx" :class="{ 'switch-off': !thinkEnabled }" @click="toggleThinkMode()">
                <div class="box-div-8274x"></div>
              </div>
            </div>
          </div>
          <!-- 【显示优化】加 ref 供 scrollToBottom() 拿到滚动容器 DOM，实现新内容自动滚到底部 -->
          <div class="box-div-6e3mh" ref="msgListRef">
            <!-- 阶段5-1（V1 主线口径）:该次级会话真实消息流（@派发 / @回报） -->
            <template v-for="(m, i) in visibleMessages" :key="i">
              <!-- 主控派发（主控→次级）:主控机器人图标在右侧；气泡可折叠。
                   结构对齐主对话页:折叠态挂「内容容器 div」，按钮容器与内容容器同级
                   （按钮永远在气泡外侧下方，折叠时不位移、不钻进气泡） -->
              <div v-if="m.type === 'dispatch'" class="box-div-pgdps">
                <img class="box-img-mainctl" src="/assets/icons/logo.png" alt="主控" />
                <div class="box-div-w2py2" :class="{ 'msg-folded': m.collapsed }">
                  <span class="box-span-3jrmj">{{ m.content }}</span>
                </div>
                <div class="box-div-msgact">
                  <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                  <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                </div>
              </div>
              <!-- AI 正文（含工具调用指令块）:与主对话页口径完全一致；气泡可折叠。
                   结构对齐:折叠态挂「内容容器 div」，按钮容器与内容容器同级 -->
              <div v-else-if="m.type === 'ai'" class="box-div-q87ne">
                <!-- 【头像接入】原「AI」文字徽标 → 本页槽位头像（圆形透明底 PNG，CSS 已同步去蓝底） -->
                <img class="box-span-4x3up" :src="secAvatarUrl" alt="AI" />
                <div class="box-div-kdism" :class="{ 'msg-folded': m.collapsed }">
                  <span class="box-span-qexcn">{{ m.content }}</span>
                </div>
                <div class="box-div-msgact">
                  <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                  <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                </div>
              </div>
              <!-- 次级回报（次级→主控）:次级模型蓝色 AI 图标在左侧；气泡可折叠。
                   结构对齐:折叠态挂「内容容器 div」，按钮容器与内容容器同级 -->
              <div v-else-if="m.type === 'report'" class="box-div-q87ne">
                <!-- 【头像接入】原「AI」文字徽标 → 本页槽位头像（圆形透明底 PNG） -->
                <img class="box-span-4x3up" :src="secAvatarUrl" alt="AI" />
                <div class="box-div-kdism" :class="{ 'msg-folded': m.collapsed }">
                  <span class="box-span-qexcn">{{ m.content }}</span>
                </div>
                <div class="box-div-msgact">
                  <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                  <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                </div>
              </div>
              <!-- 次级模型思考过程:折叠气泡（结构对齐主对话页 think 气泡:头部行固定 + 内容区 v-show） -->
              <div v-else-if="m.type === 'think'" class="box-div-q87ne">
                <!-- 【头像接入】原「AI」文字徽标 → 本页槽位头像（圆形透明底 PNG） -->
                <img class="box-span-4x3up" :src="secAvatarUrl" alt="AI" />
                <div class="box-div-kdism">
                  <div class="box-div-sec-think">
                    <span class="box-span-sec-think">AI思考过程</span>
                    <button class="box-button-msgact" type="button" @click="toggleThink(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                    <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                  </div>
                  <div v-show="!m.collapsed">
                    <span class="box-span-qexcn">{{ m.content }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="box-div-moxfw">
                <span class="box-span-kbzfw">{{ m.role || 'AI' }}</span>
                <div class="box-div-y8bio" :class="{ 'msg-folded': m.collapsed }">
                  <span class="box-span-7ak7e">{{ m.content }}</span>
                </div>
                <div class="box-div-msgact">
                  <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                  <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                </div>
              </div>
            </template>
            <div v-if="!visibleMessages.length" class="box-div-q87ne">
              <!-- 【头像接入】空态同样显示本页槽位头像，与消息气泡视觉一致 -->
              <img class="box-span-4x3up" :src="secAvatarUrl" alt="AI" />
              <div class="box-div-kdism">
                <span class="box-span-qexcn">（等待主控派发任务……）</span>
              </div>
            </div>
          </div>
          <div class="box-div-hftze">
            <div class="box-div-npqfl">
              <div class="box-div-j4npf" :class="{ 'energy-active': taskActive }">
                <div class="box-div-321ft"></div>
                <div class="box-div-zta3r"></div>
                <div class="box-div-m9zq2"></div>
                <div class="box-div-lcd6v"></div>
                <div class="box-div-gp30n"></div>
                <div class="box-div-ecduj"></div>
                <div class="box-div-ot9di"></div>
                <div class="box-div-enhcf"></div>
                <div class="box-div-wqk1p"></div>
              </div>
            </div>
            <!-- 阶段5-1（V1 主线口径）:次级页无输入框 —— 任务由主模型 @ 派发触发 -->
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 阶段5-1（V1 主线口径）:任务卡已融入消息流，不再使用独立底部块 -->
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
/* 阶段5-1（V1 主线口径）:任务卡已融入消息流，listTasks / abortTask / TaskListItem 均已不再需要 */

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

/** 方案A:本页绑定的次级槽位（开发=2）；复刻到其他次级页仅需改此值 */
const SEC_SLOT = 6
/** 【头像接入】本页次级模型头像:按 SEC_SLOT 直取 /assets/avatars/model_{slot}.png。
 *  与主对话页 PageO0x2f.vue 的 senderIcon() 路径口径完全一致（slot 2~9 → model_{slot}.png），
 *  各次级页随自身 SEC_SLOT 自动对应，本行无需再改。 */
const secAvatarUrl = `/assets/avatars/model_${SEC_SLOT}.png`
/** 顶部角色名（"开发 · 模型名"），从 /api/orch/roles 按 SEC_SLOT 取 */
const secRoleLabel = ref<string>('开发 · 加载中…')
/** 拉取本页角色名（按 SEC_SLOT 从角色池匹配 persona_name + model_name） */
async function loadSecRoleLabel() {
  try {
    const res = await fetch('/api/orch/roles')
    const j = await res.json()
    const brief = j && j.data ? j.data : null
    const pool = brief && Array.isArray(brief.data) ? brief.data : []
    const hit = pool.find((it: any) => Number(it.slot) === SEC_SLOT)
    if (hit) {
      const pname = String(hit.persona_name || hit.name || '次级').trim()
      const mname = String(hit.model_name || hit.model || hit.model_id || '').trim()
      secRoleLabel.value = mname ? `${pname} · ${mname}` : pname
    } else {
      secRoleLabel.value = '该页面尚未配置角色槽位'
    }
  } catch {
    secRoleLabel.value = '开发 · 加载中…'
  }
}

/** 阶段5-1（V1 主线口径）:该次级会话真实消息流（@派发 / @回报 / AI真思考 / AI正文）
 *  与主对话页完全同口径:think=真思考（reasoning_content）、ai=正文（含工具调用指令块）；
 *  唯一差别:本页无用户输入框（次级窗口 = 用户与模型的完整聊天，只读）。 */
interface SecMsg {
  type: 'dispatch' | 'report' | 'plain' | 'think' | 'ai'
  role?: string
  content: string
  collapsed?: boolean
  /** 【显示优化】用户是否手动开合过该气泡:一旦为 true，updateFoldStates() 的自动折叠规则永久跳过它，
   *  保证「用户手动展开的优先级 > 自动折叠」，避免用户正在查看时被自动折叠。
   *  mergeSecMessages 增量补齐时以"页面对象"为基准复用原引用，本标记天然继承、无需额外迁移（仅前端内存字段，不落盘）*/
  userTouched?: boolean
}
const messages = ref<SecMsg[]>([])
/** 【显示优化】消息流滚动容器 DOM 引用（模板 .box-div-6e3mh）——用于自动滚动到底部 */
const msgListRef = ref<HTMLElement | null>(null)
/** 【显示优化】智能折叠:记录上一条消息条数，仅在「新增气泡」时同步折叠态，避免每帧重排 */
let lastMsgCount = 0
/** 【显示优化】自动滚动到底部:
 *  · force = false（默认）:仅当用户"已在底部附近"时才跟随滚动——用户正在向上翻阅历史时不打断阅读；
 *  · force = true:无条件滚到底部，用于"首屏历史加载完 / 新一轮派发 / 回读补齐"等确定要看的时刻。*/
function scrollToBottom(force = false) {
  nextTick(() => {
    const el = msgListRef.value
    if (!el) return
    if (!force) {
      // 距底部 80px 以内视为"正在跟读"，此时才自动跟随；已上翻则不动
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
      if (!nearBottom) return
    }
    el.scrollTop = el.scrollHeight
  })
}

/** AI思考模式开关:默认开启，关闭时隐藏所有 think 气泡（AI 正文不受影响）。
 *  【思考开关·独立持久化】值存储于后端 config.json 的 show_think_mode_dev 字段
 *  （次级开发页专属）—— 与主对话页 show_think_mode、悬浮窗 show_think_mode_float
 *  三者互不同步、互不覆盖；本页可独立开关，刷新 / 重启工作台均保持自己的状态。 */
const thinkEnabled = ref<boolean>(true)

/** 实际渲染的消息列表:思考模式关闭时只过滤 think（AI 正文属于对话内容，必须保留，与主对话页口径一致） */
const visibleMessages = computed<SecMsg[]>(() =>
  thinkEnabled.value ? messages.value : messages.value.filter((m) => m.type !== 'think'),
)

/** 【阶段5-2】读取后端持久化的思考开关状态（复用 GET /api/config/get，不新建接口）:
 *  兼容两种返回形态（{code,data:{config:{...}}} 与 {code,data:{...}}）；
 *  非 boolean 一律保持默认 true（老配置缺失无感，与 api_server.py load_config 的默认值兜底一致）。 */
async function loadThinkMode() {
  try {
    const res = await fetch('/api/config/get')
    const data = await res.json()
    const cfg = data?.data?.config ?? data?.data ?? {}
    // 【思考开关·独立持久化】读取本页专属字段 show_think_mode_dev（不读主对话页/悬浮窗的字段）
    if (typeof cfg.show_think_mode_dev === 'boolean') thinkEnabled.value = cfg.show_think_mode_dev
  } catch (e) {
    console.warn('[thinkMode] 读取持久化状态失败，保持默认开启:', e)
  }
}

/** 【思考开关·独立持久化】点击开关:先本地取反（即时响应，不等网络），再异步落盘。
 *  本页写入 show_think_mode_dev（次级开发页专属），与主对话页 show_think_mode、
 *  悬浮窗 show_think_mode_float 三字段互相独立，各自刷新 / 重启后保持自己的状态。 */
async function toggleThinkMode() {
  thinkEnabled.value = !thinkEnabled.value
  try {
    await fetch('/api/config/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // 【思考开关·独立持久化】只写本页专属字段 show_think_mode_dev（1 个字段）:
      //  后端 /api/config/set 为深合并语义（load_config → old_config.update(request.config) → save_config），
      //  不会覆盖用户 config.json 其余 40+ 项配置。
      body: JSON.stringify({ config: { show_think_mode_dev: thinkEnabled.value } }),
    })
  } catch (e) {
    console.warn('[thinkMode] 保存状态失败（本地已生效，下次刷新可能回退）:', e)
  }
}

/** 能量条工作状态:主控 @次级唤醒（dispatch）→亮；内容进入记忆文件（memory_saved）/异常（error）→灭 */
const taskActive = ref<boolean>(false)

/** 顶部展示的当前项目名:跟随主窗/悬浮窗（localStorage['current_selected_project']） */
const curProjectName = ref<string>('（全局）')

/** 从 localStorage 同步当前项目名到顶部展示（兼容 JSON 对象与纯文本两种存储格式） */
function syncProjectFromStorage() {
  try {
    const sp = localStorage.getItem('current_selected_project')
    if (!sp) { curProjectName.value = '（全局）'; return }
    try {
      const obj = JSON.parse(sp)
      // 【修复·顶部口径统一】写入端在选「（全局）」时兜底写的是 { project_name:'default' } 对象串，
      //  原实现直接取 project_name → 顶部会显示 "default"，与下拉框「（全局）」显示不一致；
      //  这里统一归一化:空值或 'default' 一律显示「（全局）」，具体项目名原样显示。
      //  注意:仅影响"顶部展示"，不改变 localStorage 存储值，因此次级缓存键 chat_secondary_default 不受影响。
      const nm = (obj && obj.project_name) || ''
      curProjectName.value = (!nm || nm === 'default') ? '（全局）' : nm
    } catch {
      curProjectName.value = sp
    }
  } catch {}
}

/** 跨窗口项目同步:主窗/悬浮窗切换项目时写入 localStorage，本页收到 storage 事件后跟随
 *  项目切换 = 整套对话切换:清空当前消息后按新项目重载（缓存键与后端过滤均带项目名，互不混杂） */
function onStorageChange(e: StorageEvent) {
  if (e.key !== 'current_selected_project') return
  syncProjectFromStorage()
  // 【方案C·完整根治·跨项目串台】切项目 = 整套对话 + 整套通信通道切换:
  //   原实现只清 messages 后重读历史，但 SSE 仍挂在旧项目的通道上 —
  //   进一步说，旧通道残留的 sec_snapshot / 旧轮的流式事件会被本页照收 → 串台。
  //   现改为:① 先关旧 SSE（断开旧项目通道）；② 清空 messages；③ 用新项目名重连 SSE；
  //           ④ 再重读历史（镜像 / 回退接口均按新项目名走）。
  //   切换瞬间会有一瞬空白（SSE 建连 + 首屏回读），但彻底消除"旧项目内容停留在新项目页"。
  if (es) {
    try { es.close() } catch {}
    es = null
  }
  messages.value = []
  connectSSE()
  loadSecMessages()
}

/** 折叠/展开次级模型的思考过程气泡（保留原名，仅 think 场景使用） */
function toggleThink(m: SecMsg) {
  m.collapsed = !m.collapsed
  // 【显示优化】打"用户手动开合过"标记 → updateFoldStates() 此后永久跳过它
  m.userTouched = true
}

/** 折叠/展开任意气泡（dispatch / ai / report / plain 通用，对齐主对话页 toggleFold） */
function toggleFold(m: SecMsg) {
  m.collapsed = !m.collapsed
  // 【显示优化】打"用户手动开合过"标记 → updateFoldStates() 此后永久跳过它
  m.userTouched = true
}

/** 智能折叠:历史消息折叠、最新一条展开（对齐主对话页 updateFoldStates 口径）。
 *  唯一调用点:SSE「dispatch 到达」（=new 用户消息）分支 —— 绝不因历史回读/定时刷新触发；
 *  用户点击的折叠状态只由用户自己改变，这是"点击折叠不再被重置"的根治口径。 */
function updateFoldStates() {
  const list = messages.value
  if (list.length === 0) return
  list.forEach((m, i) => {
    // 【显示优化】用户手动开合过的气泡永久跳过自动规则（手动优先级 > 自动折叠）:
    //  原实现是无条件覆盖，只能靠"只在 dispatch 时调用本函数"来规避"用户点击被重置"；
    //  有了本行保护后，可放心把触发条件放宽到"任意新增气泡"（think / ai / report 都会触发）。
    if (m.userTouched) return
    m.collapsed = i !== list.length - 1
  })
}

/** 本轮 think / ai 气泡引用（各仅一条），避免"思考/正文交替到达"被切成多气泡；由 dispatch 事件触发重置 */
let roundThinkMsg: SecMsg | null = null
let roundAiMsg: SecMsg | null = null

/** 本轮是否已收到过流式正文（ai_output_stream）——收尾 report 去重的权威标记。
 *  为什么不用 roundAiMsg 引用判重:roundAiMsg 是 messages.value 数组里的对象引用，
 *  一旦 mergeSecMessages / loadSecMessages 用新数组整体替换 messages.value，
 *  该引用就不在新数组里（messages.value.includes(roundAiMsg)===false），
 *  判重随之失效 → 收尾 report 整段被再贴一遍 →
 *  用户看到"一条 AI 头像气泡 + 一条回报头像气泡、内容相同"的重复。
 *  用布尔标记与数组替换、对象引用完全解耦，任何路径下判重都稳定。 */
let streamedThisTurn = false

/** 【回放期标记·新增】SSE 建连回放进行中:收到 sec_replay_begin → true，收到 sec_replay_end → false。
 *  用途:回放期间「本轮内容」由后端回放事件流逐条铺出，是此刻唯一真源；
 *  此时必须阻止 mergeSecMessages 的「以 fresh 为权威整体重建」把刚回放的流式气泡顶掉
 *  （否则用户会看到回放/流式出来的正文被旧落盘内容覆盖 → 内容闪退、冻住不动）。 */
let replaying = false

/** 【方案B·根因修复】本地已持有完整本轮快照的标记:
 *  由 loadSecMessages 在「localStorage 读到非空」或「后端事件粒度镜像读到非空」时置 true。
 *  切回本页时该标记为 true，意味着页面上已有完整本轮内容 —— 此时 SSE 建连回放只需保证
 *  "内容不丢"（本地已具备），无需再经历"裁气泡 + 逐字重播"的秒级空白。 */
let localSnapshotReady = false

/** 【方案B·根因修复】跳过回放重建标记:
 *  sec_replay_begin 到达时，若判定本地已完整（见下方分支），则置 true 且"不裁气泡"；
 *  后续回放事件在 onmessage 头部被静默丢弃，直到 sec_replay_end 复位。
 *  作用:切回延时从秒级（逐字重播）降到零（本地一铺到位），且绝不丢内容（本地已是完整快照）。 */
let skipReplay = false

/** 【根因级新增】从 messages.value 末尾往前查找"本轮"指定类型的气泡（think / ai）。
 *  为什么不再用 roundThinkMsg / roundAiMsg 对象引用:
 *  这两个指针指向的是 messages.value 里的某个对象，而 messages.value 存在 3 处整体替换
 *  （草稿恢复 / loadSecMessages 回读 / mergeSecMessages 合并）——一旦替换，
 *  指针指向的对象就不在新数组里（messages.value.includes(ptr)===false），
 *  后续所有增量都会写到"已不在渲染数组里的幽灵对象"上 →
 *  用户停在页面上看到内容"冻住不动"，切页回读才"一次蹦出来"（即用户描述的"更新到夹层里"）。
 *  改为每次从当前数组末尾查找，就与数组替换、对象引用完全解耦，任何路径下都稳定。
 *  查找边界:遇到 dispatch（新一轮派发的起点）即停止，绝不误取上一轮的气泡。 */
function _findRoundMsg(t: string): SecMsg | null {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i]
    if (!m) continue
    if (m.type === 'dispatch') return null
    if (m.type === t) return m
  }
  return null
}

/** 思考内容增量追加:同一轮内续写当前 think 气泡（无则新开），落地口径与主对话页 appendThink 100% 一致。
 *  【对齐主对话页·根治分气泡】不再用 _findRoundMsg('think') 从数组末尾倒查（倒查遇 dispatch 才停，
 *  而一轮任务只有一个 dispatch → 多轮思考全部倒查到同一条，视觉上"思考合并成一坨"）。
 *  改为直接依赖 roundThinkMsg 指针（与主对话页 appendThink 逐行同款）:
 *    · 指针有效（且对象仍在新数组里）→ 续写当前 think 气泡;
 *    · 指针已置空（终态事件 ai_output 已置空）或对象已被数组整体替换 → push 新气泡并重置指针。
 *  分轮的权威机制 = SSE 终态事件 ai_output 置空指针（主对话页同款），而非倒查。 */
function appendThink(text: string) {
  if (!text) return
  if (roundThinkMsg && messages.value.includes(roundThinkMsg)) {
    roundThinkMsg.content = String(roundThinkMsg.content || '') + text
  } else {
    messages.value.push({ type: 'think', content: text, collapsed: false })
    roundThinkMsg = messages.value[messages.value.length - 1]
  }
}

/** AI 正文流式追加:兼容"增量 delta"与"累积 full"两种后端口径，落地口径与主对话页 appendAiOutput 100% 一致。
 *  【对齐主对话页·根治分气泡】不再用 _findRoundMsg('ai') 从数组末尾倒查（倒查遇 dispatch 才停，
 *  而一轮任务只有一个 dispatch → 多轮 AI 正文全部倒查到同一条，这就是"AI 内容 + 工具结果 塞进一个气泡"的根因）。
 *  改为直接依赖 roundAiMsg 指针（与主对话页 appendAiOutput 逐行同款）:
 *    · 指针有效（且对象仍在新数组里）→ 续写当前 ai 气泡;
 *    · 指针已置空（终态事件 ai_output 已置空）或对象已被数组整体替换 → push 新气泡并重置指针。
 *  分轮的权威机制 = 后端每轮 AI 正文收尾补推 ai_output 终态事件 → 前端置空指针 → 下一轮流式自然落新气泡。
 *  streamedThisTurn 在此置位（对齐主对话页 appendAiOutput 内置位口径），供收尾 report 判重使用（幂等）。 */
function appendAiOutput(text: string) {
  if (!text) return
  streamedThisTurn = true
  const last = (roundAiMsg && messages.value.includes(roundAiMsg)) ? roundAiMsg : null
  if (last) {
    const cur = String(last.content || '')
    if (text.length >= cur.length && text.startsWith(cur)) last.content = text
    else last.content = cur + text
  } else {
    messages.value.push({ type: 'ai', content: text })
    roundAiMsg = messages.value[messages.value.length - 1]
  }
}

/** ===== 帧节流（对齐主对话页 PageO0x2f.vue flushDomUpdates 口径） =====
 *  SSE 逐 delta 高频到达时，不直接改数据，先入缓冲，rAF 每帧只提交一次，
 *  大幅减少 DOM 重排抖动，获得与主对话页一致的"平滑逐字"观感。 */
let pendingThink = ''
let pendingStream = ''
let domUpdateScheduled = false
let rafId = 0

/** 帧节流刷新:把缓冲的思考/正文增量每帧一次性提交 */
function flushDomUpdates() {
  domUpdateScheduled = false
  rafId = 0
  if (pendingThink) { appendThink(pendingThink); pendingThink = '' }
  if (pendingStream) { appendAiOutput(pendingStream); pendingStream = '' }
}

/** 调度一次帧刷新:rAF 一帧内只跑一次（无 rAF 环境退化为 setTimeout 16ms） */
function scheduleFlush() {
  if (domUpdateScheduled) return
  domUpdateScheduled = true
  if (typeof requestAnimationFrame === 'function') {
    rafId = requestAnimationFrame(() => flushDomUpdates())
  } else {
    rafId = setTimeout(() => flushDomUpdates(), 16) as any
  }
}

/** 复制文本到剪贴板（对齐主对话页 handleCopyText:clipboard 优先，execCommand 兜底，全环境兼容） */
function handleCopyText(text: string) {
  if (!text) return
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
      return
    }
  } catch {}
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  } catch {}
}
/** ===== 方案A:次级对话消息持久化（与主窗完全隔离:localStorage 键前缀 + 后端文件名前缀 secondary_）===== */
const SEC_PERSIST_PREFIX = 'secondary_'

/** 获取当前项目名（与主窗 currentProjectName() 口径一致:解析 localStorage['current_selected_project']） */
function secProjectName(): string {
  try {
    const sp = localStorage.getItem('current_selected_project')
    if (!sp) return 'default'
    try {
      const obj = JSON.parse(sp)
      return (obj && obj.project_name) || 'default'
    } catch { return sp || 'default' }
  } catch { return 'default' }
}
/** 次级对话缓存键:chat_secondary_{槽位}_{项目}（与主窗 chat_{项目} 键空间隔离；含槽位维度，8 个次级页互不共用同一键） */
function secCacheKey(): string {
  return 'chat_' + SEC_PERSIST_PREFIX + SEC_SLOT + '_' + secProjectName()
}

let secPersistTimer: any = null
/** 落盘（localStorage + 后端，与 origin/端口解耦）；fire-and-forget，失败静默。
 *
 *  【方案A-3·口径锁定】本函数只负责"写"，永不参与"读":
 *    · localStorage 键 `chat_secondary_{项目}` —— 仅作"首屏防白屏占位"，不是真源；
 *    · 后端 `sessions/chat_secondary_{项目}.json`（POST /api/chat/history/save）—— 仅作备份镜像，永不回读；
 *    · 次级页读的唯一真源 = `/api/orch/secondary_history`
 *      （对应后端 orchestrator 落盘的 `latest_secondary_history_{项目}_开发.json`）。
 *  目的:切页 N 次后，前端都不会从"可能被污染的本地镜像"回灌旧副本。
 */
function persistSecMessages() {
  if (secPersistTimer) { clearTimeout(secPersistTimer); secPersistTimer = null }
  const data = messages.value
  try { localStorage.setItem(secCacheKey(), JSON.stringify(data)) } catch {}
  try {
    fetch('/api/chat/history/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: SEC_PERSIST_PREFIX + SEC_SLOT + '_' + secProjectName(), messages: data }),
    }).catch(() => {})
  } catch {}
}

/** ===== 方案A-1/A-4:判重归一化 + 本轮定位（三个纯函数，只用于判重，绝不改动任何展示内容） =====
 *
 *  问题背景:同一轮内容存在两种口径:
 *    · 页面实时/回放 = 事件粒度 + 含「工具调用块」原文（dispatch/think/ai 多条交替）；
 *    · 后端落盘真源 = 轮粒度 + 「工具执行结果」已剥离（user 条 header || body）。
 *  两种口径做裸串对比（相等 / 互为前缀）永远判不出同一条 → 每次回读都追加一份 → 重复累积。
 *  解法:把两种口径都归一化为「指纹」（剥外壳前缀 → 剥工具块 → 丢工具结果行 → 去 markdown/空白/大小写），
 *        对指纹做等价判定，从而把"同一段正文的两种口径"识别为同一条。
 */
function normSecText(s: string): string {
  let t = String(s || '')
  // ① 统一换行
  t = t.replace(/\r\n?/g, '\n')
  // ② 剥历史回读外壳前缀（行首"用户问:…/回答:…/系统派发:…/系统回报:…"）
  t = t.replace(/^[ \t]*(用户问|回答|系统派发|系统回报|派发|回报)[ \t]*[::][ \t]*/gm, '')
  // ③ 剥「工具调用块」起止标记及其中的内容（含未闭合的残缺块）。
  //    注意:标记字面量一律用字符串拼接构造 —— 避免源码里出现与工具调用块同名的字面量
  //    （本文件既有约定:同名文字面量会干扰编辑/解析链路，故一律拼接）。
  {
    const TK_BEGIN = '【工具调用' + '开始】'
    const TK_END = '【工具调用' + '结束】'
    const pieces: string[] = []
    let rest = t
    while (rest) {
      const b = rest.indexOf(TK_BEGIN)
      if (b < 0) { pieces.push(rest); break }
      pieces.push(rest.slice(0, b))
      const e = rest.indexOf(TK_END, b + TK_BEGIN.length)
      if (e < 0) { rest = ''; break }
      rest = rest.slice(e + TK_END.length)
    }
    t = pieces.join('')
  }
  // ④ 逐行丢掉「工具执行结果:」及其缩进续行（与后端 strip_tool_result_blocks 同口径）
  {
    const lines = t.split('\n')
    const keptLines: string[] = []
    let dropping = false
    for (const line of lines) {
      if (/^[ \t]*工具执行结果[ \t]*[::]/.test(line)) { dropping = true; continue }
      if (dropping) {
        if (/^[ \t]+\S/.test(line) || /^[ \t]*$/.test(line)) continue
        dropping = false
      }
      keptLines.push(line)
    }
    t = keptLines.join('\n')
  }
  // ⑤ 去 markdown 标记 + 所有空白 + 统一小写（只作用于比较指纹，不改任何展示内容）
  t = t.replace(/[#*`>\-\s]/g, '').toLowerCase()
  return t
}

/** 展示净化（方案C·前端兜底）:剥离历史回读串里的「工具执行结果:…」段，只保留 AI 正文
 *  与后端 orchestrator.strip_tool_result_blocks 同源逻辑:
 *  - 命中「工具执行结果:」的行 → 进入丢弃态，该行与后续"带缩进"的续行一并丢弃；
 *  - 遇到"非缩进且非空"的行 → 视为下一段 AI 正文，退出丢弃态并保留该行；
 *  - 目的:即便后端漏切，前端也不把「工具执行结果:…」铺上屏
 *    （口径:拼接内容只进记忆文件，前端也不应该有接口去接这个内容）。 */
function stripToolResultForDisplay(text: string): string {
  const t = String(text || '')
  if (!t || !t.includes('工具执行结果:')) return t
  const kept: string[] = []
  let dropping = false
  for (const line of t.split('\n')) {
    if (line.trim().startsWith('工具执行结果:')) { dropping = true; continue }
    if (dropping) {
      if (line.trim() && !/^\s/.test(line)) dropping = false
      else continue
    }
    kept.push(line)
  }
  return kept.join('\n').trim()
}

/** 次级对话内容等价判定（方案A-1）:只吃"归一化指纹"，逐层放宽容忍。
 *  a. 两个指纹都为空 → 视为同一条（空对空）；任一为空 → 不算同一条；
 *  b. 指纹完全相等 → 同一条；
 *  c. 指纹互为前缀 → 同一条（同段正文的截断 / 拼接差异）；
 *  d. 单向包含且短串 ≥ 30 字 → 同一条（同段正文被包在包装 / 摘要里）；
 *  e. 前 85% 重合且长度差 ≤ 25% → 同一条（同段正文尾部轻微差异）。
 */
function sameSecContent(a: string, b: string): boolean {
  const x = normSecText(a)
  const y = normSecText(b)
  if (!x && !y) return true
  if (!x || !y) return false
  if (x === y) return true
  if (x.startsWith(y) || y.startsWith(x)) return true
  const shortLen = Math.min(x.length, y.length)
  const longLen = Math.max(x.length, y.length)
  if (shortLen >= 30 && (x.includes(y) || y.includes(x))) return true
  const prefixLen = Math.floor(shortLen * 0.85)
  if (prefixLen > 0 && x.slice(0, prefixLen) === y.slice(0, prefixLen) && (longLen - shortLen) / shortLen <= 0.25) return true
  return false
}

/** 对消息列表按「类型 + 归一化指纹」做稳定去重（保留首次出现，顺序与折叠状态不变）。
 *  用途:localStorage 回灌可能带进"同一轮多份副本"，先用本函数归一化去重，
 *        再交给 mergeSecMessages 增量补齐 —— 避免本地旧副本被原样送进页面。
 */
function dedupeSecMessages(list: SecMsg[]): SecMsg[] {
  const out: SecMsg[] = []
  for (const m of list) {
    const dup = out.some(x => x.type === m.type && sameSecContent(String(x.content || ''), String(m.content || '')))
    if (!dup) out.push(m)
  }
  return out
}

/** 定位"本轮起点"（方案A-4）:取末尾最后一条 dispatch 的内容作为"本轮指印"，
 *  再正向找到【最早】与该指印等价的 dispatch 下标；
 *  这样即便页面同时存在"原版 + 若干重复副本"，也能一次性从最早那一份开始整段裁掉。
 *  返回 -1 表示消息列表中不存在 dispatch（首屏为空 / 仅历史无 dispatch）。
 */
function lastRoundStartIndex(list: SecMsg[]): number {
  let lastDispatch = -1
  for (let i = list.length - 1; i >= 0; i--) {
    if (list[i] && list[i].type === 'dispatch') { lastDispatch = i; break }
  }
  if (lastDispatch < 0) return -1
  const fingerprint = String(list[lastDispatch].content || '')
  if (!fingerprint) return lastDispatch
  for (let i = 0; i <= lastDispatch; i++) {
    const m = list[i]
    if (m && m.type === 'dispatch' && sameSecContent(String(m.content || ''), fingerprint)) return i
  }
  return lastDispatch
}

/** 方案A/B-1:把后端次级会话历史消息（{role,header,content,msg_type}）转为页面消息模型
 *  msg_type（后端回读新增字段）:think=思考过程 / tool=工具执行 / 空=派发或回报；
 *  有 msg_type 时优先按类型分气泡（与实时 SSE 表现一致），兼容旧记录（无该字段 → 走 role 分支）。 */
function convertSecHistoryMsg(m: any): SecMsg {
  const role = String((m && m.role) || '')
  const mtype = String((m && m.msg_type) || '')
  const body = String((m && m.content) || '')
  // AI 真思考（后端 ai_reasoning 事件落盘为 msg_type=think）:折叠展示
  if (mtype === 'think') {
    // 兼容老记录:历史错配期曾把「含工具调用块的正文」落盘为 think，检测到工具调用标记时按 AI 正文展示，
    // 避免把正文错当思考折叠隐藏（新记录不会再发生该错配）。
    // 说明:标记字符串用拼接方式构造，避免源码出现与工具调用块同名的字面量（防止编辑工具解析截断）。
    const _tmark = '【工具调用' + '开始】'
    const _tend = '【工具调用' + '结束】'
    if (body.includes(_tmark) || body.includes(_tend)) {
      return { type: 'ai', content: stripToolResultForDisplay(body), collapsed: true }
    }
    return { type: 'think', content: body, collapsed: true }
  }
  // AI 正文（后端 ai_output_stream 事件落盘为 msg_type=ai，含工具调用指令块）:整段展示
  // 【方案C·前端兜底】剥离历史落盘串里的「工具执行结果:…」段（后端已做，这里双保险）
  if (mtype === 'ai') return { type: 'ai', content: stripToolResultForDisplay(body), collapsed: true }
  // 兼容老记录:历史 msg_type=tool（旧「工具执行」节点，主对话页无此节点）按 AI 正文展示，不丢历史
  if (mtype === 'tool') return { type: 'ai', content: stripToolResultForDisplay(body), collapsed: true }
  // 派发 / 正文:按 role 区分（user → 派发；assistant → AI 正文）
  // 【修复·口径统一】assistant 的历史消息统一渲染为 ai 类型（不再渲染为 report）:
  // 后端落盘时，"流式正文"与"回报内容"本质是同一份内容
  // （orchestrator 先流式推 ai_output_stream、收尾再推 report）。
  // 若回读时把 assistant 渲染成 report，切换页面后就会出现
  // "AI 头像一条 + 回报头像一条"的视觉重复（用户实测反馈），
  // 且与 1.vue 实时口径不一致 —— 同一功能两副面孔。
  // 统一为 ai 后:实时渲染 ai、历史回读也渲染 ai，两页头像口径完全一致。
  if (role === 'user') {
    // 优先展示 header（后端落盘 header 已是主控原文），无 header 时回退 content
    return { type: 'dispatch', content: String((m && m.header) || body), collapsed: true }
  }
  // 【方案C·前端兜底】role 分支（老记录无 msg_type）同样剥离「工具执行结果:…」段
  return { type: 'ai', content: stripToolResultForDisplay(body), collapsed: true }
}

/** 启动回读:localStorage 先展示缓存，随后无条件从后端 /api/orch/secondary_history 按 session+slot 补齐（SSE 无回溯，补读是唯一能拿到历史派发的路） */
async function loadSecMessages() {
  // 第一步:首屏 rapid path —— 若页面为空，先用 localStorage 缓存即时渲染（防白屏）。
  //   【方案A-2·口径调整】localStorage 仅作"占位"，不是真源:
  //     若后端真源（/api/orch/secondary_history）能返回非空数据，下一步会先对本地回灌的
  //     消息做一次"归一化去重"，把本地缓存里累积的重复副本清掉，再交给 mergeSecMessages 增量补齐。
  let fromLocalCache = false
  try {
    if (!messages.value.length) {
      const raw = localStorage.getItem(secCacheKey())
      const saved = raw ? JSON.parse(raw) : []
      if (Array.isArray(saved) && saved.length) {
        messages.value = saved; fromLocalCache = true
        // 【方案B·根因修复】本地 localStorage 已有非空 messages 快照 → 标记"本地已完整"
        localSnapshotReady = true
      }
    }
  } catch {}
  // 第二步:向后端合并式补齐（不整段替换 —— 见 mergeSecMessages 注释）
  //   【方案C·完整根治·回读改读镜像】
  //     真源改为读「前端落盘的事件粒度镜像」= sessions/chat_secondary_{项目}.json
  //     （写入方 = 本文件的 persistSecMessages → POST /api/chat/history/save）。
  //     为什么要换:后端 /api/orch/secondary_history 返回的是「轮粒度拼接」= {role,content} 两条/轮，
  //     与页面的「事件粒度分条」天生不同 —— 一旦以它为准回读，页面会被那 1 条拼接文本整体替换，
  //     中间的 AI 正文段（工具调用前的说明 / 工具调用后的总结等）就全部消失（这就是"刷新后只剩总结"的根因）。
  //     镜像 = 前端 messages 数组原样落盘 → 与实时 / 回放 100% 同口径，刷新 / 切回 = 实时看到的。
  //     兜底:镜像为空（新项目 / 从未派发过）→ 回退旧接口，保证不白屏、不丢历史。
  try {
    let _arr: SecMsg[] = []
    // 优先:读事件粒度镜像（原样数组，含 type/content/collapsed）
    try {
      const _mres = await fetch(`/api/chat/history/load?project=${encodeURIComponent(SEC_PERSIST_PREFIX + SEC_SLOT + '_' + secProjectName())}`)
      const _mj = await _mres.json()
      const _md = _mj && Array.isArray(_mj.data) ? _mj.data : []
      if (_md.length) {
        // 只保留合法 SecMsg（type/content 均为 string），再做一次指纹去重（防镜像被污染）
        _arr = dedupeSecMessages(_md.filter((m: any) => m && typeof m.type === 'string' && typeof m.content === 'string'))
        // 【方案B·根因修复】后端事件粒度镜像已有非空数据 → 标记"本地已完整"
        //   （镜像就是本页 messages 数组的原样落盘，与实时/回放 100% 同口径）
        localSnapshotReady = true
      }
    } catch {}
    // 兜底:镜像为空 / 不可用 → 回退旧接口（轮粒度拼接），保证新项目首次进入不空白
    if (!_arr.length) {
      const _pn = encodeURIComponent(secProjectName())
      const res = await fetch(`/api/orch/secondary_history?session_id=default&slot=${SEC_SLOT}&project_name=${_pn}`)
      const j = await res.json()
      // 修复:后端返回为双层包裹 {code,msg,data:{ok,data:{session_id,slot,messages}}}，
      // 原写法 j.data.messages 少读一层 → 永远取到 undefined → 次级页永远空白；
      // 此处兼容双层（data.data）与单层（data）两种结构
      const _inner = j && j.data && j.data.data ? j.data.data : (j && j.data ? j.data : null)
      const _oj = _inner && Array.isArray(_inner.messages) ? _inner.messages : []
      _arr = _oj.map(convertSecHistoryMsg)
    }
    if (_arr.length) {
      // 【方案A-2·根因修复】回读命中非空 → 先对"本地缓存回灌产生的重复副本"做一次归一化去重，
      //   再由 mergeSecMessages 用 _arr 做增量补齐 —— 这是"多次切页后本地累积重复"的根治口径。
      if (fromLocalCache) messages.value = dedupeSecMessages(messages.value)
      mergeSecMessages(_arr)
    }
  } catch {}
}

/** 合并式回读（重写）:保留用户折叠状态 + 保证新内容立刻可见。
 *
 *  执行策略（三层判定，逐层收窄）:
 *  ────────────────────────────────────────────────────────────
 *  ① 消息列表为空（首屏）→ 整段铺 fresh；
 *  ② 有消息 + 正在流式中（roundAiMsg / roundThinkMsg 存在且仍在列表内）
 *     → 只补尾部新增，绝不整体重建（保护"逐字流式"的气泡不被回读打断）；
 *  ③ 有消息 + 非流式（对话已结束 / 打开首屏 / 切回页面）
 *     → 以「后端落盘数据」为权威整体重建，逐条按「type + content」对齐:
 *        - 内容完全一致 → 继承用户已点击的 collapsed（用户操作优先）；
 *        - 内容不一致 / 新条目 → 采用 fresh 的版本（后端为准）。
 *
 *  为什么必须重写（根因）:
 *  旧实现 `if (fresh.length <= cur.length) return` 会在「后端条数没增加」时
 *  直接 return —— 结果:
 *    1) 打开本页时 localStorage 有旧缓存(比如 N 条)，后端此刻也只落 N 条
 *       → 短路 return → 一个字都不更新 → 「打开看不到新内容」；
 *    2) 用户切页后，后端已多落几条 → 补齐 → 一次性蹦出 → 「不是流式」。
 *  这条短路就是"必须切页才显示 / 一次蹦出来"的根因。
 */
function mergeSecMessages(fresh: SecMsg[]) {
  const cur = messages.value
  // ⓪【回放期保护·新增】SSE 建连回放期间:本轮内容由后端「回放事件流」逐条铺出，是此刻唯一真源；
  //    此时后端落盘历史（fresh）往往尚未落全、内容是旧快照，
  //    若仍走下方 ③「以 fresh 为权威整体重建」，就会把刚回放/刚流式出来的正文顶回旧内容
  //    → 用户看到内容闪退、必须切页才蹦出来（这正是缺陷2 的机制）。
  //    故回放期只做一件事:把 fresh 中 messages 尚未包含的「新条目」按序补到末尾，不覆盖、不重建。
  if (replaying) {
    // 【方案B-1·根因修复】回放期直接丢弃本次回读结果（fresh 整段忽略）:
    //   回放期间「回放事件流」是本轮唯一真源；后端落盘历史（fresh）此刻仍是
    //   「轮粒度 + 工具结果已净化」的旧口径，与页面上正由回放铺出的
    //   「事件粒度 + 含工具块原文」气泡口径不一致 —— 按「完全相等」补尾部必然判不出重复，
    //   于是每次切页回来都追加一份派发/思考/正文 → 多次切页即多次累积重复。
    //   口径:回放期一律不合并 fresh；历史轮的补齐交给 onopen（首屏）与切回页面时的合并回读。
    return
  }
  // ① 首屏:整段铺
  if (!Array.isArray(cur) || cur.length === 0) {
    messages.value = fresh
    // 【显示优化】首屏铺完 → 强制滚到底部，直接看到最新内容
    scrollToBottom(true)
    return
  }
  // ② 【已移除·根因级】不再用 roundAiMsg/roundThinkMsg 引用判定"_streaming"并短路 return:
  //    旧逻辑只要指针还在数组里就判定"正在流式"，随后 `if (fresh.length <= cur.length) return`
  //    → 后端条数没增加时一个字都不更新 → 用户停在页面上看到内容"冻住"，
  //    切页后 fresh 变长才"一次蹦出来"（这就是"更新到夹层里"的机制）。
  //    现改为:无论是否流式，统一走下方 ③ 的"逐条 type+content 去重合并"，
  //    与数组整体替换、对象引用完全解耦，永不空转 return。
  // ③ 非流式:以「页面当前列表」为基准、按内容等价去重，只把 fresh 中页面确实没有的历史轮补到末尾。
  //    【根因修复·切页回来多出一行 AI 正文】
  //    旧实现按数组索引把 fresh 与 cur 逐位对齐，但两者粒度天生不同:
  //      · 后端回读 fresh = 「轮粒度」（问 + 答，AI 正文已经 stripToolResultForDisplay 净化）
  //      · 页面 cur      = 「事件粒度」（dispatch / think / ai 多条交替）
  //    索引一错位、type 就比对不上 → 同一句正文（含工具块的实时版 vs 净化版）被判为"新条目"追加，
  //    而页面上同句正文仍然存在 → 视觉上就是"切页回来多出一行"。
  //    现改为「内容等价判定 + 以页面为基准增量补齐」:
  //      · 互为前缀 = 同一轮内容（含工具块原文 vs 已剥离净化版）→ 判定为同一条，不追加；
  //      · 页面现状（顺序 + 用户点击过的折叠状态）100% 保留，不被重建；
  //      · fresh 仅承担"补页面缺失的历史轮"职责，多次切页幂等、无副作用。
  // 【方案A-1·判重解耦】不再用裸串"相等/互为前缀"做判据，改用归一化指纹等价判定:
  //   这样「实时/回放 = 含工具块原文」与「后端落盘 = 已剥离净化版」会被识别为同一条，
  //   多次切页/多次回读都幂等，不再追加同款副本。
  const merged: SecMsg[] = []
  // 页面现状全量保留（顺序、折叠状态不动）—— fresh 只做"增量补齐"，不再整体重建
  for (const m of cur) merged.push(m)
  for (const f of fresh) {
    const hit = merged.find(m => m.type === f.type && sameSecContent(String(m.content || ''), String(f.content || '')))
    // 命中同款（含互为前缀的含工具块版 / 净化版）→ 跳过，避免同句正文并存
    if (hit) continue
    // 页面确实没有的新历史轮 → 追加到末尾（首次进入补齐历史 / 新历史轮落盘后的补读）
    merged.push(f)
  }
  // 【刷新去噪·根因修复】零新增 → 早退:不换数组、不重排、不滚底，完整保留用户当前视图与阅读位置。
  //   机制:上方 ③ 分支已把页面现状（cur）全量拷入 merged，随后仅按「type + 内容指纹」补 fresh 中
  //   页面确实没有的历史轮；因此 merged.length === cur.length 等价于"fresh 里没有任何页面没有的新条目"。
  //   此时若仍执行 messages.value = merged，即使内容等价，也会换掉数组引用、触发整列表重排，
  //   再叠加 scrollToBottom(true) 强制滚底 —— 这正是"切走再切回、无任务派发也重复刷新一次"的直接落点。
  //   修复口径:无新增 = 无副作用可做 → 直接 return；仅当确实出现新条目时才更新并滚底。
  if (merged.length === cur.length) return
  messages.value = merged
  // 【显示优化】回读补齐完成 → 强制滚到底部（切回页面 / 切项目重载后立刻看到最新内容）
  scrollToBottom(true)
}
/** 防抖落盘:400ms 合并，避免流式每帧全量写盘阻塞主线程 */
watch(messages, () => {
  if (secPersistTimer) clearTimeout(secPersistTimer)
  secPersistTimer = setTimeout(() => { persistSecMessages() }, 400)
  // 【显示优化】任意"新增气泡"都同步折叠态 + 自动滚底（think / ai / report 的流式新增同样触发）:
  //  原实现只在 SSE「dispatch 到达」时折叠，think / ai / report 增量新增气泡不触发 → 历史气泡不折叠；
  //  现 updateFoldStates() 已跳过 userTouched 气泡，"用户点击被重置"的顾虑从根上消除，故放开触发条件。
  if (messages.value.length !== lastMsgCount) {
    lastMsgCount = messages.value.length
    updateFoldStates()
    // AI 流式新增 → 智能跟随（用户正在上翻时不打断）；派发/回读等强制滚底由各自分支另行调用
    scrollToBottom(false)
  }
}, { deep: true })

/** 阶段5-1:SSE 单连接句柄（次级独立通道 /api/chat/stream/sec_{SEC_SLOT}，与主控 default 物理隔离） */
let es: EventSource | null = null

/** 页面重新可见时补一次合并式回读（替代原 2 秒兜底轮询）:
 *  历史回读只发生在「连接建立」与「页面重新可见」两个时机，绝不周期性刷新 —— 这是修复
 *  "折叠点击被反复重置""流式过程被整段覆盖"的根治口径；
 *  "不切页不显示"的原场景由 es.onopen 立即回读 + 本函数切回时补一次覆盖，效果等价、副作用为零。 */
function onVisibilityChange() {
  if (document.visibilityState === 'visible') loadSecMessages()
}

/** [AI-FILL] change 事件:切换历史会话后拉取对应记录 */
function handleChatGroupChange() {
  // TODO: 补全业务逻辑
}

/** [AI-FILL] click 事件:开启新对话（清空上下文 / 新建会话） */
function handleNewChat() {
  // TODO: 补全业务逻辑
}

/** [AI-FILL] click 事件:复制思考内容 */
function handleCopyThink() {
  // 提示: 使用 navigator.clipboard.writeText(要复制的内容) 实现复制
  // TODO: 补全业务逻辑
}

/** [AI-FILL] click 事件:截图并回填输入框 */
function handleScreenshot() {
  // TODO: 补全业务逻辑
}

/** [AI-FILL] click 事件:上传文件 */
function handleSendFile() {
  // TODO: 补全业务逻辑
}

/* 阶段5-1（V1 主线口径）:次级页无发送入口，handleChatSend 已移除 */

/* 阶段5-1（V1 主线口径）:不再有前端任务提交入口 / 任务列表刷新 / 中止调用 */

/** 阶段5-1（V1 主线口径）:SSE 单连接，次级会话消息流（@派发 / @回报）
 *  通道隔离（Step 2）:连本页专属通道 sec_{SEC_SLOT}（如 sec_2），与主控 default 物理隔离，
 *  主控事件不会再漏进本页；下方 slot 过滤保留作为双保险。 */
function connectSSE() {
  // 【方案C·完整根治·跨项目串台】通道键与后端 orchestrator.push_secondary_event 严格对应 = sec_{slot}_{项目}:
  //   原实现仅 sec_{slot}（无项目维度）→ 项目A 派发后切到项目B，B 页连的仍是同一条 sec_{slot}
  //   → 后端把 A 的残留快照回放给 B 页 → 用户看到"两个项目显示同一内容"。
  //   现改为 URL 携带项目名，与后端通道键 = sec_{SEC_SLOT}_{项目} 严格一一对应:
  //     · 项目切换后立即重连（见 onStorageChange）→ 各项目物理上是独立通道与独立快照；
  //     · 项目名空值回退 'default'，与后端 _proj = project or "default" 口径一致。
  //   【方案A·回放提速】URL 追加 ?fast=1:
  //     仅影响「建连时的历史快照回放节奏」—— 后端 fast=True 时 0ms/条快发（原 18ms/条打字机节奏），
  //     切回从"秒级逐字重播"压到毫秒级；实时任务进行中的流式 chunk 不受任何影响（仍逐字推）。
  //     · 回放的内容 / 顺序 / 条数 100% 不变，气泡最终形态与逐字回放完全一致。
  es = new EventSource('/api/chat/stream/sec_' + SEC_SLOT + '_' + (secProjectName() || 'default') + '?fast=1')
  // 连接建立后立即回读一次历史:
  // 兜住"派发/思考/正文事件先于 SSE 建立"这种时序竞争 —— 打开页面瞬间，后端已在推事件，
  // 但前端还没注册进 SSE_CONNECTIONS["sec_2"]，后端会直接丢弃这些事件；
  // 此回读是唯一能补齐的方式（后端 SSE 无回溯）。
  es.onopen = () => {
    // 【方案B-2·根因修复】建连回读只服务"首屏补历史"这一个目的:
    //   每次进入/切回本页都会触发 onopen，若无条件回读，就会在"回放尚未开始或正在回放"的窗口里
    //   把后端旧口径历史合并进来，与页面上已有内容判重失配 → 内容重复累积。
    //   口径:messages 为空（首次进入）才回读；已有内容时不回读，避免重复注入。
    if (!messages.value.length) loadSecMessages()
  }
  es.onmessage = (ev) => {
    try {
      // 【根因修复·新增】容错剥离 SSE 数据帧可能残留的 `data: ` 前缀。
      //   根因:实测浏览器交付的 event.data 仍带 `data: ` 前缀（形如 "data: {\"type\":...}"），
      //   直接 JSON.parse 必然抛异常；而原 catch 是空块 → 异常被静默吞掉 →
      //   所有事件（含逐字 ai_output_stream 与 heartbeat）全部被丢弃，
      //   表现就是"onopen 已触发（连接正常）却一个字都收不到，必须切页回读才有内容"。
      //   处理:显式剥一层 `data:` 前缀（含其后可选空格）再解析；只剥一层，绝不破坏合法 JSON。
      let raw = String(ev.data ?? '')
      if (raw.startsWith('data:')) {
        raw = raw.slice(5)
        if (raw.startsWith(' ')) raw = raw.slice(1)
      }
      const msg = JSON.parse(raw)
      // 方案A/B-2:只接收本页槽位事件（无 slot 字段的旧事件照收，保持兼容）
      if (msg.slot != null && Number(msg.slot) !== SEC_SLOT) return
      // 【方案B·根因修复】跳过回放期:本地已有完整本轮快照时（判定见下方 sec_replay_begin 分支），
      //   回放事件（dispatch / think / ai_output_stream / ai_output / report）一律静默丢弃，
      //   直到 sec_replay_end 复位 —— 实现"切回零延时"（本地一铺到位，不再逐字重播）。
      //   安全边界:
      //     · 此时本轮内容已由本地快照完整呈现（localSnapshotReady 已确证），丢弃不影响任何内容；
      //     · 若回放期间确有实时事件混入（任务进行中被切回），任务结束时会通过
      //       onVisibilityChange 补一次合并回读做最终对齐，保证不丢新内容。
      //     · sec_replay_end 到达时 flushDomUpdates()，保证缓冲不为空。
      if (skipReplay) {
        if (msg.type === 'sec_replay_end') {
          skipReplay = false
          flushDomUpdates()
        }
        return
      }
      // 【回放节奏真实化·新增】SSE 建连回放期标记（与后端 sec_replay_begin / sec_replay_end 配对）:
      //   · 回放开始 → 置 replaying=true，重置本轮气泡指针与流式标记，
      //     让后端回放的逐字增量落到「本轮新气泡」上（否则会续写到上一轮的旧气泡/幽灵对象里）；
      //   · 回放结束 → 置 replaying=false，先刷一次缓冲（防尾包被吞），再补一次历史对齐。
      //   该标记同时是 mergeSecMessages 的「回放期保护」依据（回放期禁止整段重建）。
      if (msg.type === 'sec_replay_begin') {
        // 【方案B·根因修复】本地已完整 → 跳过回放重建（切回零延时）:
        //   本页 messages / 后端事件粒度镜像（sessions/chat_secondary_{项目}.json，就是本页原样落盘）
        //   在"切回"场景下通常已是本轮完整快照；此时若仍按原逻辑"裁掉本轮 + 靠回放事件逐条重建"，
        //   就会经历"先消失、再逐字重播"的秒级空白 —— 这正是用户感知到的切回延时主因之一。
        //   跳过判定（三条全满足才跳过，保证绝不丢内容）:
        //     ① localSnapshotReady:本地已有非空快照（见 loadSecMessages 两处置位）;
        //     ② messages.value.length > 0:页面已铺好内容（非首屏）;
        //     ③ lastRoundStartIndex >= 0:能定位本轮起点（确认是本轮而非纯历史）。
        //   满足 → skipReplay=true 且不裁气泡；不满足 → 走原逻辑（裁气泡 + 回放重建），
        //   保证首屏 / 无本地快照时内容完整无缺失。
        if (localSnapshotReady && messages.value.length > 0 && lastRoundStartIndex(messages.value) >= 0) {
          skipReplay = true
          replaying = false
          // 本轮指针按原口径复位（回放被跳过后，后续实时事件从新气泡起算，不被回放污染）
          roundThinkMsg = null
          roundAiMsg = null
          streamedThisTurn = false
          taskActive.value = true
          return
        }
        replaying = true
        roundThinkMsg = null
        roundAiMsg = null
        streamedThisTurn = false
        taskActive.value = true
        // 【回放去重·根因修复】回放前先移除"本轮"（= 最后一条 dispatch 及其之后）的已有气泡，
        //   让回放事件从头完整重建本轮 —— 这是"切页回来本轮内容整段重复"的根治口径。
        //   根因:回放下发的事件与落盘内容"口径不同"
        //        （dispatch=派发原文 vs 落盘 header；think/ai=含工具结果原文 vs 落盘已剥离工具结果），
        //        下游 mergeSecMessages 按"完全相等"去重必然失败 → 旧气泡 + 回放气泡同存 → 重复。
        //   口径:回放期"本轮内容"以回放事件为唯一真源，不与页面上残留的旧版本并存。
        //   边界:messages 中无 dispatch（首屏为空 / 仅历史无 dispatch）→ 不移除，回放直接在末尾追加，同样不重复。
        // 【方案A-4·根因修复】裁剪锚点由"数组末尾下标"改为"按内容定位本轮最早一份":
        //   旧实现只裁掉末尾最后一条 dispatch 及之后 —— 若判重曾失败把整轮又追加到末尾，
        //   页面上就同时存在"原版 + 副本"两份；只裁末尾那份 → 留下原版 → 回放再铺一遍 → 两份一模一样。
        //   现改为:先取末尾最后一条 dispatch 内容做"本轮指印"，再用归一化指纹从列表头找到【最早】等价的
        //   dispatch，从那里开始整段裁掉 —— 无论累积了多少份重复副本，都被一次性清干净。
        //   边界:messages 中无 dispatch（首屏为空 / 仅历史无 dispatch）→ 返回 -1 → 不裁，回放直接在末尾追加，同样不重复。
        const _list = messages.value
        const _roundStart = lastRoundStartIndex(_list)
        if (_roundStart >= 0) {
          messages.value = _list.slice(0, _roundStart)
        }
        return
      }
      if (msg.type === 'sec_replay_end') {
        // 【方案A·根因修复】回放结束不再触发"回读 + 合并":
        //   回放事件流已把本轮完整铺出（唯一真源），紧随其后的这次回读
        //   会拿"轮粒度 + 已净化"的后端历史与页面"事件粒度 + 含工具块原文"的气泡做判重，
        //   口径失配 → 必然再追加一份 → 这是"切页一次多一份"最确定的注入点。
        //   口径:本轮以回放为唯一真源；历史轮补齐交给 onopen（首屏）与切回时机的合并回读。
        replaying = false
        flushDomUpdates()
        return
      }
      // 【修复·根因级 v2】后端在 SSE 连接建立时下发的「本轮快照」重放:
      // 上一版逻辑:仅在 done=false（本轮进行中）时铺 —— 假设"结束时历史文件已落盘"，
      //            而实际落盘有延迟（后台线程写 json + 项目隔离路径查询），
      //            于是任务刚结束时打开次级页 → done=true → 一条不铺 → 历史也没落盘
      //            → 用户看到"空白，必须切页才显示"。这就是根因。
      // 现改为:无论 done 是什么，都按"类型+内容"逐条去重后铺 ——
      //        - 快照内容还没在 messages 里 → 铺（立刻可见，不用等历史落盘）；
      //        - 快照内容已在 messages 里（历史先到）→ 跳过该条（不重复）。
      // 并统一把本轮 think/ai 指针指向"最后一条"，保证后续流式增量有正确落点。
      if (msg.type === 'sec_snapshot') {
        const _sq = String(msg.query || '')
        const _sr = String(msg.reasoning || '')
        const _so = String(msg.output || '')
        const _hasSame = (t: string, c: string) => messages.value.some(m => m.type === t && String(m.content || '') === c)
        const _findLast = (t: string) => {
          for (let i = messages.value.length - 1; i >= 0; i--) {
            if (messages.value[i].type === t) return messages.value[i]
          }
          return null
        }
        if (_sq && !_hasSame('dispatch', _sq)) {
          messages.value.push({ type: 'dispatch', content: _sq, collapsed: false })
        }
        if (_sr && !_hasSame('think', _sr)) {
          messages.value.push({ type: 'think', content: _sr, collapsed: false })
        }
        if (_so && !_hasSame('ai', _so)) {
          messages.value.push({ type: 'ai', content: _so, collapsed: false })
        }
        // 无论是否新铺，本轮指针都要指向最后一条 think/ai（后续流式增量才能正确追加）
        if (_sr) roundThinkMsg = _findLast('think')
        if (_so) roundAiMsg = _findLast('ai')
        // 【修复·根因级】快照里已经带了流式正文（_so）→ 视同"本轮已收到过流式正文"，
        // 必须置位 streamedThisTurn，否则收尾 report 到达时判重失效 → 再贴一条重复气泡
        // （用户实测:同一段"只读核验已完成…"出现两条、头像相同）。
        if (_so) streamedThisTurn = true
        // 本轮仍在进行 → 点亮能量条（快照 done 由 report/ai_output 事件置位）
        if (!msg.done) taskActive.value = true
        return
      }
      if (msg.type === 'dispatch') {
        // 新一轮派发到达 → 重置本轮 think/ai 气泡引用（保证新一轮的增量追加落到新气泡上）
        roundThinkMsg = null
        roundAiMsg = null
        // 新一轮开始 → 清零"本轮已流式"标记（收尾 report 去重的权威口径）
        streamedThisTurn = false
        messages.value.push({ type: 'dispatch', content: msg.content ?? msg.text ?? '' })
        taskActive.value = true
        // 新一轮开始 → 折叠历史、展开最新一条。
        // 【显示优化】updateFoldStates() 内部已跳过 userTouched 气泡，用户手动开合不会再被重置。
        updateFoldStates()
        // 【显示优化】新一轮派发 = 用户新消息 → 强制滚到底部（必须立刻可见）
        scrollToBottom(true)
      } else if (msg.type === 'report' || msg.type === 'secondary_summary') {
        // 流结束先刷缓冲，避免尾包被吞（对齐主对话页「ai_output 到达先 flushDomUpdates」口径）
        flushDomUpdates()
        // 流式改造后去重（新增）:最终轮正文已通过 ai_output_stream 流式到达本页，
        // report 若与末条 ai 气泡内容完全相同则不重复 push（避免出现"同一轮两个相同气泡"），
        // 但仍保留其"本轮结束"语义（下方熄灭能量条）——这是流式改造的必要配套。
        const _reportText = String(msg.content ?? msg.summary ?? '')
        // 去重判据（根治重复·v3）:不再依赖"末条必须是 ai 类型"这一脆条件，改为双重判据 ——
        //   ① 本轮收到过任何流式正文（streamedThisTurn===true）→ 直接判重；
        //   ② 遍历 messages 中所有 ai 气泡:任一条内容与 report 完全相同 / 以 report 结尾 → 判重。
        // 为什么这样改:report 与 ai 本质是同一份内容（后端先流式推 ai_output_stream、
        // 收尾再推 report）。原判据只看"末条"，而多轮任务里末条可能是 dispatch/think/report，
        // 一旦不是 ai 类型，整个判据直接短路 → report 必被再贴一遍 →
        // 用户看到"一条 AI 头像 + 一条回报头像、内容相同"的重复。
        // 且本判据不引用 roundAiMsg 对象引用，与数组整体替换完全解耦，任何路径下都稳定。
        let _anyAiSame = false
        if (!streamedThisTurn) {
          for (let i = messages.value.length - 1; i >= 0; i--) {
            const _m = messages.value[i]
            if (!_m || _m.type !== 'ai') continue
            const _t = String(_m.content || '')
            if (!_t) continue
            if (_t === _reportText || (_reportText.length > 0 && _t.endsWith(_reportText))) {
              _anyAiSame = true
              break
            }
          }
        }
        const _isDupAi = !!(streamedThisTurn || _anyAiSame)
        if (_reportText && !_isDupAi) {
          messages.value.push({ type: 'report', content: _reportText })
        }
        // 结束信号兜底（Step 3）:次级已走独立通道，主控的 memory_saved 不再进本页，
        // 故在本轮最终回报到达时熄灭能量条，避免能量条常亮。
        taskActive.value = false
      } else if (msg.type === 'think' || msg.type === 'ai_reasoning') {
        // AI 真思考（reasoning_content）:入帧节流缓冲，rAF 时一次性追加到当前 think 气泡（对齐主对话页口径）；
        // think 为旧事件名，保留向后兼容
        const thinkText = msg.content ?? msg.text ?? ''
        if (thinkText) {
          pendingThink += thinkText
          scheduleFlush()
        }
      } else if (msg.type === 'ai_output_stream') {
        // AI 正文流式增量:入帧节流缓冲，rAF 时一次性追加到当前 ai 气泡（对齐主对话页口径）
        const aiText = msg.content ?? msg.text ?? ''
        if (aiText) {
          // 标记本轮已收到过流式正文 → 收尾 report 到达时整段忽略（根治重复）
          streamedThisTurn = true
          pendingStream += aiText
          scheduleFlush()
        }
      } else if (msg.type === 'ai_output') {
        // 正文收尾兜底:先刷缓冲（避免尾包被吞），若本轮从未收到任何 stream 增量，用完整内容推送一次
        flushDomUpdates()
        const aiText = msg.content ?? msg.text ?? ''
        if (aiText && !roundAiMsg) appendAiOutput(aiText)
        // 【需求2·分气泡·对齐主对话页】后端每轮 AI 正文收尾会补推一次 ai_output 终态事件,
        // 前端收到后必须显式置空本轮气泡指针:
        //   · 下一轮的 ai_output_stream 增量 → 不再续写旧气泡,自然 push 出新气泡;
        //   · 多轮 AI 输出(一轮/二轮/三轮…)天然分气泡,视觉上"一轮一个气泡",与主对话页 100% 同构;
        //   · 工具执行结果按用户口径不推前端 → 用户看到的分气泡内容 = 纯 AI 输出内容。
        // 对齐 PageO0x2f.vue L908-916 的"终态置空"机制;与 report 事件不冲突(report 分支靠 streamedThisTurn 判重)。
        roundThinkMsg = null
        roundAiMsg = null
      } else if (msg.type === 'memory_saved' || msg.type === 'error') {
        taskActive.value = false
      }
    } catch (err) {
      // 【健壮性·长期保留】不再静默吞异常:
      //   原实现是空 catch，JSON.parse 失败（含心跳等非 JSON 内容）全被藏住，
      //   排查时看不到任何线索 → 反复回环。现降级为可见告警并附带原始数据，便于一次性定位。
      console.warn('[SEC] onmessage 处理失败 raw=', String(ev.data).slice(0, 200), err)
    }
  }
  es.onerror = () => {
    console.warn('[orch] SSE 连接异常，浏览器将自动重连')
  }
}

onMounted(() => {
  connectSSE()
  // 顶部显示当前项目名，并跟随主窗/悬浮窗的项目切换（读 localStorage['current_selected_project']）
  syncProjectFromStorage()
  // 顶部显示本页次级角色名（"开发 · 模型名"）
  loadSecRoleLabel()
  // 方案A:恢复上次的次级对话消息（localStorage 优先，为空则从后端回读）
  loadSecMessages()
  // 【阶段5-2·T4】恢复思考模式开关的持久化状态（不 await:异步读取，不阻塞 SSE 与后续事件监听注册）
  loadThinkMode()
  // 页面重新可见时补一次合并式回读（替代原定时轮询；非周期性，不影响折叠状态与流式观感）
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('storage', onStorageChange)
})

onUnmounted(() => {
  window.removeEventListener('storage', onStorageChange)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  if (es) {
    es.close()
    es = null
  }
})

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPage1() {
  router.push('/1')
}

function goPage12() {
  router.push('/1-2')
}

function goPage22() {
  router.push('/2-2')
}

function goPage32() {
  router.push('/3-2')
}

function goPage42() {
  router.push('/4-2')
}

function goPage52() {
  router.push('/5-2')
}

function goPage62() {
  router.push('/6-2')
}

function goPage72() {
  router.push('/7-2')
}
</script>

<style scoped>
.box-div-nbrvi {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-kwru5 {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  flex-grow: 1;
  min-height: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-s0rn6 {
  display: flex;
  flex-direction: row;
  gap: 6px;
  min-height: 40px;
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding-top: 5px;
  padding-right: 12px;
  padding-bottom: 12px;
  padding-left: 12px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  height: 40px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-start;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-45g0b {
  font-size: 18px;
  color: #1d2129;
  display: none;
  align-self: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-span-8d74b {
  font-size: 20px;
  font-weight: 600;
  color: #1d2129;
  text-align: center;
  align-self: center;
  margin-right: 12px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-bk35h {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-ehg1m {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-2ke2s {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-jy07j {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-92cbv {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-3yza8 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-u5t27 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-1m6p4 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 12px;
  padding-bottom: 6px;
  padding-left: 12px;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-zutir {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 40px;
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding-top: 16px;
  padding-right: 16px;
  padding-bottom: 16px;
  padding-left: 16px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  flex-grow: 1;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-u5vtw {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  flex-grow: 1;
  min-height: 400px;
  overflow: hidden;
  background-color: #ffffff;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-8vbro {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: 100%;
  flex-grow: 0;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-jieyo {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: auto;
  flex-grow: 1;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-select-22m8f {
  font-size: 13px;
  color: #1f2329;
  background-color: #ffffff;
  border-style: solid;
  border-color: #e5e6eb;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  padding-top: 4px;
  padding-right: 8px;
  padding-bottom: 4px;
  padding-left: 8px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-7u0t5 {
  font-size: 12px;
  color: #4e5969;
  background-color: #f7f8fa;
  border-style: none;
  padding-top: 4px;
  padding-right: 10px;
  padding-bottom: 4px;
  padding-left: 10px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-qty03 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: auto;
  flex-grow: 0;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-iklzd {
  font-size: 12px;
  color: #4e5969;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

/* 【主题统一·T2】开启态轨道改用全局主色令牌 var(--primary) + 兜底 #165DFF:
   病灶:原先硬编码 #165DFF → 用户在「系统配置 → 界面主题」把主色改成粉紫/红时，开关仍停留在蓝色（未接主题）。
   兜底值保证 theme.js 加载失败时轨道仍为蓝底可见可辨（兜底口径与主对话页 .box-div-7pnux.think-on 完全一致）。
   关闭态 .box-div-r9cdx.switch-off 的灰轨 #d8dce5 属中性色，不随主题变化，保持不变。 */
.box-div-r9cdx {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
  width: 44px;
  height: 24px;
  min-width: 44px;
  padding-left: 4px;
  padding-right: 4px;
  background-color: var(--primary, #165DFF);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
  border-bottom-left-radius: 12px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-8274x {
  width: 16px;
  height: 16px;
  min-width: 16px;
  max-width: 16px;
  background-color: #ffffff;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}
/* AI思考模式开关:关闭态（灰轨 + 滑块靠左），与开启态（主色轨道 var(--primary) + 滑块靠右）区分。
   【阶段5-2】原注释写"蓝 #165DFF"已过时 —— 开启态已改为跟随后端主题主色，
   用户切换主题（如粉紫 #EE2AF1）时本开关同步变色，不再固定为蓝。 */
.box-div-r9cdx.switch-off {
  background-color: #d8dce5;
  justify-content: flex-start;
}

.box-div-6e3mh {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  flex-grow: 1;
  min-height: 0px;
  overflow: auto;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-q87ne {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  min-width: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-4x3up {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  max-width: 36px;
  /* 【头像接入】已删除原文字徽标的 background-color: var(--primary) 蓝底，
     以及 color / font-size / font-weight 三项仅对文字生效的属性；
     PNG 为圆形透明底，去蓝底后四角不再露色。 */
  object-fit: cover;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-kdism {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-grow: 1;
  min-width: 0px;
  background-color: #f7f8fa;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-qexcn {
  font-size: 14px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-pgdps {
  display: flex;
  flex-direction: row-reverse;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  min-width: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-g5t8t {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  max-width: 36px;
  background-color: #86909c;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-w2py2 {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-grow: 1;
  min-width: 0px;
  background-color: #f7f8fa;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-3jrmj {
  font-size: 14px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-hi0g4 {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  background-color: #f7f8fa;
  padding-top: 10px;
  padding-right: 10px;
  padding-bottom: 10px;
  padding-left: 10px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-uzlg1 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  width: 100%;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-nyt8w {
  font-size: 12px;
  color: #4e5969;
  background-color: transparent;
  border-style: none;
  padding-top: 2px;
  padding-right: 6px;
  padding-bottom: 2px;
  padding-left: 6px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-span-4illm {
  font-size: 12px;
  font-weight: 600;
  color: #4e5969;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-lo98c {
  font-size: 12px;
  color: #4e5969;
  background-color: transparent;
  border-style: none;
  padding-top: 2px;
  padding-right: 6px;
  padding-bottom: 2px;
  padding-left: 6px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-h9xkp {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-8pxmq {
  font-size: 12px;
  color: #86909c;
  line-height: 1.7;
  white-space: pre-wrap;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-moxfw {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  min-width: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-kbzfw {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  max-width: 36px;
  background-color: var(--primary);
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-y8bio {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-grow: 1;
  min-width: 0px;
  background-color: #f7f8fa;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-7ak7e {
  font-size: 14px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-hftze {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  flex-grow: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-npqfl {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: auto;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-4r28n {
  font-size: 12px;
  color: #4e5969;
  background-color: #f7f8fa;
  border-style: none;
  padding-top: 4px;
  padding-right: 10px;
  padding-bottom: 4px;
  padding-left: 10px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-1tf3w {
  font-size: 12px;
  color: #4e5969;
  background-color: #f7f8fa;
  border-style: none;
  padding-top: 4px;
  padding-right: 10px;
  padding-bottom: 4px;
  padding-left: 10px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-j4npf {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: auto;
  min-width: 0px;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  flex-grow: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-321ft {
  width: 3px;
  height: 6px;
  min-width: 3px;
  background-color: #d8dce5;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-zta3r {
  width: 4px;
  height: 10px;
  min-width: 4px;
  background-color: #d8dce5;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-m9zq2 {
  width: 4px;
  height: 14px;
  min-width: 4px;
  background-color: var(--primary);
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-lcd6v {
  width: 5px;
  height: 18px;
  min-width: 5px;
  background-color: var(--primary);
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-gp30n {
  width: 6px;
  height: 22px;
  min-width: 6px;
  background-color: var(--primary);
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-ecduj {
  width: 5px;
  height: 18px;
  min-width: 5px;
  background-color: var(--primary);
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-ot9di {
  width: 4px;
  height: 14px;
  min-width: 4px;
  background-color: var(--primary);
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-enhcf {
  width: 4px;
  height: 10px;
  min-width: 4px;
  background-color: #d8dce5;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-wqk1p {
  width: 3px;
  height: 6px;
  min-width: 3px;
  background-color: #d8dce5;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-yipj7 {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 8px;
  width: auto;
  flex-grow: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-textarea-nvw17 {
  flex-grow: 1;
  min-width: 0px;
  font-size: 13px;
  color: #1f2329;
  background-color: #ffffff;
  border-style: solid;
  border-color: #e5e6eb;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-stgen {
  font-size: 13px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 8px;
  padding-right: 16px;
  padding-bottom: 8px;
  padding-left: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}
/* 顶部当前项目名（跟随主窗/悬浮窗项目切换，仅展示不可选） */
.box-span-curproj {
  font-size: 12px;
  color: #4e5969;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

/* 主控模型图标（派发气泡右侧，复用主窗机器人头像 logo.png，尺寸对齐 AI 圆徽） */
.box-img-mainctl {
  width: 36px;
  height: 36px;
  min-width: 36px;
  max-width: 36px;
  border-radius: 50%;
  object-fit: cover;
}

/* 气泡折叠态:限制高度（4.8em ≈ 3 行，与主对话页 .msg-folded 完全一致）+ 隐藏溢出；
   结构口径已对齐主对话页:折叠态挂「内容容器 div」（不再是内容 span），
   按钮容器与内容容器同级 → 折叠时按钮位置不动，永远不会"钻进气泡" */
.msg-folded {
  max-height: 4.8em;
  overflow: hidden;
  position: relative;
}

/* 气泡操作栏:折叠按钮容器（对齐主对话页 .box-div-msgact） */
.box-div-msgact {
  display: flex;
  flex-direction: row;
  gap: 6px;
  margin-top: 4px;
}

/* 气泡操作按钮:平时无边框/透明（逐字照抄主对话页 .box-button-msgact）；
   悬停时才出现灰底，与主对话页视觉完全统一。
   此前本页缺该样式 → 浏览器套用默认按钮边框 → 用户看到"按钮多出外框"，
   本条即修复该问题的根因（不再是补丁式微调）。 */
.box-button-msgact {
  border: none;
  background: transparent;
  color: #86909c;
  font-size: 12px;
  line-height: 1.4;
  padding: 2px 6px;
  border-radius: 4px;
  transition: color .15s ease, background-color .15s ease;
  cursor: pointer;
}
.box-button-msgact:hover {
  color: var(--primary);
  background-color: #f2f3f5;
}

/* 次级模型思考过程折叠区 */
.box-div-sec-think {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}
.box-span-sec-think {
  font-size: 12px;
  color: #86909c;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

/* 能量条基础态:所有子柱默认灰色（对齐主控 .box-div-nkke7 > div；缺此条会导致 energy-active 动画与写死色互相抵消失去动态观感） */
.box-div-j4npf > div {
  background-color: #d8dce5;
}

/* 能量条工作状态:主控唤醒→流光点亮；内容进入记忆文件→熄灭（动画口径对齐主窗 dotPulse） */
.box-div-j4npf.energy-active > div {
  animation: dotPulse 1.05s ease-in-out infinite;
}
.box-div-j4npf.energy-active > div:nth-child(1) { animation-delay: 0s; }
.box-div-j4npf.energy-active > div:nth-child(2) { animation-delay: .1s; }
.box-div-j4npf.energy-active > div:nth-child(3) { animation-delay: .2s; }
.box-div-j4npf.energy-active > div:nth-child(4) { animation-delay: .3s; }
.box-div-j4npf.energy-active > div:nth-child(5) { animation-delay: .4s; }
.box-div-j4npf.energy-active > div:nth-child(6) { animation-delay: .5s; }
.box-div-j4npf.energy-active > div:nth-child(7) { animation-delay: .6s; }
.box-div-j4npf.energy-active > div:nth-child(8) { animation-delay: .7s; }
.box-div-j4npf.energy-active > div:nth-child(9) { animation-delay: .8s; }
@keyframes dotPulse {
  0%, 100% { background-color: #d8dce5; transform: scaleY(1); }
  50% { background-color: var(--primary); transform: scaleY(1.18); }
}
</style>
