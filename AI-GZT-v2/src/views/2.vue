<!--
  页面《2》　路由:/2（2）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-q7ahd">
    <div class="box-div-bgph5">
      <div class="box-div-sdnf3" :class="{ collapsed: sidebarCollapsed }">
        <div v-show="sidebarCollapsed" class="repo-collapsed-tip" @click="toggleSidebar">点击展开仓库</div>
        <div class="box-div-fltjp">
          <h2 class="box-h2-rzd35">仓库</h2>
          <div class="box-div-c1eb8">
            <button class="box-button-4r0o8" type="button" @click="openRepository">打开仓库</button>
            <button class="box-button-l0sdq" type="button" @click="refreshTree">刷新</button>
            <button class="box-button-lgbdg" type="button" @click="toggleSidebar">{{ sidebarCollapsed ? '»' : '«' }}</button>
          </div>
        </div>
        <div class="box-div-kiadn" @contextmenu.prevent="showContainerContextMenu">
          <div
            v-for="node in fileTree"
            :key="node.path"
            class="repo-node"
            :style="{ paddingLeft: node.level * 16 + 4 + 'px' }"
            @contextmenu.prevent.stop="showContextMenu($event, node)"
          >
            <button v-if="node.is_dir" class="repo-toggle" type="button" @click="toggleNode(node)">{{ node.expanded ? '▾' : '▸' }}</button>
            <span v-else class="repo-toggle-placeholder"></span>
            <span class="repo-icon">{{ node.is_dir ? '📁' : '📄' }}</span>
            <span class="repo-name" :class="{ active: node.path === currentPath, isolated: node.is_isolated }" @click="handleNodeClick(node)">{{ node.name }}</span>
            <span v-if="node.is_isolated" class="repo-isolated-flag">（已隔离）</span>
          </div>
          <div v-if="fileTree.length === 0" style="text-align: center; color: #999; padding: 40px 0;">仓库为空</div>
        </div>
        <div class="box-div-vr9zw">
          <button class="box-button-658q9" type="button" @click="ragBuild" :disabled="ragBuilding">{{ ragBuilding ? '重建中…' : '全库RAG重建' }}</button>
        </div>
      </div>
      <div class="box-div-lxn0o">
        <div class="box-div-m77ss">
          <h2 class="box-h2-vj1l1">文件</h2>
          <div class="box-div-doxym">
            <input class="box-input-d8soa" type="text" placeholder="请输入关键词" v-model="keyword" />
            <button class="box-button-qo5zs" type="button">⌕</button>
          </div>
        </div>
        <div class="box-div-3vr0j">
          <div class="box-div-v9680">
            <div class="box-div-hcg8q">
              <span class="box-span-hh5m7">路径:</span>
              <span class="box-span-lnm96">{{ currentPath || '未选择文件' }}</span>
            </div>
            <div class="repo-toolbar-actions">
              <button v-if="isMarkdown" class="box-button-r9cwr" type="button" @click="toggleMdMode">{{ mdMode === 'preview' ? '源码' : '预览' }}</button>
              <button v-if="previewType === 'text' && (!isMarkdown || mdMode === 'source')" class="box-button-r9cwr" type="button" @click="handleFileSave">保存</button>
              <button v-if="currentPath" class="box-button-r9cwr" type="button" @click="openExternal">外部打开</button>
            </div>
          </div>
          <div class="box-div-17sf6">
            <div v-if="!currentPath" class="repo-preview-empty">请从左侧选择文件</div>
            <div v-else-if="previewType === 'image'" class="repo-preview-center">
              <img :src="previewUrl" alt="预览图片" />
            </div>
            <div v-else-if="previewType === 'pdf'" class="repo-preview-fill">
              <iframe :src="previewUrl"></iframe>
            </div>
            <div v-else-if="previewType === 'video'" class="repo-preview-center">
              <video :src="previewUrl" controls autoplay muted></video>
            </div>
            <div v-else-if="previewType === 'audio'" class="repo-preview-center">
              <audio :src="previewUrl" controls autoplay></audio>
            </div>
            <div v-else-if="previewType === 'hex'" class="repo-preview-hex">
              <template v-if="hexData">
                <div v-for="(line, idx) in hexData.hex_lines" :key="idx" class="hex-line">
                  <span class="hex-offset">{{ (hexData.offset + idx * 16).toString(16).padStart(8, '0') }}</span>
                  <span class="hex-bytes">{{ line }}</span>
                  <span class="hex-ascii">{{ hexData.ascii_lines[idx] }}</span>
                </div>
                <div v-if="hexData.read_size < hexData.total_size" class="hex-tip">仅显示前16KB内容，完整内容请外部打开查看</div>
              </template>
            </div>
            <div v-else-if="previewType === 'office'" class="repo-preview-empty">
              📄 该文档类型暂不支持内嵌预览，请点击「外部打开」查看
            </div>
            <div v-else-if="isMarkdown && mdMode === 'preview'" class="repo-md-preview" v-html="mdHtml"></div>
            <div v-else ref="editorRef" class="repo-editor-host"></div>
          </div>
        </div>

        <!-- 右键菜单（fixed 定位，边界自动调整） -->
        <div
          v-if="menuVisible"
          ref="menuRef"
          class="repo-ctxmenu"
          :style="menuStyle"
          @click.stop
        >
          <div v-if="ctxData && !ctxData.is_dir && isRunnableFile(ctxData.name)" class="repo-ctxmenu-item" @click="doRun">运行</div>
          <div v-if="ctxData && ctxData.is_dir" class="repo-ctxmenu-item" @click="doRagProject">RAG项目入库</div>
          <div v-if="ctxData && !isCurrentIsolated()" class="repo-ctxmenu-item" @click="doIsolate">加入项目信息隔离</div>
          <div v-if="ctxData && isCurrentIsolated()" class="repo-ctxmenu-item" @click="doUnisolate">解除项目信息隔离</div>
          <div class="repo-ctxmenu-item" @click="doNewFile">新建文件</div>
          <div class="repo-ctxmenu-item" @click="doNewFolder">新建文件夹</div>
          <div v-if="!ctxData" class="repo-ctxmenu-item" @click="doCreateProjectManual">创建项目文件夹</div>
          <div v-if="ctxData" class="repo-ctxmenu-item" @click="doCopy">复制</div>
          <div v-if="clipboard && (!ctxData || ctxData.is_dir)" class="repo-ctxmenu-item" @click="doPaste">粘贴</div>
          <div v-if="ctxData" class="repo-ctxmenu-item" @click="doRename">重命名</div>
          <div v-if="ctxData" class="repo-ctxmenu-item danger" @click="doDelete">删除</div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import { get, post } from '@/api/request'

/** 仓库树节点（嵌套结构，便于展开/折叠） */
interface TreeNode {
  name: string
  path: string
  is_dir: boolean
  size?: number
  is_isolated?: boolean
  expanded: boolean
  loaded: boolean
  children: TreeNode[]
}

/** 后端 /api/file/list 返回项 */
interface FileListItem {
  name: string
  path: string
  is_dir: boolean
  size?: number
  is_isolated?: boolean
}

/** 后端 /api/file/hex_read 返回 data */
interface HexData {
  hex_lines: string[]
  ascii_lines: string[]
  offset: number
  total_size: number
  read_size: number
}

/** 预览类型（参考旧页 file_editor.html 的 6 类预览） */
type PreviewType = 'empty' | 'text' | 'image' | 'pdf' | 'video' | 'audio' | 'hex' | 'office'

const tree = ref<TreeNode[]>([])
const keyword = ref('')
const currentPath = ref('')
const fileContent = ref('')

/** ===== 预览状态 ===== */
const previewType = ref<PreviewType>('empty')
const previewUrl = ref('')
const hexData = ref<HexData | null>(null)

/** ===== 编辑器状态（CodeMirror 动态加载 + md 渲染） ===== */
const editorRef = ref<HTMLElement | null>(null)
let cmInstance: any = null
let cmLoaded = false
let cmLoadingPromise: Promise<void> | null = null
const mdMode = ref<'preview' | 'source'>('source')
const markedReady = ref(false)

/** ===== 仓库左栏折叠状态 ===== */
const sidebarCollapsed = ref(false)

/** 全库 RAG 重建进行中（按钮 :disabled + 文案切换，对齐旧前端 ragBuilding；防重复点击） */
const ragBuilding = ref(false)

/** 折叠/展开仓库左栏 */
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

/** 当前文件是否为 markdown */
const isMarkdown = computed(() => currentPath.value.toLowerCase().endsWith('.md'))
/** markdown 渲染后的 HTML */
const mdHtml = computed(() => {
  if (!isMarkdown.value || !markedReady.value) return ''
  const m = (window as any).marked
  return m ? m.parse(fileContent.value) : ''
})

const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'ico', 'tiff', 'tif']
const hexExts = ['exe', 'dll', 'bin', 'zip', 'rar', '7z', 'iso', 'msi', 'pkg', 'deb', 'rpm', 'tar', 'gz', 'bz2', 'xz']
const pdfExts = ['pdf']
const videoExts = ['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'flv', 'wmv']
const audioExts = ['mp3', 'wav', 'ogg', 'aac', 'wma', 'm4a']
const officeExts = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']

/** ===== 右键菜单状态 ===== */
const menuVisible = ref(false)
const menuStyle = ref<{ left: string; top: string }>({ left: '0px', top: '0px' })
const menuRef = ref<HTMLElement | null>(null)
const pendingX = ref(0)
const pendingY = ref(0)
/** 当前右键的数据节点（空白处右键为 null） */
const ctxData = ref<TreeNode | null>(null)
/** 前端剪贴板（复制项，刷新即清空） */
const clipboard = ref<{ path: string; name: string; is_dir: boolean } | null>(null)
/** 隔离清单（相对仓库根路径） */
const isolationPaths = ref<string[]>([])

/** 展平为可见行（仅展开目录的子级可见），携带 level 供缩进 */
const fileTree = computed(() => {
  const out: Array<TreeNode & { level: number }> = []
  const walk = (nodes: TreeNode[], level: number) => {
    nodes.forEach((n) => {
      const visible = !keyword.value || n.name.toLowerCase().includes(keyword.value.toLowerCase())
      if (visible) out.push({ ...n, level })
      if (n.is_dir && n.expanded && n.children.length) walk(n.children, level + 1)
    })
  }
  walk(tree.value, 0)
  return out
})

/** 拉取某目录下的直接子项（相对仓库根的 path，根传空串） */
async function loadChildren(parentPath: string): Promise<TreeNode[]> {
  const data = await get<FileListItem[]>('/api/file/list', { path: parentPath })
  return (data || []).map((item) => ({
    name: item.name,
    path: item.path,
    is_dir: item.is_dir,
    size: item.size,
    is_isolated: item.is_isolated,
    expanded: false,
    loaded: false,
    children: [],
  }))
}

/** 按 path 在树中查找真实节点 */
function findNode(path: string, nodes: TreeNode[] = tree.value): TreeNode | null {
  for (const n of nodes) {
    if (n.path === path) return n
    if (n.children.length) {
      const hit = findNode(path, n.children)
      if (hit) return hit
    }
  }
  return null
}

/** 加载仓库根（刷新） */
async function refreshTree() {
  try {
    tree.value = await loadChildren('')
  } catch (e) {
    console.error('加载仓库失败', e)
  }
}

/** 展开 / 折叠目录（首次展开才拉取子项） */
async function toggleNode(node: TreeNode) {
  if (!node.is_dir) return
  const real = findNode(node.path)
  if (!real) return
  if (real.expanded) {
    real.expanded = false
    return
  }
  if (!real.loaded) {
    try {
      real.children = await loadChildren(real.path)
      real.loaded = true
    } catch (e) {
      console.error('加载目录失败', e)
      return
    }
  }
  real.expanded = true
}

/** 按扩展名判断预览类型 */
function detectPreviewType(path: string): PreviewType {
  const dot = path.lastIndexOf('.')
  const ext = dot >= 0 ? path.slice(dot + 1).toLowerCase() : ''
  if (!ext) return 'text'
  if (imageExts.includes(ext)) return 'image'
  if (pdfExts.includes(ext)) return 'pdf'
  if (videoExts.includes(ext)) return 'video'
  if (audioExts.includes(ext)) return 'audio'
  if (hexExts.includes(ext)) return 'hex'
  if (officeExts.includes(ext)) return 'office'
  return 'text'
}

/** 读取文件:按类型分流（文本走 file/read，hex 走 hex_read，其余走 file/preview 直链） */
async function readFile(path: string) {
  currentPath.value = path
  previewUrl.value = `/api/file/preview?path=${encodeURIComponent(path)}`
  hexData.value = null
  fileContent.value = ''
  destroyEditor()
  const ptype = detectPreviewType(path)
  previewType.value = ptype
  try {
    if (ptype === 'text') {
      const content = await get<string>('/api/file/read', { path })
      fileContent.value = content ?? ''
      if (isMarkdown.value) {
        await ensureMarked()
        mdMode.value = 'preview'
      } else {
        mdMode.value = 'source'
        await ensureCodeMirror()
        await nextTick()
        mountEditor()
      }
    } else if (ptype === 'hex') {
      const data = await get<HexData>('/api/file/hex_read', { path })
      hexData.value = data
    }
    // image/pdf/video/audio/office 直接使用 previewUrl，无需额外请求
  } catch (e) {
    console.error('读取文件失败', e)
  }
}

/** 按扩展名映射 CodeMirror mode（未匹配返回 null = 纯文本） */
function detectMode(path: string): any {
  const dot = path.lastIndexOf('.')
  const ext = dot >= 0 ? path.slice(dot + 1).toLowerCase() : ''
  const map: Record<string, string> = {
    py: 'python',
    html: 'htmlmixed',
    vue: 'htmlmixed',
    js: 'javascript',
    ts: 'javascript',
    json: 'javascript',
    css: 'css',
    java: 'clike',
    c: 'clike',
    cpp: 'clike',
    h: 'clike',
    sql: 'sql',
    md: 'markdown',
  }
  return map[ext] || null
}

/** 动态注入样式表（避免重复） */
function loadCss(href: string) {
  if (document.querySelector(`link[href="${href}"]`)) return
  const l = document.createElement('link')
  l.rel = 'stylesheet'
  l.href = href
  document.head.appendChild(l)
}

/** 动态加载脚本（Promise 化） */
function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('加载脚本失败: ' + src))
    document.head.appendChild(s)
  })
}

/** 加载 marked（md 渲染库），只加载一次 */
async function ensureMarked(): Promise<void> {
  if ((window as any).marked) {
    markedReady.value = true
    return
  }
  await loadScript('/static/marked.min.js')
  markedReady.value = true
}

/** 按需加载 CodeMirror 及依赖（单例，仅首次加载） */
function ensureCodeMirror(): Promise<void> {
  if (cmLoaded && (window as any).CodeMirror) return Promise.resolve()
  if (cmLoadingPromise) return cmLoadingPromise
  const base = '/static/'
  cmLoadingPromise = (async () => {
    loadCss(base + 'codemirror.min.css')
    loadCss(base + 'foldgutter.min.css')
    await loadScript(base + 'codemirror.min.js')
    await loadScript(base + 'xml.min.js')
    await loadScript(base + 'htmlmixed.min.js')
    await loadScript(base + 'markdown.min.js')
    await loadScript(base + 'python.min.js')
    await loadScript(base + 'javascript.min.js')
    await loadScript(base + 'css.min.js')
    await loadScript(base + 'clike.min.js')
    await loadScript(base + 'sql.min.js')
    await loadScript(base + 'foldcode.min.js')
    await loadScript(base + 'foldgutter.min.js')
    await loadScript(base + 'brace-fold.min.js')
    await loadScript(base + 'comment-fold.min.js')
    await loadScript(base + 'indent-fold.min.js')
    await loadScript(base + 'matchbrackets.min.js')
    await loadScript(base + 'closebrackets.min.js')
    cmLoaded = true
  })()
  return cmLoadingPromise
}

/** 挂载 / 复用 CodeMirror 实例 */
function mountEditor() {
  if (!editorRef.value) return
  const CM = (window as any).CodeMirror
  if (!CM) return
  const modeName = detectMode(currentPath.value)
  if (cmInstance) {
    cmInstance.setValue(fileContent.value)
    cmInstance.setOption('mode', modeName)
    cmInstance.refresh()
    return
  }
  cmInstance = CM(editorRef.value, {
    value: fileContent.value,
    mode: modeName,
    lineNumbers: true,
    lineWrapping: false,
    matchBrackets: true,
    autoCloseBrackets: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
    theme: 'default',
  })
  cmInstance.on('change', () => {
    fileContent.value = cmInstance.getValue()
  })
}

/** 销毁 CodeMirror 实例并清空挂载点 */
function destroyEditor() {
  if (cmInstance) {
    cmInstance.off('change')
    cmInstance = null
  }
  if (editorRef.value) {
    editorRef.value.innerHTML = ''
  }
}

/** 切换 markdown 预览 / 源码 */
async function toggleMdMode() {
  if (mdMode.value === 'preview') {
    mdMode.value = 'source'
    await ensureCodeMirror()
    await nextTick()
    mountEditor()
  } else {
    mdMode.value = 'preview'
    destroyEditor()
  }
}

/** 点击节点:目录展开/折叠，文件读取 */
function handleNodeClick(node: TreeNode) {
  if (node.is_dir) toggleNode(node)
  else readFile(node.path)
}

/** 保存当前文件内容（仅文本类） */
async function handleFileSave() {
  if (!currentPath.value || previewType.value !== 'text') return
  try {
    await post('/api/file/write', { path: currentPath.value, content: fileContent.value })
    window.alert('保存成功')
  } catch (e) {
    console.error('保存文件失败', e)
  }
}

/** 外部打开当前文件 */
async function openExternal() {
  if (!currentPath.value) return
  try {
    await get('/api/file/open_external', { path: currentPath.value })
  } catch (e) {
    console.error('外部打开失败', e)
  }
}

/** 顶部「打开仓库」:调用系统资源管理器打开仓库根目录 */
async function openRepository() {
  try {
    await get('/api/file/open_repository')
  } catch (e) {
    console.error('打开仓库失败', e)
  }
}

/** 全库 RAG 重建（启动 + 每 1s 轮询状态，1:1 对齐旧前端 web_file_repo.html 的 handleRagBuild） */
async function ragBuild() {
  if (ragBuilding.value) return
  ragBuilding.value = true
  try {
    // 注意:此处不用统一封装 get()——/api/rag/build 返回 {code,msg} 无 data 字段，
    // get() 只解包 .data 会导致拿不到 code/msg；改用原生 fetch 读完整响应（与旧前端 axios 语义 1:1）。
    const res: any = await fetch('/api/rag/build').then((r) => r.json())
    if (res && res.code === 200) {
      window.alert(res.msg)
      // 轮询构建状态，直到 success / error
      const timer = window.setInterval(async () => {
        try {
          // 同上:/api/rag/build/status 返回 {code,status,result} 无 data 字段，须用原生 fetch 读完整响应
          const statusRes: any = await fetch('/api/rag/build/status').then((r) => r.json())
          if (statusRes.status === 'success') {
            window.clearInterval(timer)
            const r = statusRes.result || {}
            window.alert(`✅ RAG入库完成！成功:${r.success}个，失败:${r.fail}个，总计:${r.total}个`)
            ragBuilding.value = false
          } else if (statusRes.status === 'error') {
            window.clearInterval(timer)
            window.alert('❌ RAG入库失败:' + ((statusRes.result && statusRes.result.error) || ''))
            ragBuilding.value = false
          }
        } catch (e) {
          window.clearInterval(timer)
          console.error('RAG 状态查询失败', e)
          ragBuilding.value = false
        }
      }, 1000)
    } else {
      window.alert((res && res.msg) || '启动失败')
      ragBuilding.value = false
    }
  } catch (e) {
    console.error('RAG 重建启动失败', e)
    window.alert('RAG入库启动失败:' + ((e as any)?.message ?? String(e)))
    ragBuilding.value = false
  }
}

/** ===== 项目信息隔离 ===== */
async function loadIsolation() {
  try {
    const data = await get<{ paths?: string[]; list?: string[] }>('/api/isolation/list')
    const paths = (data && (data.paths || data.list)) || []
    isolationPaths.value = Array.isArray(paths) ? paths : []
  } catch (e) {
    // 拉取失败不阻断文件树使用（隔离功能降级为不可见）
    console.error('加载隔离清单失败', e)
  }
}

/** 当前右键目标是否已被隔离（含父路径前缀命中） */
function isCurrentIsolated(): boolean {
  const cur = ctxData.value
  if (!cur) return false
  const p = cur.path
  return isolationPaths.value.some((ip) => p === ip || p.startsWith(ip + '/'))
}

/** ===== 右键菜单 ===== */
/** 方案A:nextTick 后测量菜单真实尺寸，越界则自动左翻/上翻并夹边 */
async function positionMenu() {
  await nextTick()
  const el = menuRef.value
  const w = el ? el.offsetWidth : 160
  const h = el ? el.offsetHeight : 360
  let left = pendingX.value
  let top = pendingY.value
  if (left + w > window.innerWidth) left = pendingX.value - w
  if (top + h > window.innerHeight) top = pendingY.value - h
  menuStyle.value = { left: Math.max(8, left) + 'px', top: Math.max(8, top) + 'px' }
}

/** 节点右键 */
function showContextMenu(event: MouseEvent, node: TreeNode) {
  ctxData.value = node
  pendingX.value = event.clientX
  pendingY.value = event.clientY
  menuVisible.value = true
  positionMenu()
}

/** 容器空白处右键（data 为 null，用于新建/创建项目文件夹） */
function showContainerContextMenu(event: MouseEvent) {
  ctxData.value = null
  pendingX.value = event.clientX
  pendingY.value = event.clientY
  menuVisible.value = true
  positionMenu()
}

function hideContextMenu() {
  menuVisible.value = false
}

function handleDocumentClick() {
  if (menuVisible.value) hideContextMenu()
}

function handleResize() {
  if (menuVisible.value) hideContextMenu()
}

/** 是否可运行文件（复用后端 open_external） */
function isRunnableFile(fileName: string): boolean {
  if (!fileName) return false
  const dot = fileName.lastIndexOf('.')
  if (dot < 0) return false
  const ext = fileName.slice(dot).toLowerCase()
  return ['.bat', '.cmd', '.exe', '.ps1', '.html', '.htm'].includes(ext)
}

/** 运行（仅可执行/可打开类文件） */
async function doRun() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  try {
    await get('/api/file/open_external', { path: node.path })
  } catch (e) {
    console.error('运行失败', e)
  }
}

/** RAG 项目入库（仅文件夹） */
async function doRagProject() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  try {
    await post('/api/rag/build/project', { path: node.path })
    window.alert('项目 RAG 入库已启动')
  } catch (e) {
    console.error('RAG 项目入库失败', e)
  }
}

/** 加入项目信息隔离 */
async function doIsolate() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  try {
    await post('/api/isolation/add', { path: node.path })
    await loadIsolation()
    refreshTree()
  } catch (e) {
    console.error('加入隔离失败', e)
  }
}

/** 解除项目信息隔离 */
async function doUnisolate() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  try {
    await post('/api/isolation/remove', { path: node.path })
    await loadIsolation()
    refreshTree()
  } catch (e) {
    console.error('解除隔离失败', e)
  }
}

/** 新建文件 */
async function doNewFile() {
  const node = ctxData.value
  hideContextMenu()
  const parentPath = node && node.is_dir ? node.path : ''
  const fileName = window.prompt('请输入文件名')
  if (!fileName) return
  const fullPath = parentPath ? `${parentPath}/${fileName}` : fileName
  try {
    await post('/api/file/create', { path: fullPath, is_dir: false })
    refreshTree()
  } catch (e) {
    console.error('新建文件失败', e)
  }
}

/** 新建文件夹 */
async function doNewFolder() {
  const node = ctxData.value
  hideContextMenu()
  const parentPath = node && node.is_dir ? node.path : ''
  const folderName = window.prompt('请输入文件夹名')
  if (!folderName) return
  const fullPath = parentPath ? `${parentPath}/${folderName}` : folderName
  try {
    await post('/api/file/create', { path: fullPath, is_dir: true })
    refreshTree()
  } catch (e) {
    console.error('新建文件夹失败', e)
  }
}

/** 创建项目文件夹（仅空白处右键） */
async function doCreateProjectManual() {
  hideContextMenu()
  const projectName = window.prompt('请输入项目名称')
  if (!projectName) return
  try {
    await post('/api/project-manual/create', { project_name: projectName, save_path: '' })
    refreshTree()
  } catch (e) {
    console.error('创建项目文件夹失败', e)
  }
}

/** 复制（仅前端剪贴板） */
function doCopy() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  clipboard.value = { path: node.path, name: node.name, is_dir: node.is_dir }
}

/** 粘贴（复制到目标文件夹，空白处则粘到仓库根） */
async function doPaste() {
  const node = ctxData.value
  const clip = clipboard.value
  hideContextMenu()
  if (!clip) return
  const destDir = node && node.is_dir ? node.path : ''
  try {
    await post('/api/file/copy', { src_path: clip.path, dest_dir: destDir })
    refreshTree()
  } catch (e) {
    console.error('粘贴失败', e)
  }
}

/** 重命名 */
async function doRename() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  const newName = window.prompt('请输入新名称', node.name)
  if (!newName || newName === node.name) return
  try {
    await post('/api/file/rename', { old_path: node.path, new_name: newName })
    refreshTree()
  } catch (e) {
    console.error('重命名失败', e)
  }
}

/** 删除（项目文件夹走 project/delete，普通文件走 file/delete） */
async function doDelete() {
  const node = ctxData.value
  hideContextMenu()
  if (!node) return
  if (!window.confirm(`确定要删除「${node.name}」吗？删除后无法恢复！`)) return
  try {
    let isProject = false
    if (node.is_dir) {
      try {
        const children = await get<FileListItem[]>('/api/file/list', { path: node.path })
        isProject = (children || []).some((item) => item.name.endsWith('项目手册.md'))
      } catch (e) {
        // 读取子文件失败按普通文件夹处理
      }
    }
    if (isProject) {
      await post('/api/project/delete', { project_name: node.name, project_root: node.path })
      window.alert('项目删除成功，所有关联数据已同步清理')
    } else {
      await post('/api/file/delete', { path: node.path })
    }
    if (currentPath.value === node.path) {
      currentPath.value = ''
      previewType.value = 'empty'
    }
    refreshTree()
  } catch (e) {
    console.error('删除失败', e)
  }
}

onMounted(() => {
  refreshTree()
  loadIsolation()
  document.addEventListener('click', handleDocumentClick)
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  window.removeEventListener('resize', handleResize)
  destroyEditor()
})
</script>

<style scoped>
.box-div-q7ahd {
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

.box-div-bgph5 {
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

.box-div-sdnf3 {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 372px;
  /* 【防挤压修复】左栏宽度恒定 372px，不被右侧文件面板挤压（否则左栏变窄 → 标题被压成逐字竖排） */
  flex-shrink: 0;
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
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

/* ===== 仓库左栏折叠态 ===== */
.box-div-sdnf3.collapsed {
  width: 48px;
  min-width: 48px;
  max-width: 48px;
  padding-left: 4px;
  padding-right: 4px;
  overflow: hidden;
}
.box-div-sdnf3.collapsed .box-div-fltjp,
.box-div-sdnf3.collapsed .box-div-kiadn,
.box-div-sdnf3.collapsed .box-div-vr9zw {
  display: none;
}
.repo-collapsed-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  flex-grow: 1;
  min-height: 200px;
  writing-mode: vertical-rl;
  letter-spacing: 2px;
  font-size: 14px;
  color: var(--primary);
  cursor: pointer;
  user-select: none;
}

.box-div-fltjp {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-h2-rzd35 {
  /* 【标题横排修复】"仓库"不允许逐字换行（此前被挤压后中文逐字竖排），且不参与 flex 收缩 */
  white-space: nowrap;
  flex-shrink: 0;
  font-size: 20px;
  font-weight: 600;
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

.box-div-c1eb8 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 262px;
  min-height: 40px;
  align-items: flex-start;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-4r0o8 {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-l0sdq {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-lgbdg {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 28px;
  height: 28px;
  min-width: 28px;
  max-width: 28px;
  font-size: 14px;
  color: #1f2329;
  background-color: #f2f3f5;
  border-style: none;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-kiadn {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  flex-grow: 1;
  min-height: 320px;
  overflow: auto;
  background-color: #ffffff;
  padding-top: 12px;
  padding-right: 12px;
  padding-bottom: 12px;
  padding-left: 12px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-wwgws {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-ytha6 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-sg709 {
  font-size: 12px;
  color: #4e5969;
  background-color: transparent;
  border-style: none;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  text-align: center;
  padding-top: 2px;
  padding-right: 0px;
  padding-bottom: 2px;
  padding-left: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-zswlk {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-wilwj {
  width: 13px;
  height: 10px;
  min-width: 13px;
  max-width: 13px;
  background-color: #ff9a2e;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-xxi7b {
  font-size: 13px;
  font-weight: 600;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-1pi92 {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding-left: 20px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-qk0c8 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-j1xhu {
  display: flex;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-te13a {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-ccv0w {
  width: 10px;
  height: 13px;
  min-width: 10px;
  max-width: 10px;
  background-color: #c9cdd4;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-2ka7r {
  font-size: 13px;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-1zcpt {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-hghcf {
  display: flex;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-g8isu {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-ybqm4 {
  width: 10px;
  height: 13px;
  min-width: 10px;
  max-width: 10px;
  background-color: #c9cdd4;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-hfyc4 {
  font-size: 13px;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-5pl8l {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-yez36 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-tdy79 {
  font-size: 12px;
  color: #4e5969;
  background-color: transparent;
  border-style: none;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  text-align: center;
  padding-top: 2px;
  padding-right: 0px;
  padding-bottom: 2px;
  padding-left: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-0oypx {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-5qbcj {
  width: 13px;
  height: 10px;
  min-width: 13px;
  max-width: 13px;
  background-color: #ff9a2e;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-5gvo8 {
  font-size: 13px;
  font-weight: 600;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-wb47j {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding-left: 20px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-60hak {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-w87rc {
  display: flex;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-sy7b4 {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-cmkjz {
  width: 10px;
  height: 13px;
  min-width: 10px;
  max-width: 10px;
  background-color: #c9cdd4;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-hqln5 {
  font-size: 13px;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-gvvzy {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-lmuyh {
  display: flex;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-842qa {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-ewr0m {
  width: 10px;
  height: 13px;
  min-width: 10px;
  max-width: 10px;
  background-color: #c9cdd4;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-zv0w2 {
  font-size: 13px;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-ylecs {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-2f83a {
  display: flex;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-0p6my {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-ykjjc {
  width: 10px;
  height: 13px;
  min-width: 10px;
  max-width: 10px;
  background-color: #c9cdd4;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-f7bqu {
  font-size: 13px;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-09w5x {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-top: 3px;
  padding-bottom: 3px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-glg6n {
  display: flex;
  width: 18px;
  min-width: 18px;
  max-width: 18px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-4vro3 {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  min-width: 16px;
  max-width: 16px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-6k838 {
  width: 10px;
  height: 13px;
  min-width: 10px;
  max-width: 10px;
  background-color: #c9cdd4;
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  border-bottom-right-radius: 2px;
  border-bottom-left-radius: 2px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-span-hg7e5 {
  font-size: 13px;
  color: #1f2329;
  line-height: 1.6;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-vr9zw {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-658q9 {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-lxn0o {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 40px;
  min-width: 0;
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

.box-div-m77ss {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  justify-content: space-between;
  align-items: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-h2-vj1l1 {
  /* 【标题横排修复】右栏"文件"标题同类防护，与左栏"仓库"保持一致的抗挤压策略 */
  white-space: nowrap;
  flex-shrink: 0;
  font-size: 20px;
  font-weight: 600;
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

.box-div-doxym {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: 312px;
  max-width: 420px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-input-d8soa {
  flex-grow: 1;
  height: 32px;
  font-size: 14px;
  color: #1f2329;
  background-color: #ffffff;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-qo5zs {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 28px;
  height: 28px;
  min-width: 28px;
  max-width: 28px;
  font-size: 24px;
  color: #1f2329;
  background-color: transparent;
  border-style: none;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-3vr0j {
  display: flex;
  flex-direction: column;
  gap: 0px;
  width: 100%;
  flex-grow: 1;
  min-height: 320px;
  overflow: hidden;
  min-width: 0;
  background-color: #ffffff;
  border-style: solid;
  border-color: #e5e6eb;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-v9680 {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  width: 100%;
  flex-grow: 0;
  min-width: 0;
  background-color: #f7f8fa;
  border-style: solid;
  border-color: #e5e6eb;
  border-top-width: 0px;
  border-right-width: 0px;
  border-bottom-width: 1px;
  border-left-width: 0px;
  padding-top: 8px;
  padding-right: 12px;
  padding-bottom: 8px;
  padding-left: 12px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-hcg8q {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  width: auto;
  flex-grow: 1;
  min-width: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-hh5m7 {
  font-size: 12px;
  color: #86909c;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-span-lnm96 {
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: nowrap;
  overflow: hidden;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-button-r9cwr {
  flex-grow: 0;
  font-size: 12px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 4px;
  padding-right: 12px;
  padding-bottom: 4px;
  padding-left: 12px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-17sf6 {
  display: flex;
  flex-direction: column;
  gap: 0px;
  width: 100%;
  flex-grow: 1;
  min-height: 0px;
  overflow: auto;
  min-width: 0;
  padding-top: 12px;
  padding-right: 12px;
  padding-bottom: 12px;
  padding-left: 12px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-1h6hh {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-q27t4 {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-88tv2 {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-2lwxj {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-yddze {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-v2vir {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-awr4j {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-17zvq {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-z5gl2 {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-xmoh1 {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-cxcso {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-a2zqc {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-gpl47 {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-ryp1k {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-v44gs {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-i36d7 {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-s0egu {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-gsv7s {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-l12sc {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-pxruf {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-569sa {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-t5ojv {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-l00nk {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-6obct {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-f9bgg {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-8y6h8 {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-nx2o0 {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-g4jbo {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-r50z5 {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-ccu5y {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-jj86g {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-i5dzj {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-s5e3n {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-div-ij43m {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding-top: 2px;
  padding-bottom: 2px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-vwtzw {
  width: 24px;
  min-width: 24px;
  text-align: right;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #86909c;
  line-height: 1.6;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

.box-span-f7x0w {
  flex-grow: 1;
  min-width: 0px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #1f2329;
  line-height: 1.6;
  white-space: pre-wrap;
  min-height: 19px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  gap: 8px;
}

/* ===== 仓库文件树 / 编辑区样式 ===== */
.repo-node {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-top: 3px;
  padding-bottom: 3px;
  font-size: 13px;
}
.repo-toggle {
  width: 18px;
  min-width: 18px;
  font-size: 12px;
  color: #4e5969;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}
.repo-toggle-placeholder {
  display: inline-block;
  width: 18px;
  min-width: 18px;
}
.repo-icon {
  font-size: 13px;
}
.repo-name {
  cursor: pointer;
  color: #1f2329;
}
.repo-name.active {
  color: var(--primary);
  font-weight: 600;
}
.repo-editor {
  width: 100%;
  height: 100%;
  min-height: 300px;
  border: none;
  outline: none;
  resize: none;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2329;
  box-sizing: border-box;
}
/* ===== CodeMirror 编辑器挂载点 ===== */
.repo-editor-host {
  width: 100%;
  height: 100%;
  min-height: 300px;
  overflow: auto;
}
.repo-editor-host :deep(.CodeMirror) {
  height: 100%;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 14px;
  line-height: 1.6;
}
.repo-editor-host :deep(.CodeMirror-gutters) {
  border-right: 1px solid #e4e7ed;
  background: #f7f8fa;
}
/* ===== Markdown 渲染预览 ===== */
.repo-md-preview {
  width: 100%;
  height: 100%;
  overflow: auto;
  padding: 16px 20px;
  font-size: 14px;
  line-height: 1.7;
  color: #1f2329;
  box-sizing: border-box;
  background: #ffffff;
}
.repo-md-preview :deep(h1),
.repo-md-preview :deep(h2),
.repo-md-preview :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
}
.repo-md-preview :deep(table) {
  border-collapse: collapse;
  margin: 12px 0;
}
.repo-md-preview :deep(th),
.repo-md-preview :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 6px 12px;
}
.repo-md-preview :deep(pre) {
  background: #f7f8fa;
  padding: 12px;
  border-radius: 4px;
  overflow: auto;
}
.repo-md-preview :deep(code) {
  font-family: Consolas, Monaco, "Courier New", monospace;
}

/* ===== 右键菜单（对齐旧页 web_file_repo.html） ===== */
.repo-ctxmenu {
  position: fixed;
  z-index: 3000;
  min-width: 150px;
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  padding: 4px 0;
}
.repo-ctxmenu-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #1f2329;
  cursor: pointer;
  white-space: nowrap;
}
.repo-ctxmenu-item:hover {
  background: #f2f7ff;
  color: var(--primary);
}
.repo-ctxmenu-item.danger {
  color: #f56c6c;
}
.repo-ctxmenu-item.danger:hover {
  background: #fff1f0;
}
/* ===== 隔离标记 ===== */
.repo-isolated-flag {
  font-size: 12px;
  color: #f56c6c;
  margin-left: 6px;
}
.repo-name.isolated {
  opacity: 0.6;
}
/* ===== 预览区（对齐旧页 file_editor.html） ===== */
.repo-toolbar-actions {
  display: flex;
  gap: 8px;
}
.repo-preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  padding: 40px 0;
  text-align: center;
}
.repo-preview-center {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  overflow: auto;
  padding: 8px;
}
.repo-preview-center img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.repo-preview-center video {
  max-width: 100%;
  max-height: 100%;
}
.repo-preview-fill {
  height: 100%;
}
.repo-preview-fill iframe {
  width: 100%;
  height: 100%;
  border: none;
}
.repo-preview-hex {
  height: 100%;
  overflow: auto;
  padding: 12px;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre;
}
.hex-line {
  display: flex;
  gap: 20px;
}
.hex-offset {
  color: #909399;
  width: 76px;
}
.hex-bytes {
  color: #303133;
  width: 370px;
  letter-spacing: 1px;
}
.hex-ascii {
  color: #606266;
}
.hex-tip {
  color: #909399;
  margin-top: 16px;
}
</style>
