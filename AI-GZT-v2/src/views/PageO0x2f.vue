<!--
  页面《首页》　路由:/page-o0x2f（pageO0x2f）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
  该页面为首页，router 草稿中作为默认重定向目标。
-->
<template>
  <div class="box-div-8ouzx" :class="{ 'float-mode': isFloat }">
    <div class="box-div-62xqx">
      <div class="box-div-yanfg">
        <img class="box-span-3ttij" src="/assets/icons/logo.png" />
        <span class="box-span-6kcox">AI-GZT</span>
        <button class="box-button-gvyw3" type="button" @click="goPagePageO0x2f()" :class="{ 'lc-nav-active': route.path === '/page-o0x2f' }">主对话</button>
        <button class="box-button-hyhye" type="button" @click="goPage1()" :class="{ 'lc-nav-active': route.path === '/1' }">次级对话</button>
        <button class="box-button-ebs5o" type="button" @click="goPage2()" :class="{ 'lc-nav-active': route.path === '/2' }">仓库</button>
        <button class="box-button-lnrux" type="button" @click="goPage3()" :class="{ 'lc-nav-active': route.path === '/3' }">模型配置</button>
        <button class="box-button-poots" type="button" @click="goPage4()" :class="{ 'lc-nav-active': route.path === '/4' }">系统配置</button>
        <button class="box-button-v4ho7" type="button" @click="goPage5()" :class="{ 'lc-nav-active': route.path === '/5' }">备份</button>
        <button class="box-button-wr90q" type="button" @click="goPage6()" :class="{ 'lc-nav-active': route.path === '/6' }">日志</button>
        <button class="box-button-0ihym" type="button" @click="goPage7()" :class="{ 'lc-nav-active': route.path === '/7' }">任务</button>
        <button class="box-button-zjopk" type="button" @click="goPage8()" :class="{ 'lc-nav-active': route.path === '/8' }">插件</button>
        <button class="box-button-e327z" type="button" @click="goPage9()" :class="{ 'lc-nav-active': route.path === '/9' }">记忆</button>
        <button class="box-button-71sid" type="button" @click="goPage10()" :class="{ 'lc-nav-active': route.path === '/10' }">关于</button>
        <div class="box-div-2uaow">
          <p class="box-p-4xtqa">版本V2.0</p>
        </div>
      </div>
      <div class="box-div-35526">
        <div class="box-div-bk778">
          <div class="box-div-9a58f">
            <div class="box-div-59iim">
              <h2 class="box-h2-l1ula">{{ personaName || '主控' }}</h2>
              <div class="box-div-j3t1o">
                <div class="box-div-7d3d1">
                  <!-- 选择项目下拉框:对齐 web 版 chat_ui.html 的 projectSelector，插在「开启新对话」之后 -->
                  <select class="box-select-644z5" v-model="curProject" @focus="loadProjects" @change="switchProject">
                    <option value="">（全局）请选择项目</option>
                    <option v-for="p in projects" :key="p.project_id || p.project_name" :value="JSON.stringify(p)">{{ p.project_name }}</option>
                  </select>
                </div>
                <!-- 【阶段5-2·M2】点击改走 toggleThinkMode():
                     原 @click="thinkMode = !thinkMode" 只改本地 ref，刷新/重启必回默认 true（无持久化）。
                     新函数 = 本地取反（即时响应）+ 异步 POST /api/config/set 落盘。 -->
                <div class="box-div-mqz2q" @click="toggleThinkMode()" style="cursor:pointer;">
                  <span class="box-span-cbnsx">思考</span>
                  <div class="box-div-7pnux" :class="{ 'think-on': thinkMode }">
                    <div class="box-div-1w4rg"></div>
                  </div>
                </div>
              </div>
            </div>
            <div class="box-div-4w6en">
              <!-- 【显示优化】加 ref 供 scrollToBottom() 拿到滚动容器 DOM，实现新内容自动滚到底部 -->
              <div class="box-div-wvyv4" ref="msgListRef">
                <!-- 阶段5-1（V1 主线口径）:消息流 v-for，任务卡作为 type='task' 条目融流；思考关闭时 think 气泡不渲染 -->
                <template v-for="(m, i) in visibleMessages" :key="i">
                  <div v-if="m.type === 'user'" class="box-div-d1c5j">
                    <span class="box-span-i5aio">我</span>
                    <div class="box-div-dlklc" :class="{ 'msg-folded': m.collapsed }">
                      <span class="box-span-vlxkl">{{ m.content }}</span>
                      <!-- 【附件方案②】用户气泡内直接渲染附件（完全对齐旧页 chat_ui.html L982-993）:
                           图片 → 缩略图，点击新窗打开原图（window.open，与你拍板口径一致，零新组件）；
                           其它 → 文件卡（📄 文件名 + 下载链接）。
                           渲染位置与旧页一致:挂在"消息内容区"内，不是独立消息。 -->
                      <div class="msg-attachments" v-if="m.attachments && m.attachments.length">
                        <template v-for="(a, ai) in m.attachments" :key="ai">
                          <img
                            v-if="a.file_type === 'image'"
                            class="msg-attach-img"
                            :src="a.url"
                            :title="a.original_name"
                            @click="openImage(a.url)"
                          />
                          <div v-else class="msg-attach-file">
                            <span>📄</span>
                            <span class="msg-attach-name">{{ a.original_name }}</span>
                            <a :href="a.url" target="_blank" class="msg-attach-dl">下载</a>
                          </div>
                        </template>
                      </div>
                    </div>
                    <div class="box-div-msgact">
                      <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                      <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                    </div>
                  </div>
                  <div v-else-if="m.type === 'think'" class="box-div-0fxg5">
                    <div class="box-div-248pp">
                      <button class="box-button-7k8i5" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                      <span class="box-span-9q2h1">AI思考过程</span>
                      <button class="box-button-2seb1" type="button" @click="handleCopyThink">⧉</button>
                    </div>
                    <div class="box-div-m1e8x" v-show="!m.collapsed">
                      <span class="box-span-mugyd">{{ m.content }}</span>
                    </div>
                  </div>
                  <div v-else-if="m.type === 'task'" class="box-div-taskcard">
                    <span class="task-id">{{ m.content.task_id }}</span>
                    <span class="task-state" :class="'st-' + m.content.state">{{ m.content.state_name }}</span>
                    <span class="task-rework" v-if="m.content.rework_count > 0">回炉{{ m.content.rework_count }}</span>
                    <button class="btn-task-abort" type="button" @click="handleAbortTask(m.content.task_id)">中止</button>
                  </div>
                  <div v-else-if="m.type === 'secondaryMsg'" class="box-div-e9vp9">
                    <!-- 【头像接入】改传整条消息:m 内同时含 slot（首选）与 role（反查兜底），
                         由 senderIcon() 内部决定切图，模板侧不再只看 role。 -->
                    <img class="box-span-fq7xn" :src="senderIcon(m)" alt="AI" />
                    <!-- 【视觉分层·M1】系统派发 / 次级回报专属 class「msg-sys」:
                         灰底蓝字 + 浅蓝描边，与「用户蓝底白字」「AI 白底描边」三向区分。
                         只挂 secondaryMsg 分支，下方 else 的 AI 分支不挂 → 两类消息彻底分开。
                         类定义见文件末尾 .msg-sys / .msg-sys-text（全部走全局主题令牌）。 -->
                    <div class="box-div-tn7ye msg-sys" :class="{ 'msg-folded': m.collapsed }">
                      <div style="font-size:12px;color:#86909c;margin-bottom:4px;">来自 {{ m.role || '次级' }} 的消息</div>
                      <!-- 折叠态挂「内容容器 div」（与相邻 else AI 气泡口径完全一致，本页此前是全页唯一挂在内容 span 上的气泡）；
                           按钮容器与内容容器同级 → 展开/折叠时按钮位置恒定，与主控其余气泡统一 -->
                      <!-- 【视觉分层·M2】系统派发正文加「msg-sys-text」→ 蓝字（var(--primary)），
                           与灰底构成"灰底蓝字"；下方 AI 分支的 box-span-faprc 不挂，保持深色正文。 -->
                      <span class="box-span-faprc msg-sys-text">{{ m.content }}</span>
                    </div>
                    <div class="box-div-msgact">
                      <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                      <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                    </div>
                  </div>
                  <div v-else class="box-div-e9vp9">
                    <img class="box-span-fq7xn" src="/assets/icons/logo.png" alt="AI" />
                    <div class="box-div-tn7ye" :class="{ 'msg-folded': m.collapsed }">
                      <span class="box-span-faprc">{{ m.content }}</span>
                    </div>
                    <div class="box-div-msgact">
                      <button class="box-button-msgact" type="button" @click="toggleFold(m)">{{ m.collapsed ? '▸' : '▾' }}</button>
                      <button class="box-button-msgact" type="button" @click="handleCopyText(String(m.content || ''))">⧉</button>
                    </div>
                  </div>
                </template>
              </div>
              <div class="box-div-b2oll">
                <!-- 附件预览条:截图 / 上传文件后即时可见 + ✕ 可取消（对齐 chat_ui.html 的 renderAttachments） -->
                <div class="box-div-attach" v-if="attachments.length">
                  <div class="box-attach-item" v-for="(a, i) in attachments" :key="i">
                    <img v-if="a.file_type === 'image'" class="box-attach-thumb" :src="a.url" :alt="a.original_name || '截图'" />
                    <span v-else class="box-attach-name">📄 {{ a.original_name || '文件' }}</span>
                    <button class="box-attach-del" type="button" @click="attachments.splice(i, 1)">×</button>
                  </div>
                </div>
                <div class="box-div-1qfcv">
                  <button class="box-button-3h58p" type="button" @click="handleScreenshot">截图</button>
                  <button class="box-button-qit6d" type="button" @click="handleSendFile">发送文件</button>
                  <!-- 悬浮窗专用:打开工作台（复用旧悬浮窗 local:// 协议拦截，后端零改动） -->
                  <button v-if="isFloat" class="box-button-qit6d" type="button" @click="handleOpenWorkbench">打开工作台</button>
                  <div class="box-div-nkke7" :class="{ 'energy-active': taskActive }">
                    <div class="box-div-z2jyo"></div>
                    <div class="box-div-scpjn"></div>
                    <div class="box-div-7dnug"></div>
                    <div class="box-div-y55zw"></div>
                    <div class="box-div-e930y"></div>
                    <div class="box-div-v0zkl"></div>
                    <div class="box-div-5bh4j"></div>
                    <div class="box-div-lynj2"></div>
                    <div class="box-div-6wvrj"></div>
                  </div>
                </div>
                <div class="box-div-sfe42">
                  <textarea class="box-textarea-6jw94" v-model="chatInput" placeholder="请输入内容……" rows="3"></textarea>
                  <button class="box-button-ery33" type="button" @click="handleChatSend">发送</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// 【人设名展示】读取 9 槽位模型配置:用于取主控（slot=1）的 persona_name 显示在标题区
import { listModels } from '@/api/model'

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

/** 悬浮窗模式:URL 带 ?mode=float 时隐藏外层导航，仅保留对话区（复用同一组件，零代码重复，与主窗天然互通） */
const isFloat = computed<boolean>(() => route.query.mode === 'float')

/** 【思考开关·独立持久化】按实例类型选择持久化字段名:
 *  主对话页(普通实例) → 'show_think_mode'
 *  悬浮窗(?mode=float) → 'show_think_mode_float'
 *  两个实例其实是同一个 PageO0x2f.vue（main.py 用 ?mode=float 加载第二份），
 *  靠 isFloat 分流到各自字段 —— 从而做到"主对话页关 / 悬浮窗开"各自独立、互不覆盖，
 *  彻底消除旧实现"两窗共用 show_think_mode、来回点击互相覆盖"的现象。
 *  setup 顶层 route 已就绪，直接取 .value 得常量（避免把计算属性当对象键名导致取值失败）。 */
const thinkField = isFloat.value ? 'show_think_mode_float' : 'show_think_mode'

/** [AI-FILL] 数据声明:请补全初始值与精确类型 */
const chatInput = ref<string>('')

/** AI思考模式开关（默认开启:仅控制页面是否显示已有思考气泡，不改请求参数——thinking 恒为 true，思考内容照常生成）
 *  【思考开关·独立持久化】值按实例类型分别存储于后端 config.json 的独立字段（由 thinkField 决定）:
 *    · 主对话页（普通实例）  → show_think_mode
 *    · 悬浮窗（?mode=float） → show_think_mode_float
 *    · 次级开发页（1.vue）   → show_think_mode_dev
 *  三处互不同步、互不覆盖 —— 可"主对话页关 + 悬浮窗开 + 开发页开"三态并存，
 *  各自刷新 / 重启工作台均保持自己的状态（彻底消除旧实现共用一个字段导致的状态互相覆盖）。 */
const thinkMode = ref<boolean>(true)

/** 实际渲染的消息列表:思考模式关闭时过滤掉所有 think 类型（原数据不丢，重新开启即还原） */
const visibleMessages = computed(() => (thinkMode.value ? messages.value : messages.value.filter((m) => m.type !== 'think')))

/** 【阶段5-2】读取后端持久化的思考开关状态（复用 GET /api/config/get，不新建接口）:
 *  兼容两种返回形态（{code,data:{config:{...}}} 与 {code,data:{...}}）；
 *  非 boolean 一律保持默认 true（老配置缺失无感，与 api_server.py load_config 默认值兜底一致）。 */
async function loadThinkMode() {
  try {
    const res = await fetch('/api/config/get')
    const data = await res.json()
    const cfg = data?.data?.config ?? data?.data ?? {}
    // 【思考开关·独立持久化】按 thinkField 读取"本实例对应"的字段:
    //  主对话页读 show_think_mode、悬浮窗读 show_think_mode_float（各读各的，互不干扰）
    if (typeof cfg[thinkField] === 'boolean') thinkMode.value = cfg[thinkField]
  } catch (e) {
    console.warn('[thinkMode] 读取持久化状态失败，保持默认开启:', e)
  }
}

/** 【阶段5-2】点击开关:先本地取反（即时响应，不等网络），再异步落盘。
 *  后端 /api/config/set 为深合并语义（load_config → old_config.update(request.config) → save_config），
 *  因此只传 show_think_mode 这 1 个字段，不会覆盖用户 config.json 其余 40+ 项配置。 */
async function toggleThinkMode() {
  thinkMode.value = !thinkMode.value
  try {
    await fetch('/api/config/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // 【思考开关·独立持久化】按 thinkField 写入"本实例对应"的字段（只传 1 个字段:
      //  后端 /api/config/set 是深合并语义 old_config.update(request.config)，不会覆盖用户其余 40+ 项配置）
      body: JSON.stringify({ config: { [thinkField]: thinkMode.value } }),
    })
  } catch (e) {
    console.warn('[thinkMode] 保存状态失败（本地已生效，下次刷新可能回退）:', e)
  }
}

/** 【人设名展示】主控模型（slot=1）的 persona_name，用于标题区动态显示。
 *  读取失败或为空时保持空串，模板侧用 || 兜底显示"主控"（与项目"主控/次级"术语一致）。
 *  数据源:listModels()（脱敏，不含 api_key），比 getModel(1) 更安全。 */
const personaName = ref<string>('')

/** 【头像接入·反查缓存】全量模型列表缓存（含 slot / persona_name），供 senderIcon() 做
 *  role → slot 反查兜底（改造前已落盘的老消息无 slot 字段时用）；加载失败保持空数组，不影响主流程。 */
const modelListCache = ref<any[]>([])

/** 【人设名展示】异步读取主控（slot=1）人设名，挂载时调用一次；失败不影响主流程 */
async function loadPersonaName() {
  try {
    const list = await listModels()
    // 【头像接入】顺路缓存全量列表（零新增网络请求）—— senderIcon() 的 role → slot 反查数据源
    modelListCache.value = Array.isArray(list) ? list : []
    const main = list.find((m) => m.slot === 1)
    if (main && main.persona_name) personaName.value = String(main.persona_name).trim()
  } catch (e) {
    console.warn('[personaName] 读取主控人设名失败，保持兜底文案:', e)
  }
}

/** 能量条任务进行中标志（Q3甲:由 SSE 的 task_active 事件驱动蓝色流光） */
const taskActive = ref<boolean>(false)

/** 当前会话ID（同时作为消息持久化键:chat_<session_id>） */
const sessionId = ref<string>('default')
/** 【修复·核心变量】messages.value 当前实际归属的项目名:落盘一律以它为准，不用动态求值的 currentProjectName()。
 *  原因:切项目时 v-model / storage 事件会先把 curProject 改成新项目，若落盘时动态求值，
 *  待落盘的那批消息（含刚发出的用户消息）会被写进「新项目 key」→ 旧项目下从未写入 → 切回来就消失。
 *  取值时机:loadProjectMessages() 加载前同步更新，与 messages.value 的实际归属严格一致。*/
let loadedProjectName = 'default'
/** ===== 项目维度缓存键:chat_<当前项目名>（切项目 → 对话区干净切换） ===== */
function currentProjectName(): string {
  if (!curProject.value) return 'default'
  try { return JSON.parse(curProject.value).project_name || 'default' } catch { return 'default' }
}
function chatCacheKey(): string {
  return 'chat_' + currentProjectName()
}
/** 落盘裁剪:按"完整 user→ai 对话对"从尾部整轮截断，防止 localStorage 无限膨胀；内存显示不受影响。
 *  A3修复:上限由 60 放宽到 200，避免长对话回溯时历史内容从持久化缓存被真删。
 *  R4 修复·根因级:旧实现是 `list.slice(list.length - N)` —— 按"总条数"从尾部一刀切，
 *  一旦刀口落在某轮中间，就会把该轮的 user 提问砍掉、只留下 think/ai，
 *  用户看到的就是"中间我发出的内容消失"（残缺轮次）。
 *  现改为:先定位到距尾部 N 条以内、且是"轮次起点（type==='user'）"的位置，
 *  整轮裁剪 —— 保证落盘的历史永远是完整的 user→ai 对，绝不出现孤儿气泡。 */
const PERSIST_MAX_MSGS = 200
function trimForPersist(): any[] {
  const list = messages.value
  if (list.length <= PERSIST_MAX_MSGS) return list
  // 目标切点:尾部保留满 PERSIST_MAX_MSGS 条的起点
  let cutIdx = list.length - PERSIST_MAX_MSGS
  // 从切点向前回溯到最近的 user 边界（保证起点是完整轮的开头，不砍轮中间）
  // 极端情况（前 PERSIST_MAX_MSGS 条内一条 user 都没有）→ cutIdx 回退到 0，返回全部，宁多不少
  while (cutIdx > 0 && list[cutIdx] && list[cutIdx].type !== 'user') cutIdx--
  return list.slice(cutIdx)
}

/** 选择项目下拉:项目列表 + 当前选中项（JSON 字符串，对齐 chat_ui.html 口径） */
interface ProjItem { project_id?: string; project_name: string; project_root?: string; manual_path?: string }
const projects = ref<ProjItem[]>([])
const curProject = ref<string>('')

/** 【修复·下拉框回显】判断 localStorage 中的项目串是否代表「（全局）」:
 *  · null / 空串 → 是（从未选过 / 选过全局）
 *  · switchProject 未选具体项目时兜底写入的 { project_name:'default' } 对象串 → 是
 *  · 解析异常 → 否（保守当作具体项目，不误伤）
 *  为什么需要:模板里「（全局）」option 的 value 是空串，而写入端存的是 default 对象串，
 *  单靠字符串比较读回时匹配不到任何 option → 下拉框显示空白（实测 bug:选全局后切页回来变空选）。*/
function isGlobalProjectStr(sp: string | null): boolean {
  if (!sp) return true
  try {
    const obj = JSON.parse(sp)
    return !obj || !obj.project_name || obj.project_name === 'default'
  } catch {
    return false
  }
}

/** 附件数组（截图 / 上传文件共用，随 handleChatSend 的 body 一起提交） */
const attachments = ref<any[]>([])

/** [AI-FILL] change 事件:切换历史会话后拉取对应记录 */
function handleChatGroupChange() {
  // TODO: 补全业务逻辑
}

/** [AI-FILL] click 事件:开启新对话（清空上下文 / 新建会话） */
function handleNewChat() {
  // TODO: 补全业务逻辑
}

/** click 事件:打开工作台（悬浮窗专用，复用旧悬浮窗 chat_float.html 的 local:// 协议拦截，后端零改动） */
function handleOpenWorkbench() {
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = 'local://open-ai-workbench'
  document.body.appendChild(iframe)
  setTimeout(() => document.body.removeChild(iframe), 100)
}

/** [AI-FILL] click 事件:复制思考内容 */
function handleCopyThink() {
  // 提示: 使用 navigator.clipboard.writeText(要复制的内容) 实现复制
  // TODO: 补全业务逻辑
}

/** click 事件:截图（照搬 chat_ui.html 的 /api/screenshot/trigger 口径，结果入附件数组） */
async function handleScreenshot() {
  try {
    const res = await fetch('/api/screenshot/trigger', { method: 'POST' })
    const data = await res.json()
    if (data.code === 200) {
      attachments.value.push(data.data)
      // 【附件方案②】已删除原提示消息「已添加截图附件（共 N 个），将随下一条消息提交。」:
      //  对齐旧页 chat_ui.html 口径 —— 附件只出现在"底部预览条 + 用户消息气泡内"，
      //  不再单独冒一条无意义的系统消息污染对话流（用户原话:"这个是没有意义的"）。
    } else if (data.code !== 400) {
      messages.value.push({ type: 'ai', content: `截图失败:${data.msg || ''}` })
    }
  } catch (e) {
    messages.value.push({ type: 'ai', content: `截图失败:${e}` })
  }
}

/** click 事件:上传文件（隐藏 input 触发 → 通用上传接口 → 入附件数组） */
function handleSendFile() {
  const el = document.createElement('input')
  el.type = 'file'
  el.multiple = true
  el.accept = 'image/*,.pdf,.docx,.xlsx,.txt,.md,.json,.zip'
  el.onchange = async () => {
    const files = el.files
    if (!files || !files.length) return
    for (const f of Array.from(files)) {
      try {
        const fd = new FormData()
        fd.append('file', f)
        const res = await fetch('/api/chat/upload_file', { method: 'POST', body: fd })
        const data = await res.json()
        if (data.code === 200) attachments.value.push(data.data)
        else messages.value.push({ type: 'ai', content: `上传失败:${data.msg || ''}` })
      } catch (e) {
        messages.value.push({ type: 'ai', content: `上传失败:${e}` })
      }
    }
    // 【附件方案②】已删除原提示消息「附件已就绪（共 N 个），将随下一条消息提交。」
    //  与截图路径同一口径:附件只在预览条与用户气泡内呈现，不再单独冒系统消息。
  }
  el.click()
}

/** 消息流条目:user（用户）/ ai（主模型回复，含工具调用原文）/ think（思考过程）/ task（任务卡，融流）/ secondaryMsg（次级模型 @主控 时主对话页展示"来自 XX 的消息"） */
interface ChatMsg {
  type: 'user' | 'ai' | 'think' | 'task' | 'secondaryMsg'
  content: any
  /** 次级消息来源（type=secondaryMsg 时用于渲染"来自 XX 的消息"标签） */
  role?: string
  /** 气泡折叠态（每个气泡可独立展开/收起，对齐原版 msg-toggle-btn） */
  collapsed?: boolean
  /** 【显示优化】用户是否手动开合过该气泡:
   *  一旦为 true，updateFoldStates() 的自动折叠规则永久跳过它，
   *  保证「用户手动展开的优先级 > 自动折叠」，避免用户正在查看时被自动折叠。（仅前端内存字段，不落盘）*/
  userTouched?: boolean
  /** 【附件方案②】用户消息随带的本轮附件快照（发送时的浅拷贝数组）:
   *  用于在用户气泡内直接渲染图片缩略图 / 文件卡，
   *  与旧页 chat_ui.html 的 addMessage(role, content, memoryCount, attachments) 语义完全一致。 */
  attachments?: any[]
}


/**
 * 次级消息气泡图标 —— 按来源模型槽位切图（slot 2~9 各自头像）
 *
 * 【2026-10-13 头像接入】三级优先级:
 *   ① 首选 slot:消息自带 slot（后端 secondary_to_main payload 透传）→ /assets/avatars/model_{slot}.png;
 *   ② 兜底反查:老消息无 slot → 用 role（人设名）在 modelListCache 反查 slot，命中同 ① ;
 *   ③ 最终兜底:主控气泡 / role 为空 / 反查失败 → 保持原 logo.png（渲染不退化）。
 * 资源目录:AI-GZT-v2/public/assets/avatars/（构建自动拷入 dist，打包无需改动）。
 */
function senderIcon(m: any): string {
  // ① 首选:消息自带 slot（本次改造后所有新消息都有）
  const slot = Number((m && m.slot) || 0)
  if (slot >= 2 && slot <= 9) return `/assets/avatars/model_${slot}.png`
  // ② 兜底:历史老消息无 slot → 用 role 反查全量模型列表（仅 slot 2~9 范围有效）
  const role = String((m && m.role) || '').trim()
  if (role && role !== '次级') {
    const hit = modelListCache.value.find(
      (x: any) => String(x.persona_name || '').trim() === role
    )
    const s = Number((hit && hit.slot) || 0)
    if (s >= 2 && s <= 9) return `/assets/avatars/model_${s}.png`
  }
  // ③ 最终兜底:主控气泡 / role 为空 / 反查失败 → 保持原样 logo.png
  return '/assets/icons/logo.png'
}

/** 消息流数组 —— 5 类条目按发生顺序排列，任务卡随对话滚动、状态原地刷新 */
const messages = ref<ChatMsg[]>([])

/** 任务卡 upsert:同 task_id 只原地刷新状态，不重复插卡（对齐 V1「随对话滚动、状态原地刷新」） */
function upsertTaskCard(t: any) {
  const idx = messages.value.findIndex((m) => m.type === 'task' && m.content.task_id === t.task_id)
  const card: ChatMsg = { type: 'task', content: t }
  if (idx >= 0) messages.value[idx] = card
  else messages.value.push(card)
}

/** [AI-FILL] click 事件:发送对话内容（普通对话发送 —— 无任何提交语义，派发由主模型输出触发） */
async function handleChatSend() {
  const text = String(chatInput.value || '').trim()
  if (!text) return
  // 【附件方案②】用户消息随带附件快照（必须浅拷贝 [...attachments.value]）:
  //  否则本轮末尾 `attachments.value = []` 会把消息内持有的同一数组引用一并清空 → 气泡里渲染不出附件。
  messages.value.push({ type: 'user', content: text, attachments: [...attachments.value] })
  // 【修复①·用户消息立即落盘】:用户消息此前只在 AI 终态（SSE ai_output / error）才落盘，
  //  AI 未回复就切页 / 切项目 / 关窗 → 用户消息内存一丢就没了（实测"我的输出消失"）。
  //  这里 push 后立即落盘（localStorage chat_{当前项目} + 后端 sessions/chat_{当前项目}.json），
  //  与 AI 消息享有同等持久化待遇，不再等 AI 回复。
  persistMessages()
  // 【R3 修复·根因级，对齐旧前端 chat_ui.html 的 addMessage('user',...) 语义】
  // 用户发消息 = 显式进入新一轮:立即置空本轮 think/ai 指针，
  // 保证新一轮的 ai_reasoning / ai_output_stream 一定落到新气泡上，而不是被追加到上一轮。
  // 这是"思考合并 / 输出合并"的正面分轮机制（R1 的终态置空是反面分轮，两者互补成闭环）。
  // 同时调用一次兜底函数 ensureRoundLandmarks():该函数已降级为兜底（不再是唯一判据），
  // 但保留调用可覆盖"后端未推终态事件"等异常路径。
  roundThinkMsg = null
  roundAiMsg = null
  ensureRoundLandmarks()
  chatInput.value = ''
  // Q3甲:发送即进入「任务进行中」→ 能量条流光（结束时由 SSE 的 memory_saved / error 熄灭）
  taskActive.value = true
  streamedThisTurn.value = false // C 修复:重置本轮流式标记，供 SSE / fetch 兜底互斥
  try {
    // 请求体字段名必须与后端 ChatRequest 对齐:query / session_id / thinking / attachments
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: text,
        session_id: sessionId.value,
        thinking: true, // 思考模式开关仅控制显示:请求恒带思考，关闭开关也不截断思考输出的生成
        attachments: attachments.value,
        model_slot: 1, // 主对话固定用「模型1」（系统自动，用户无感）:后端按该槽位读 models_config.json 的人设/3固定提示/温度/回复上限/api_url/model_name/api_key
      }),
    })
    if (!resp.ok) {
      // 错误可见化:HTTP 非 2xx（422 字段不符 / 500 等）→ 把状态与 detail 打进消息流，杜绝"静默无响应"
      let detail = ''
      try { detail = JSON.stringify(await resp.json()) } catch { detail = '' }
      messages.value.push({ type: 'ai', content: `请求失败:HTTP ${resp.status} ${detail}` })
      // 请求级异常兜底熄灭（正常轮由 SSE 的 memory_saved 熄灭）
      taskActive.value = false
      return
    }
    const data = await resp.json()
    // C 修复:SSE 已流式直显过内容 → 不再 push 最终轮（避免顶掉/重复）；仅当 SSE 无内容时兜底
    if (!streamedThisTurn.value) {
      messages.value.push({ type: 'ai', content: data?.response ?? '（无响应）' })
    }
    // 附件随本次请求一并提交完成，清空
    attachments.value = []
  } catch (e) {
    messages.value.push({ type: 'ai', content: `请求失败:${e}` })
    // 请求级异常兜底熄灭（正常轮由 SSE 的 memory_saved 熄灭，对齐原文件 chat_ui.html）
    taskActive.value = false
  }
}

/** 任务卡「中止」按钮:通知后端中止该任务 */
async function handleAbortTask(taskId: string) {
  try {
    await fetch('/api/orch/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId }),
    })
  } catch (e) {
    console.error('[abort] 中止请求失败（已忽略）:', e)
  }
}

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPagePageO0x2f() {
  router.push('/page-o0x2f')
}

function goPage1() {
  router.push('/1')
}

function goPage2() {
  router.push('/2')
}

function goPage3() {
  router.push('/3')
}

function goPage4() {
  router.push('/4')
}

function goPage5() {
  router.push('/5')
}

function goPage6() {
  router.push('/6')
}

function goPage7() {
  router.push('/7')
}

function goPage8() {
  router.push('/8')
}

function goPage9() {
  router.push('/9')
}

function goPage10() {
  router.push('/10')
}

/** ===== 选择项目:加载列表（照搬 chat_ui.html 的 loadProjectList） ===== */
async function loadProjects() {
  try {
    const res = await fetch('/api/project/list')
    const data = await res.json()
    if (data.code === 200) {
      const selected = curProject.value
      projects.value = data.data || []
      if (selected) curProject.value = selected
    }
  } catch (e) {
    console.error('[project] 列表加载失败:', e)
  }
}

/** ===== 选择项目:切换项目（照搬 chat_ui.html 的 switchProject，含 localStorage 跨页同步） ===== */
async function switchProject() {
  const sel = curProject.value
  // 【修复②·切项目前先落盘】:此刻 loadedProjectName 仍是「旧项目」，
  //  persistMessages() 会把当前 messages（含刚发出的用户消息）完整写入旧项目缓存，并清掉待执行的防抖定时器。
  //  不先落盘的话，紧接着 loadProjectMessages() 会整体替换 messages.value，
  //  旧项目那条用户消息从未被写过 → 切回来就消失（实测现象）。
  persistMessages()
  try {
    const proj = sel ? JSON.parse(sel) : { project_name: 'default', project_root: '', manual_path: '' }
    const res = await fetch('/api/project/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(proj),
    })
    const data = await res.json()
    if (data.code === 200) {
      localStorage.setItem('current_selected_project', JSON.stringify(proj))
      curProject.value = sel
      // 切项目 → 载入新项目消息缓存（旧项目已由 watch 自动落盘，无需手动保存）
      loadProjectMessages()
    }
  } catch (e) {
    console.error('[project] 切换失败:', e)
  }
}

/** ===== Q2甲:消息持久化（按 session_id 落 localStorage，切页 / 刷新不丢） ===== */
let persistTimer: any = null
/** 【显示优化】消息流滚动容器 DOM 引用（模板 .box-div-wvyv4）——用于自动滚动到底部 */
const msgListRef = ref<HTMLElement | null>(null)
/** 【显示优化】自动滚动到底部:
 *  · force = false（默认）:仅当用户"已在底部附近"时才跟随滚动——用户正在向上翻阅历史时不打断阅读；
 *  · force = true:无条件滚到底部，用于"首屏历史加载完 / 用户主动发送消息 / 跨窗补插消息"等确定要看的时刻。*/
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
/** 智能折叠:记录上一条消息条数，仅在「新气泡出现」时同步折叠态，避免每帧重排 */
let lastMsgCount = 0
/** 立即落盘（流结束 / 卸载时调用，保证不丢）；同时清掉待执行的防抖定时器
 *  落盘 key 用 loadedProjectName（当前已加载项目），不用动态的 chatCacheKey():
 *  切项目瞬间 curProject 已变新项目，动态求值会把旧项目消息误写进新项目 key。*/
function persistMessages() {
  if (persistTimer) { clearTimeout(persistTimer); persistTimer = null }
  try { localStorage.setItem('chat_' + loadedProjectName, JSON.stringify(trimForPersist())) } catch {}
  persistMessagesToBackend()
}
/** 方案A:同时落盘到后端（与 origin/端口解耦，重启后可回读）；fire-and-forget，失败静默不影响 UI */
function persistMessagesToBackend() {
  try {
    fetch('/api/chat/history/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: loadedProjectName, messages: trimForPersist() }),
    }).catch(() => {})
  } catch {}
}
/** 载入当前项目的消息缓存（切项目 / 挂载时调用）:localStorage 优先，为空则从后端回读（治本:端口变化/换浏览器 origin 隔离） */
async function loadProjectMessages() {
  // 【配套】加载前先锁定本次归属项目名:此后落盘（persistMessages）一律以它为准，
  //  与即将替换进 messages.value 的内容严格同源，杜绝"写进别的项目 key"。
  loadedProjectName = currentProjectName()
  try {
    const raw = localStorage.getItem(chatCacheKey())
    const saved = raw ? JSON.parse(raw) : []
    messages.value = Array.isArray(saved) ? saved : []
  } catch { messages.value = [] }
  // 【R5 修复·根因级】本地缓存恢复会"整体替换" messages.value:
  // roundThinkMsg / roundAiMsg 指向的是旧数组里的对象，替换后这两个引用就成了
  // "已不在渲染数组里的幽灵对象" → 后续 SSE 增量 append 到幽灵对象 → UI 冻住不动 →
  // 切页/刷新才从新数组读到内容（用户实测:停在次级页不刷新、切页才蹦出来）。
  // 这里在替换后立即复位，是防幽灵引用的最后一道保险。
  roundThinkMsg = null
  roundAiMsg = null
  if (messages.value.length === 0) {
    try {
      const res = await fetch(`/api/chat/history/load?project=${encodeURIComponent(currentProjectName())}`)
      const j = await res.json()
      if (j && j.code === 200 && Array.isArray(j.data)) messages.value = j.data
    } catch {}
    // 【R5 修复·根因级】后端回读同样"整体替换" messages.value → 同样复位本轮指针（防幽灵引用）。
    roundThinkMsg = null
    roundAiMsg = null
  }
  lastMsgCount = messages.value.length
  updateFoldStates()
  // 【显示优化】历史/缓存加载完毕 → 强制滚到底部（首屏打开、切项目重载后都能立刻看到最新内容）
  scrollToBottom(true)
}
/** 智能折叠状态同步:最新一条展开，其余历史消息折叠（思考内容同样参与折叠，对齐旧版 chat_ui.html updateMessageFoldStates） */
function updateFoldStates() {
  const list = messages.value
  if (list.length === 0) return
  list.forEach((m, i) => {
    if (m.type === 'task') return // 任务卡不参与折叠
    // 【显示优化】用户手动开合过的气泡永久跳过自动规则（手动优先级 > 自动折叠）:
    //  原实现是无条件覆盖，只能靠"少调用本函数"来规避"用户点击被重置"，
    //  有了本行保护后可放心把触发条件放宽到"任意新增气泡"。
    if (m.userTouched) return
    m.collapsed = i !== list.length - 1
  })
}
/** 防抖落盘:流式输出每帧都改 messages 触发本 watch，改为 400ms 合并一次，
 *  避免"每帧一次全量 JSON.stringify + 同步写盘"阻塞主线程导致的点击延迟 */
watch(messages, () => {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    // 与 persistMessages 同源:防抖落盘也用 loadedProjectName，防切项目瞬间写错 key
    try { localStorage.setItem('chat_' + loadedProjectName, JSON.stringify(trimForPersist())) } catch {}
    persistMessagesToBackend()
    persistTimer = null
  }, 400)
  // 【显示优化】任意"新增气泡"都同步折叠态 + 自动滚底（think / ai / 次级消息的流式新增同样触发）:
  //  原 A2 修复刻意收窄到"仅用户消息"是为规避"用户手动展开被自动折叠重置"；
  //  现 updateFoldStates() 已跳过 userTouched 气泡，该顾虑从根上消除，故放开触发条件。
  if (messages.value.length !== lastMsgCount) {
    const lastType = messages.value[messages.value.length - 1]?.type
    lastMsgCount = messages.value.length
    updateFoldStates()
    // 用户主动发消息 → 强制滚底；AI 流式新增 → 智能跟随（用户正在上翻时不打断）
    scrollToBottom(lastType === 'user')
  }
}, { deep: true })

/** ===== Q3甲:能量条状态机（SSE task_active → 蓝色流光；memory_saved / error → 熄灭） ===== */
let es: EventSource | null = null

/** 修复:SSE 健壮性（对齐 chat_ui.html）——看门狗 / 重连 / 帧节流 状态 */
let reconnectCount = 0
const MAX_RECONNECT = 5
let lastEventAt = Date.now()
let reconnectTimer: any = null
let watchdogTimer: any = null
const WATCHDOG_TIMEOUT = 45000
const WATCHDOG_CHECK = 10000
/** 帧节流缓冲:每帧最多提交一次，避免高频分片引发大量渲染 */
let pendingThink = ''
let pendingStream = ''
let domUpdateScheduled = false
/** 帧节流句柄:requestAnimationFrame 返回的 number（供 cancelAnimationFrame 正确取消） */
let rafId = 0

/** C 修复:本轮是否已收到 SSE 流式内容（决定 fetch 返回后是否还需兜底 push 最终轮） */
const streamedThisTurn = ref(false)

/** A1修复:本轮 think/ai 气泡引用（各仅一条），避免"思考/正文交替到达"被切成多气泡；新一轮由用户消息触发重置 */
let roundThinkMsg: any = null
let roundAiMsg: any = null
/** 【R2 已降级为兜底】最后一条为用户消息则视为进入新一轮，重置本轮气泡引用。
 *  为什么降级:R1/R3 已用"终态事件(ai_output / error)显式置空 + user push 立即置空"
 *  作为分轮的权威机制（对齐旧前端 chat_ui.html 的 currentReasoningMsg / currentStreamMsg 置 null），
 *  本函数只在如下场景作为兜底保险:
 *    · 后端某路径未推送终态事件（异常降级路径）
 *    · 用户消息 push 后未走到 R3 的显式置空（异常路径兜底）
 *  注意:本函数不再作为分轮的唯一判据 —— "末条类型"判据一旦被数组整体替换 / 裁剪打断就会失效，
 *  这正是批次 A 引入"思考合并 / 输出合并"的直接原因，切勿回退为唯一判据。 */
function ensureRoundLandmarks() {
  const last = messages.value[messages.value.length - 1]
  if (!last || last.type === 'user') { roundThinkMsg = null; roundAiMsg = null }
}

/** 思考内容增量追加:同一轮内续写最后一条思考气泡（无则新开），默认展开。
 *  【R2b】不再调用 ensureRoundLandmarks() 分轮:分轮已由 R1（终态事件置空）+ R3（user push 置空）权威保证，
 *  本函数无条件按 roundThinkMsg 指针落点，指针失效时自然新开一条气泡（异常路径也有兜底）。 */
function appendThink(text: string) {
  if (!text) return
  if (roundThinkMsg && messages.value.includes(roundThinkMsg)) {
    roundThinkMsg.content = String(roundThinkMsg.content || '') + text
  } else {
    messages.value.push({ type: 'think', content: text })
    roundThinkMsg = messages.value[messages.value.length - 1]
  }
}

/** AI 正式回复流式直显（对齐原版 ai_output_stream 口径）:
 *  完全照搬后端原文 —— 不再做任何摘要/截断，工具调用文本随正文一起呈现。
 *  兼容两种后端口径:增量 delta（追加）/ 累积 full（以旧串为前缀时覆盖），杜绝重复。 */
function appendAiOutput(text: string) {
  if (!text) return
  // C 修复:标记本轮已有流式内容 → fetch 返回后不再 push 最终轮，避免重复/顶替
  streamedThisTurn.value = true
  // 【R2c】不再调用 ensureRoundLandmarks() 分轮:分轮已由 R1（终态事件置空）+ R3（user push 置空）权威保证。
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

/** 方案A:切页/重连后从后端拉取本轮输出快照，按 query 找回对应问答对，实时补齐断线期间丢弃的流式增量。
 *  仅当现有气泡内容比快照短时才以快照覆盖（保护正常流式已渲染的更多内容）；快照为空或未done也可用（实时累积）。 */
async function syncLastOutput() {
  try {
    const resp = await fetch('/api/chat/last_output/' + sessionId.value)
    if (!resp.ok) return
    const payload = await resp.json()
    const snap = payload && payload.data
    if (!snap || !snap.query) return
    const q = String(snap.query)
    // 从后往前找最后一条匹配 query 的 user 消息
    let userIdx = -1
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.type === 'user' && String(m.content) === q) { userIdx = i; break }
    }
    if (userIdx < 0) return
    const reasoning = String(snap.reasoning || '')
    const output = String(snap.output || '')
    // 补齐思考气泡:现有内容更短则以快照覆盖（补齐缺口），不存在则新建在 user 之后
    if (reasoning) {
      let thinkMsg: ChatMsg | null = null
      for (let i = userIdx + 1; i < messages.value.length; i++) {
        if (messages.value[i].type === 'think') { thinkMsg = messages.value[i]; break }
      }
      if (thinkMsg) {
        if (String(thinkMsg.content || '').length < reasoning.length) thinkMsg.content = reasoning
      } else {
        messages.value.splice(userIdx + 1, 0, { type: 'think', content: reasoning })
      }
    }
    // 补齐正文气泡:同口径，从 user 之后倒序找最后一条 ai
    if (output) {
      let aiMsg: ChatMsg | null = null
      for (let i = messages.value.length - 1; i > userIdx; i--) {
        if (messages.value[i].type === 'ai') { aiMsg = messages.value[i]; break }
      }
      if (aiMsg) {
        // 【M5·二级守卫】覆盖条件收紧:快照需"更长 且 现气泡内容是快照前缀"才整段补齐。
        //   背景:后端快照若仍带跨轮累积，会出现 output = "气泡1+气泡2" 而 cur = "气泡2"，
        //   旧逻辑仅比长度就会把气泡2整段顶替成"气泡1+气泡2"（视觉累积）。
        //   cur 为空时 startsWith('') 恒为真 → 不影响"断线期间前端无内容、需按快照补齐"的正常场景。
        const cur = String(aiMsg.content || '')
        if (output.length > cur.length && output.startsWith(cur)) aiMsg.content = output
      } else {
        messages.value.push({ type: 'ai', content: output })
      }
    }
    // 对齐旧版 chat_ui.html:快照已完成(done) 且能量柱仍在流动 → 复位熄灭（重连/切页补齐后同步关灯，避免能量柱卡死）
    if (snap.done === true && taskActive.value) taskActive.value = false
    // 补齐后立即落盘一次，保证切页往返不回放
    persistMessages()
  } catch (e) {
    console.error('[sync] 补齐本轮输出失败（已忽略）:', e)
  }
}

/** ===== SSE 健壮性（对齐 chat_ui.html）:帧节流 / 看门狗 / 重连 ===== */
/** 帧节流刷新:把缓冲的思考/正文增量每帧提交一次，避免高频分片导致大量重排 */
function flushDomUpdates() {
  domUpdateScheduled = false
  rafId = 0
  if (pendingThink) { appendThink(pendingThink); pendingThink = '' }
  if (pendingStream) { appendAiOutput(pendingStream); pendingStream = '' }
}

/** 心跳看门狗:45秒无任何消息判连接僵死（浏览器不触发 onerror），主动关闭并重连 */
function startWatchdog() {
  stopWatchdog()
  watchdogTimer = setInterval(() => {
    if (es && es.readyState === EventSource.OPEN && Date.now() - lastEventAt > WATCHDOG_TIMEOUT) {
      console.warn('[SSE] 心跳看门狗:45秒无消息，判定连接僵死，主动重连')
      lastEventAt = Date.now()
      reconnectSSE()
    }
  }, WATCHDOG_CHECK)
}
function stopWatchdog() {
  if (watchdogTimer) { clearInterval(watchdogTimer); watchdogTimer = null }
}

/** 统一重连:指数退避1/2/3/4/5秒，连续5次失败停止（网络恢复自动重试，不刷新页面、不丢对话） */
function reconnectSSE() {
  try { if (es) es.close() } catch {}
  if (reconnectCount >= MAX_RECONNECT) {
    console.error('[SSE] 连续5次重连失败，停止重连；网络恢复后将自动重试')
    // 对齐旧版 chat_ui.html:重连彻底失败 → 强制熄灭能量柱，避免永久流动卡死
    taskActive.value = false
    return
  }
  reconnectCount++
  if (reconnectTimer) clearTimeout(reconnectTimer)
  reconnectTimer = setTimeout(connectStatusSSE, 1000 * reconnectCount)
}

/** 页面重新可见 / 网络恢复时，若连接已关闭则主动重连 */
function onVisibilityChange() {
  if (document.visibilityState === 'visible' && (!es || es.readyState === EventSource.CLOSED)) reconnectSSE()
}
function onNetworkOnline() {
  reconnectCount = 0
  reconnectSSE()
}

/** 气泡折叠切换（对齐原版 msg-toggle-btn） */
function toggleFold(m: any) {
  m.collapsed = !m.collapsed
  // 【显示优化】打"用户手动开合过"标记 → updateFoldStates() 此后永久跳过它，
  //  即使用户正在展开阅读时又有新内容进来，也不会被自动折叠重置。（think 气泡同样走本函数）
  m.userTouched = true
}

/** 复制文本到剪贴板（对齐原版 handleCopy:clipboard 优先，execCommand 兜底，全环境兼容） */
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

/** 【附件方案②·F1】点击缩略图 → 新标签页打开原图（对齐旧页 chat_ui.html 的 window.open 口径，零新组件）。
 *  为什么必须抽成方法、而不是在模板里直接写 window.open:
 *  Vue 3 模板表达式的作用域是"组件渲染上下文"（即 setup 暴露的绑定），而 window 属于浏览器全局对象、
 *  不在该上下文内 → vue-tsc 类型检查会直接报 TS2339
 *  （Property 'window' does not exist on type 'CreateComponentPublicInstanceWithMixins<...>'），
 *  导致 npm run build 卡在 `vue-tsc --noEmit` 这一步（vite build 根本跑不到）。
 *  抽到 <script setup> 作用域后，函数体内访问全局 window 完全合法，模板只调用实例方法（类型可知）。 */
function openImage(url: string) {
  if (!url) return
  window.open(url, '_blank')
}

function connectStatusSSE() {
  try {
    es = new EventSource('/api/chat/stream/' + sessionId.value)
    // 连接建立（含重连成功）:重置退避计数、刷新时间戳并启动心跳看门狗
    es.onopen = () => {
      reconnectCount = 0
      lastEventAt = Date.now()
      startWatchdog()
      console.log('[SSE] connected')
      // 对齐旧版 chat_ui.html:重连成功后兜底查询断线期间任务是否已结束，补齐流式缺口并复位能量柱
      syncLastOutput()
    }
    es.onerror = (e) => {
      console.error('[SSE] error，触发重连', e)
      reconnectSSE()
    }
    es.onmessage = (ev) => {
      try {
        let raw = String(ev.data || '').trim()
        // data: 前缀防御:某些网关会给已解析数据再加 data: 前缀（对齐 chat_ui.html）
        if (raw.startsWith('data: ')) raw = raw.slice(6).trim()
        if (!raw) return
        const msg = JSON.parse(raw)
        lastEventAt = Date.now() // 收到任意消息都刷新看门狗时间戳（含心跳）
        if (msg.type === 'heartbeat') {
          reconnectCount = 0
          return
        }
        if (msg.type === 'task_active') {
          taskActive.value = !!msg.active
        } else if (msg.type === 'ai_reasoning') {
          // 思考流:入帧节流缓冲，同一帧内合并提交，避免高频重排
          pendingThink += String(msg.content || '')
          if (!domUpdateScheduled) { domUpdateScheduled = true; rafId = requestAnimationFrame(flushDomUpdates) }
        } else if (msg.type === 'ai_output_stream') {
          // AI 正式回复流式:入帧节流缓冲，原文直显
          pendingStream += String(msg.content ?? msg.text ?? '')
          if (!domUpdateScheduled) { domUpdateScheduled = true; rafId = requestAnimationFrame(flushDomUpdates) }
        } else if (msg.type === 'ai_output' || msg.type === 'error') {
          // 流结束:先渲染残留分片，避免最后分片丢失
          if (rafId) { cancelAnimationFrame(rafId); rafId = 0 }
          if (domUpdateScheduled || pendingThink || pendingStream) {
            flushDomUpdates()
          }
          if (msg.type === 'ai_output') {
            // 兜底:若本轮未收到任何流式正文，用完整内容写入消息流，避免丢弃
            if (!streamedThisTurn.value) {
              const fullOut = String(msg.content ?? msg.text ?? '')
              if (fullOut) {
                messages.value.push({ type: 'ai', content: fullOut })
                streamedThisTurn.value = true
              }
            }
          } else {
            messages.value.push({ type: 'ai', content: `❌ ${String(msg.content ?? '')}` })
            // error 为异常终态，直接熄灭能量条
            taskActive.value = false
          }
          // 【R1 修复·根因级，对齐旧前端 chat_ui.html L1451-1518】终态事件显式置空本轮气泡指针:
          // 旧前端靠 ai_output / error 让 currentReasoningMsg / currentStreamMsg 置 null 来分轮，
          // 不是靠"看末条是不是 user"。我批次 A 引入的 ensureRoundLandmarks() 用末尾类型判定，
          // 一旦 messages.value 被整体替换（loadProjectMessages / syncLastOutput）或被裁剪，
          // 判据就会失效 → 指针永不重置 → 多轮 thinking 全部追加到同一条 think 气泡（用户报的"思考合并"）、
          // 多轮正文全部追加到同一条 ai 气泡（用户报的"输出合并"）。
          // 这里显式置空，与数组整体替换、与末条类型彻底解耦，是分轮的权威机制（与 R3 互补成闭环）。
          roundThinkMsg = null
          roundAiMsg = null
          // Q3甲:ai_output（正文输出）不熄灭能量条，等后端 memory_saved（工具链全部完成）再熄灭（对齐原文件 chat_ui.html）
          // 流结束立即落盘一次，避免防抖延迟导致最后一轮内容未持久化
          persistMessages()
        } else if (msg.type === 'secondary_to_main') {
          // 次级模型 @主控 → 主对话页只显示一条"来自XX的消息"（不自动唤醒、不自动回复，避免无限续接）
          const sender = String(msg.sender || '次级')
          const body = String(msg.content ?? '')
          // 【头像接入】透传后端 payload 的 slot（2~9 → 各自头像）；
          // 旧后端无该键时落 0 → senderIcon() 走 role 反查兜底，不报错、不退化。
          const senderSlot = Number(msg.slot) || 0
          if (body) messages.value.push({ type: 'secondaryMsg', role: sender, content: body,
                                          slot: senderSlot } as any)
        } else if (msg.type === 'memory_saved') {
          // 记忆落盘=整轮对话真正结束，此时才熄灭蓝色能量条
          taskActive.value = false
        }
      } catch (err) {
        // 解析失败可见化:不再静默吞掉，便于 F12 定位
        console.error('[SSE] 消息解析失败:', err, ev.data)
      }
    }
  } catch (e) {
    console.error('[sse] 连接失败:', e)
  }
}

/** ===== 跨窗口项目同步:主窗 ↔ 悬浮窗 共用本组件，凭原生 storage 事件双向同步项目 =====
 *  原理:窗口A切项目 → 写 localStorage['current_selected_project'] → 同源窗口B自动收到 storage 事件
 *  防死循环:e.newValue === curProject.value 时直接返回（同值不重复触发） */
function onStorageChange(e: StorageEvent) {
  // 【修复③·跨窗口用户消息同步】:助手输出走后端 SSE 广播（两窗同达），用户消息此前只本地 push，
  //  另一窗口收不到 → 实测"我的输出只在发送窗口出现"。这里监听本项目 chat_ 缓存变化，
  //  把本端缺失的 user 消息补齐。硬约束:原地 push（不整体替换数组）→ 不打断本端流式输出、不产生幽灵引用。
  if (e.key && e.key === 'chat_' + currentProjectName()) {
    if (!e.newValue) return
    try {
      const incoming = JSON.parse(e.newValue)
      if (!Array.isArray(incoming)) return
      // 指纹去重:type + content + attachments 相同视为同一条，避免两窗互写后重复补插
      const seen = new Set(
        messages.value
          .filter((m) => m.type === 'user')
          .map((m) => String(m.content) + '\u0000' + JSON.stringify(m.attachments || []))
      )
      let added = 0
      incoming.forEach((m: any) => {
        if (!m || m.type !== 'user') return
        const sig = String(m.content) + '\u0000' + JSON.stringify(m.attachments || [])
        if (seen.has(sig)) return
        seen.add(sig)
        messages.value.push(m)
        added++
      })
      // 【显示优化】跨窗口补插了用户消息 → 同步折叠态并强制滚到底部（另一窗口发的消息，本端也应看到）
      if (added > 0) { updateFoldStates(); scrollToBottom(true) }
    } catch {}
    return
  }
  if (e.key !== 'current_selected_project') return
  if (!e.newValue || e.newValue === curProject.value) return
  // 【修复·同上】另一窗口切到「（全局）」时，newValue 是 default 对象串，
  //  直接赋值同样会显示空白；此处与 onMounted 用同一归一化口径。
  curProject.value = isGlobalProjectStr(e.newValue) ? '' : e.newValue
  switchProject()
}
onMounted(async () => {
  // 恢复上次选择的项目（跨页同步）——必须先恢复项目，消息缓存键才正确
  try {
    const sp = localStorage.getItem('current_selected_project')
    // 【修复·下拉框回显】「全局/default」统一归一化为空串，与 <option value=""> 对齐；
    //  原实现直接把 default 对象串塞给 v-model → 匹配不到任何 option → 切页回来显示空白。
    curProject.value = isGlobalProjectStr(sp) ? '' : (sp as string)
  } catch {}
  // 恢复当前项目的持久化消息（切页 / 刷新不丢）
  loadProjectMessages()
  // 【阶段5-2·M4】恢复思考模式开关的持久化状态（不 await:异步读取，不阻塞后续 SSE 建连）
  loadThinkMode()
  // 【人设名展示·M5】异步读取主控（slot=1）人设名，供标题区动态显示（失败保持兜底显示"主控"，不阻塞建连）
  loadPersonaName()
  // A 修复:SSE 先建连（同步调用，不阻塞），避免 loadProjects 异常/耗时导致 SSE 从未连接
  connectStatusSSE()
  // 方案A:从后端拉取本轮输出快照，补齐切页/断线期间丢弃的流式增量（异步不阻塞建连）
  syncLastOutput()
  // 页面重新可见 / 网络恢复时自动重连（对齐 chat_ui.html）
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('online', onNetworkOnline)
  // 跨窗口项目同步:监听其他窗口切换项目（本窗口不触发，天然无死循环）
  window.addEventListener('storage', onStorageChange)
  await loadProjects()
})

onUnmounted(() => {
  // 清理 SSE 连接 + 看门狗 / 重连定时器 + 事件监听，避免内存泄漏
  stopWatchdog()
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('online', onNetworkOnline)
  window.removeEventListener('storage', onStorageChange)
  if (es) { es.close(); es = null }
})
</script>

<style scoped>
/* 能量条:不额外加任何外框/底色，靠内部小能量柱依次点亮与熄灭体现"任务进行中" */
.box-div-nkke7 > div {
  background-color: #d8dce5;
}
.box-div-nkke7.energy-active > div {
  animation: dotPulse 1.05s ease-in-out infinite;
}
.box-div-nkke7.energy-active > div:nth-child(1) { animation-delay: 0s; }
.box-div-nkke7.energy-active > div:nth-child(2) { animation-delay: .1s; }
.box-div-nkke7.energy-active > div:nth-child(3) { animation-delay: .2s; }
.box-div-nkke7.energy-active > div:nth-child(4) { animation-delay: .3s; }
.box-div-nkke7.energy-active > div:nth-child(5) { animation-delay: .4s; }
.box-div-nkke7.energy-active > div:nth-child(6) { animation-delay: .5s; }
.box-div-nkke7.energy-active > div:nth-child(7) { animation-delay: .6s; }
.box-div-nkke7.energy-active > div:nth-child(8) { animation-delay: .7s; }
.box-div-nkke7.energy-active > div:nth-child(9) { animation-delay: .8s; }
@keyframes dotPulse {
  0%, 100% { background-color: #d8dce5; transform: scaleY(1); }
  50% { background-color: var(--primary); transform: scaleY(1.18); }
}
/* 气泡正文:保留换行、长词强制换行（原版 content.innerText 口径，不引入 markdown 依赖） */
.box-span-faprc,
.box-span-vlxkl,
.box-span-mugyd {
  white-space: pre-wrap;
  word-break: break-word;
}

/* 气泡操作栏:折叠 / 复制（对齐原版 message-actions + msg-toggle-btn / msg-copy-btn） */
.box-div-msgact {
  display: flex;
  flex-direction: row;
  gap: 6px;
  margin-top: 4px;
}
.box-button-msgact {
  border: none;
  background: transparent;
  color: #86909c;
  font-size: 12px;
  line-height: 1.4;
  padding: 2px 6px;
  border-radius: 4px;
  transition: color .15s ease, background-color .15s ease;
}
.box-button-msgact:hover {
  /* 【视觉分层·M8】气泡操作按钮（折叠▾/复制⧉）hover 色改走全局主色令牌:
     该按钮同时挂在「用户蓝底气泡 / 系统派发灰底气泡 / AI 白底气泡」三类气泡旁，
     属"消息视觉分层"的直接关联区 → 与 .msg-sys / 用户气泡共用同一令牌来源，
     切主色时按钮 hover 与气泡自动同步，不再出现"气泡变了、按钮没变"的割裂。
     原值 #165DFF 与 var(--primary) 当前同值 → 本次改动视觉零变化，仅统一令牌来源。
     【L0 兜底】加第二参数 #165DFF:theme.js 未加载 / 加载失败时按钮 hover 仍可见（保命）；
     theme.js 加载成功时其写入 :root 的内联 style 优先级更高，自动跟随主题色，两层互不干扰。 */
  color: var(--primary, #165DFF);
  background-color: #f2f3f5;
}

/* 折叠态:限制高度（4.8em ≈ 3 行，对齐旧版 chat_ui.html 的 .content.fold）+ 隐藏溢出，点击「▸」恢复 */
.msg-folded {
  max-height: 4.8em;
  overflow: hidden;
  position: relative;
}

/* 工具调用提示条（已弃用，保留样式不影响；原版无此节点） */
.box-div-tooltip {
  display: none;
}
.box-div-tooltip.tt-error { background-color: #fff1f0; color: #d4380d; }
.box-div-tooltip.tt-warning { background-color: #fff7e8; color: #d25f00; }
.box-span-tooltip { word-break: break-all; }

/* 附件预览条:缩略图 + 文件名 + ✕ 可取消 */
.box-div-attach {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 8px;
  padding-bottom: 8px;
}
.box-attach-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background-color: #f2f3f5;
  border-radius: 6px;
  font-size: 12px;
  color: #4e5969;
}
.box-attach-thumb {
  width: 36px;
  height: 36px;
  object-fit: cover;
  border-radius: 4px;
  display: block;
}
.box-attach-name { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.box-attach-del {
  border: none;
  background: transparent;
  color: #86909c;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
}
.box-attach-del:hover { color: #d4380d; }

/* 思考模式开关:双态（开=主色轨道+滑块右，关=灰轨道+滑块左），过渡柔和 */
.box-div-7pnux {
  transition: background-color .2s ease, justify-content .2s ease;
}
.box-div-7pnux.think-on {
  /* 【主题统一·M1】开启态轨道改用全局主色令牌 var(--primary) + 兜底 #165DFF:
     病灶:原先硬编码 #165DFF → 用户把主题改成粉紫/红等主色时，开关仍是蓝色（未接主题）。
     兜底值保证 theme.js 加载失败时开关仍可见可辨（与本文件 L0 兜底口径一致）。
     !important 保留:轨道底色由本类覆盖 .box-div-7pnux 基础的灰轨 #d8dce5。 */
  background: var(--primary, #165DFF) !important;
  justify-content: flex-end !important;
}
.box-div-8ouzx {
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

.box-div-62xqx {
  display: flex;
  flex-direction: row;
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

.box-div-yanfg {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 145px;
  min-height: 40px;
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding-top: 12px;
  padding-right: 12px;
  padding-bottom: 12px;
  padding-left: 12px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  align-items: stretch;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

/* 悬浮窗模式:隐藏外层导航栏，仅保留对话区（URL 带 ?mode=float 时生效，主窗默认不受影响） */
.float-mode .box-div-yanfg {
  display: none;
}

/* 悬浮窗模式:标题行与两控件同排（仅悬浮窗生效，主窗样式零改动） */
.float-mode .box-div-59iim {
  justify-content: space-between;
  align-items: center;
}

.box-div-title-float {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.box-span-3ttij {
  font-size: 18px;
  color: #1d2129;
  align-self: center;
  height: 68px;
  width: auto;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-span-6kcox {
  font-size: 20px;
  font-weight: 600;
  color: #1d2129;
  text-align: center;
  margin-bottom: 12px;
  align-self: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-gvyw3 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-hyhye {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-ebs5o {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-lnrux {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-poots {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-v4ho7 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-wr90q {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-0ihym {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-zjopk {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-e327z {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-button-71sid {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
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

.box-div-2uaow {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: flex-end;
  justify-content: flex-end;
  margin-top: auto;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-4xtqa {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-35526 {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 40px;
  background-color: #ffffff;
  box-shadow: none;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  flex-grow: 1;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-bk778 {
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

.box-div-9a58f {
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

.box-div-59iim {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-h2-l1ula {
  font-size: 22px;
  font-weight: 600;
  /* 【标题横排修复】不允许中文逐字换行（此前被同级控件块挤压 → 竖排），且不参与 flex 收缩 */
  white-space: nowrap;
  flex-shrink: 0;
  color: #1f2329;
  line-height: 1.4;
  margin-top: 0;
  margin-bottom: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-4w6en {
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

.box-div-j3t1o {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  /* 【标题横排修复】原 width:100% 会独占整行、把同级 h2 挤成逐字竖排；改为弹性占位（只吃剩余空间，不挤压标题） */
  flex: 1 1 auto;
  min-width: 0;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-7d3d1 {
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

.box-select-644z5 {
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

.box-button-ywdge {
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

.box-div-mqz2q {
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

.box-span-cbnsx {
  font-size: 12px;
  color: #4e5969;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-7pnux {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  width: 44px;
  height: 24px;
  min-width: 44px;
  padding-left: 4px;
  padding-right: 4px;
  background-color: #d8dce5;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
  border-bottom-left-radius: 12px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-1w4rg {
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

.box-div-wvyv4 {
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

.box-div-e9vp9 {
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

.box-span-fq7xn {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  max-width: 36px;
  background-color: transparent;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  object-fit: contain;
  gap: 8px;
}

.box-div-tn7ye {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-grow: 1;
  min-width: 0px;
  /* 【视觉分层·M5】AI 回答气泡:白底 + 灰色描边（走全局令牌，随主题色联动）。
     原值 #f7f8fa 是硬编码浅灰 → 与用户气泡同色，导致"三类消息一个样"。
     现改为语义令牌 var(--bg-card)，并补四边描边把它"卡"出来。
     box-sizing: border-box 保证加边框后不额外撑宽（与原布局宽度一致，零视觉位移）。 */
  /* 【L0 兜底】AI 气泡底与四边描边加兜底色:
     背景 #FFFFFF / 描边 #E4E7ED（逐字对齐 static/theme.css 的 --bg-card / --border-color 默认值）。
     目的:theme.js 若加载失败，AI 气泡仍为白底+灰描边（不会隐身）；theme.js 加载成功后自动跟随主题。 */
  background-color: var(--bg-card, #FFFFFF);
  box-sizing: border-box;
  border-top: 1px solid var(--border-color, #E4E7ED);
  border-right: 1px solid var(--border-color, #E4E7ED);
  border-bottom: 1px solid var(--border-color, #E4E7ED);
  border-left: 1px solid var(--border-color, #E4E7ED);
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

.box-span-faprc {
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

.box-div-d1c5j {
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

.box-span-i5aio {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 36px;
  height: 36px;
  min-width: 36px;
  max-width: 36px;
  /* 【视觉分层·M6】用户消息左侧「我」头像:深蓝 var(--primary-active)（#0E42C9）。
     原值 #86909c 是中性灰 → 贴在蓝底气泡旁显得"脏"，且无主题语义。
     改为 primary 的 active 档，与蓝底同色系形成层次（浅蓝主色 → 深蓝头像），换主色自动跟随。
     【L0 兜底】加第二参数 #0E42C9（逐字对齐 theme.css 的 --primary-active 默认值）。 */
  background-color: var(--primary-active, #0E42C9);
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

.box-div-dlklc {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-grow: 1;
  min-width: 0px;
  /* 【视觉分层·M3】用户消息气泡:蓝底（与「发送」按钮 .box-button-ery33 的 #165DFF 同源为 var(--primary)，
     后续在「系统配置 → 界面主题」改主色时，按钮与用户气泡自动同步变色）。
     原值 #f7f8fa 是硬编码浅灰 → 与 AI 气泡同色，用户消息"看不出来是谁说的"。
     【L0 兜底】加第二参数 #165DFF（逐字对齐 theme.css 的 --primary 默认值），
     保证 theme.js 加载失败时用户气泡仍为蓝底白字，不会因变量缺失而"隐身"。 */
  background-color: var(--primary, #165DFF);
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

.box-span-vlxkl {
  font-size: 14px;
  /* 【视觉分层·M4】用户消息正文:白字（配合父容器 .box-div-dlklc 的蓝底，构成"蓝底白字"）。 */
  color: #ffffff;
  line-height: 1.6;
  white-space: pre-wrap;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-0fxg5 {
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

.box-div-248pp {
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

.box-button-7k8i5 {
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

.box-span-9q2h1 {
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

.box-button-2seb1 {
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

.box-div-m1e8x {
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

.box-span-mugyd {
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

.box-div-0hvtq {
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

.box-span-k0cef {
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

.box-div-fn3g5 {
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

.box-span-pxsik {
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

.box-div-b2oll {
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

.box-div-1qfcv {
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

.box-button-3h58p {
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

.box-button-qit6d {
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

.box-div-nkke7 {
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

.box-div-z2jyo {
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

.box-div-scpjn {
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

.box-div-7dnug {
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

.box-div-y55zw {
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

.box-div-e930y {
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

.box-div-v0zkl {
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

.box-div-5bh4j {
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

.box-div-lynj2 {
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

.box-div-6wvrj {
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

.box-div-sfe42 {
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

.box-textarea-6jw94 {
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

.box-button-ery33 {
  font-size: 13px;
  color: #ffffff;
  /* 【视觉分层·M9】「发送」按钮底色改走全局主色令牌 var(--primary):
     原值 #165DFF 与 var(--primary) 当前同值 → 视觉零变化；
     改动意义在于让"用户气泡蓝底 .box-div-dlklc"与"发送按钮蓝底"在令牌层面真正同源
     （用户消息气泡本就是 var(--primary)），切主色时二者严格同步，主题统一一次到位。
     【L0 兜底】加第二参数 #165DFF:theme.js 未加载时按钮仍为蓝底白字（不会"消失"），
     加载成功后自动跟随主题色，两层互不干扰。 */
  background-color: var(--primary, #165DFF);
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

/* ==================================================================
   【视觉分层·M7】三类消息一套令牌，切主色自动联动
   ------------------------------------------------------------------
   ① 用户消息  = 蓝底白字   → .box-div-dlklc (var(--primary)) + .box-span-vlxkl (#fff)
   ② AI 回答   = 白底深字+灰描边 → .box-div-tn7ye (var(--bg-card) + var(--border-color))
   ③ 系统派发  = 灰底蓝字+浅蓝描边 → 下方 .msg-sys / .msg-sys-text（仅挂 secondaryMsg 分支）

   为什么放文件末尾:同优先级(单类选择器)下"后定义胜出" ——
   ① .msg-sys 必须晚于 .box-div-tn7ye(L1646) 才能覆盖其白底/灰描边；
   ② .msg-sys-text 必须晚于 .box-span-faprc(L1665) 才能覆盖其深色正文。
   两条规则全部引用 static/theme.css 既有令牌，不新增任何硬编码色值。
   ================================================================== */
.msg-sys {
  /* 【L0 兜底】系统派发灰底 + 浅蓝描边加兜底色:
     背景 #F5F7FA / 描边 #E8F0FF（逐字对齐 theme.css 的 --bg-page / --primary-light 默认值）。
     目的:theme.js 加载失败时，系统派发仍是灰底+浅蓝描边（与用户蓝底 / AI 白底三向可辨）；
     theme.js 加载成功后自动跟随主题。 */
  background-color: var(--bg-page, #F5F7FA);
  border-top: 1px solid var(--primary-light, #E8F0FF);
  border-right: 1px solid var(--primary-light, #E8F0FF);
  border-bottom: 1px solid var(--primary-light, #E8F0FF);
  border-left: 1px solid var(--primary-light, #E8F0FF);
}
.msg-sys-text {
  /* 【L0 兜底】系统派发蓝字加兜底色 #165DFF（对齐 theme.css 的 --primary 默认值）:
     theme.js 加载失败时仍为蓝字（与灰底构成可辨的"灰底蓝字"），加载成功后自动跟随主题。 */
  color: var(--primary, #165DFF);
}

/* ===== 【附件方案②】用户消息气泡内的附件区（对齐旧页 chat_ui.html L982-993 的 DOM 与视觉口径）=====
   1) .msg-attachments —— 附件容器:块级 flex 换行，与消息正文之间留 8px 间距
   2) .msg-attach-img  —— 图片缩略图:80×80 圆角，鼠标手型（点击后 window.open 打开原图）
   3) .msg-attach-file —— 普通文件卡:半透明底圆角小卡片（📄 + 文件名 + 下载链接）
   配色说明:用户气泡本身是"主色底 + 白字"（.box-div-dlklc + .box-span-vlxkl），
   故附件卡片统一用白色半透明底 + 白字描边，与气泡融为一体（旧页为灰底深字，行为口径相同、配色按新版设计语言适配）。 */
.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.msg-attach-img {
  display: block;
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  cursor: pointer;
}
.msg-attach-img:hover {
  opacity: 0.88;
}
.msg-attach-file {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 260px;
  padding: 6px 10px;
  border-radius: 6px;
  background-color: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  font-size: 13px;
  line-height: 1.4;
}
.msg-attach-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-attach-dl {
  flex-shrink: 0;
  margin-left: auto;
  color: #ffffff;
  text-decoration: underline;
}
</style>
