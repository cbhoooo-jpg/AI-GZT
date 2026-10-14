<!--
  页面《6》　路由:/6（6）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-y3bin">
    <div class="box-div-b4hzb">
      <div class="box-div-4m7th">
        <div class="box-div-nm567">
          <h2 class="box-h2-uady6">操作日志</h2>
          <button class="box-button-ytudm" type="button" @click="handleClear">清空日志</button>
        </div>
        <div class="box-div-tvgxh">
          <div v-for="log in logList" :key="log.id" class="log-item">
            <div class="log-content">
              <span :class="['log-type', getTypeClass(log.oper_type)]">{{ log.oper_type }}</span>
              <span :class="['log-status', log.status]">{{ log.content }}</span>
            </div>
            <span class="log-time">{{ log.oper_time }}</span>
          </div>
          <div v-if="logList.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无操作日志</div>
        </div>
        <div class="box-div-sqo4m">
          <span class="box-span-i1e7n">共 {{ total }} 条</span>
          <select class="box-select-td44z" v-model.number="pageSize" @change="handleSizeChange">
            <option :value="20">20条/页</option>
            <option :value="50">50条/页</option>
            <option :value="100">100条/页</option>
          </select>
          <div class="box-div-bj619">
            <button class="box-button-938xb" type="button" :disabled="page <= 1" @click="handlePrev">上一页</button>
            <template v-for="(p, idx) in pageNumbers" :key="idx">
              <span v-if="p === '...'" class="box-span-page-dots">…</span>
              <button
                v-else
                class="box-button-page"
                :class="{ 'box-button-page-active': p === page }"
                type="button"
                @click="handleGoPage(p)"
              >{{ p }}</button>
            </template>
            <button class="box-button-f94ur" type="button" :disabled="page >= totalPages" @click="handleNext">下一页</button>
          </div>
          <div class="box-div-jump">
            <span>前往</span>
            <input
              class="box-input-jump"
              type="number"
              min="1"
              :max="totalPages"
              v-model.number="jumpPage"
              @keyup.enter="handleJump"
              @blur="handleJump"
            />
            <span>页</span>
            <button class="box-button-jump" type="button" @click="handleJump">跳转</button>
          </div>
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

/** 日志条目结构（与后端 /api/log/list 返回的 list 项对齐） */
interface LogItem {
  id: number
  oper_type: string
  content: string
  status: string
  oper_time: string
}

const logList = ref<LogItem[]>([])
const keyword = ref('')
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const lastMaxId = ref(0)
const isLoading = ref(false)
let pollingTimer: ReturnType<typeof setInterval> | null = null

/** 总页数（用于下一页按钮禁用判断） */
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

/** 跳页输入框绑定值（始终等于当前页，翻页后自动同步） */
const jumpPage = ref(1)

/**
 * 数字页码列表（对齐旧页 web_log.html 的 el-pagination 表现，最多 7 个元素含省略号）
 * - 总页数 ≤ 7:全量列出
 * - 当前页靠前（cur ≤ 4）:1 2 3 4 5 … tp
 * - 当前页靠后（cur ≥ tp-3）:1 … tp-4 tp-3 tp-2 tp-1 tp
 * - 居中:1 … cur-1 cur cur+1 … tp
 */
const pageNumbers = computed<(number | string)[]>(() => {
  const tp = totalPages.value
  const cur = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  if (cur <= 4) return [1, 2, 3, 4, 5, '...', tp]
  if (cur >= tp - 3) return [1, '...', tp - 4, tp - 3, tp - 2, tp - 1, tp]
  return [1, '...', cur - 1, cur, cur + 1, '...', tp]
})

/** 全量加载日志（翻页 / 搜索 / 清空后调用） */
async function loadLogs() {
  try {
    const data = await get<{ list: LogItem[]; total: number }>('/api/log/list', {
      keyword: keyword.value,
      page: page.value,
      page_size: pageSize.value,
    })
    logList.value = data.list || []
    total.value = data.total || 0
    // 同步跳页输入框（保证「上一页/下一页/跳页/切条数」后输入框始终等于当前页）
    jumpPage.value = page.value
    if (logList.value.length > 0) {
      lastMaxId.value = Math.max(...logList.value.map((log) => log.id))
    }
    await nextTick()
    const logEl = document.querySelector('.box-div-tvgxh') as HTMLElement | null
    // 方案B:仅当滚动位置在顶部 200px 内时才自动滚到顶部（用户往下翻看历史日志时不强制拉回）
    if (logEl && logEl.scrollTop <= 200) logEl.scrollTop = 0
  } catch (e) {
    console.error('加载日志失败', e)
  }
}

/** 增量加载新日志（轮询调用，低延时；搜索 / 非第一页 / 请求中时跳过） */
async function loadIncrementLogs() {
  if (keyword.value || page.value !== 1 || isLoading.value) return
  isLoading.value = true
  try {
    const data = await get<{ list: LogItem[]; current_total?: number }>('/api/log/list', {
      last_id: lastMaxId.value,
      page_size: 100,
    })
    const newLogs = data.list || []
    if (newLogs.length > 0) {
      logList.value.unshift(...newLogs)
      lastMaxId.value = Math.max(...newLogs.map((log) => log.id), lastMaxId.value)
      total.value =
        typeof data.current_total === 'number' ? data.current_total : total.value + newLogs.length
      if (logList.value.length > pageSize.value) {
        logList.value = logList.value.slice(0, pageSize.value)
      }
      await nextTick()
      const logEl = document.querySelector('.box-div-tvgxh') as HTMLElement | null
      // 方案B:仅当滚动位置在顶部 200px 内时才自动滚到顶部（用户往下翻看历史日志时不强制拉回）
      if (logEl && logEl.scrollTop <= 200) logEl.scrollTop = 0
    }
  } catch (e) {
    console.error('增量加载日志失败', e)
  } finally {
    isLoading.value = false
  }
}

/** 启动 / 停止 1s 轮询（页面隐藏时停止，避免后台积压请求） */
function startPolling() {
  if (pollingTimer) return
  pollingTimer = setInterval(loadIncrementLogs, 1000)
}
function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}
function handleVisibilityChange() {
  if (document.hidden) stopPolling()
  else startPolling()
}

/** 切换每页条数:回第一页并全量刷新 */
function handleSizeChange() {
  page.value = 1
  loadLogs()
}
function handlePrev() {
  if (page.value > 1) {
    page.value -= 1
    loadLogs()
  }
}
function handleNext() {
  if (page.value < totalPages.value) {
    page.value += 1
    loadLogs()
  }
}

/** 点击数字页码跳转到指定页 */
function handleGoPage(p: number | string) {
  const n = Number(p)
  if (!Number.isFinite(n) || n === page.value) return
  page.value = n
  loadLogs()
}

/** 跳页输入框回车 / 失焦 / 点击「跳转」按钮时触发（越界自动夹到 1 ~ totalPages） */
function handleJump() {
  let n = Number(jumpPage.value)
  if (!Number.isFinite(n) || n < 1) n = 1
  if (n > totalPages.value) n = totalPages.value
  jumpPage.value = n
  if (n === page.value) return
  page.value = n
  loadLogs()
}

/** 清空全部日志 */
async function handleClear() {
  if (!window.confirm('确定要清空所有操作日志吗？')) return
  try {
    await post('/api/log/clear')
    page.value = 1
    await loadLogs()
  } catch (e) {
    console.error('清空日志失败', e)
  }
}

/** 按操作类型映射标签配色（与旧页 web_log.html 规则一致） */
function getTypeClass(type: string) {
  if (!type) return 'log'
  if (type.includes('错误') || type.includes('失败') || type.includes('异常')) return 'error'
  if (type.includes('文件')) return 'file'
  if (type.includes('配置')) return 'config'
  if (type.includes('项目')) return 'project'
  if (type.includes('AI') || type.includes('ai')) return 'ai'
  return 'log'
}

onMounted(() => {
  loadLogs()
  startPolling()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})
onBeforeUnmount(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.box-div-y3bin {
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

.box-div-b4hzb {
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

.box-div-4m7th {
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

.box-div-nm567 {
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

.box-h2-uady6 {
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

.box-button-ytudm {
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

.box-div-tvgxh {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  height: 320px;
  min-height: 0px;
  flex-grow: 1;
  overflow: auto;
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

.box-div-sqo4m {
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

.box-span-i1e7n {
  font-size: 14px;
  color: #1f2329;
  width: auto;
  min-width: 78px;
  height: 21px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-select-td44z {
  width: 128px;
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

.box-div-bj619 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-938xb {
  font-size: 14px;
  color: #4e5969;
  background-color: #f2f3f5;
  border-style: none;
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

.box-button-1pe1i {
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
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

/* ===== 数字页码 / 省略号 / 跳页区（对齐旧页 web_log.html 的 el-pagination 表现） ===== */
.box-button-page {
  min-width: 28px;
  font-size: 14px;
  color: #4e5969;
  background-color: #f2f3f5;
  border-style: none;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  cursor: pointer;
}

.box-button-page:hover {
  background-color: #e5e6eb;
}

.box-button-page-active,
.box-button-page-active:hover {
  color: #ffffff;
  background-color: var(--primary);
}

.box-span-page-dots {
  font-size: 14px;
  color: #86909c;
  padding-top: 0;
  padding-right: 4px;
  padding-bottom: 0;
  padding-left: 4px;
  user-select: none;
}

.box-div-jump {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #4e5969;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

.box-input-jump {
  width: 48px;
  height: 32px;
  font-size: 14px;
  color: #1f2329;
  text-align: center;
  background-color: #ffffff;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  outline: none;
  box-sizing: border-box;
}

.box-input-jump:focus {
  border-color: var(--primary);
}

.box-button-jump {
  font-size: 14px;
  color: #4e5969;
  background-color: #f2f3f5;
  border-style: none;
  padding-top: 6px;
  padding-right: 10px;
  padding-bottom: 6px;
  padding-left: 10px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  cursor: pointer;
}

.box-button-jump:hover {
  background-color: #e5e6eb;
}

.box-button-f94ur {
  font-size: 14px;
  color: #4e5969;
  background-color: #f2f3f5;
  border-style: none;
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

/* ===== 日志条目样式（对齐旧页 web_log.html） ===== */
.log-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.log-item:last-child {
  border-bottom: none;
}
.log-item:hover {
  background: #f7f8fa;
}
.log-content {
  flex: 1;
  font-size: 14px;
  color: #333;
  line-height: 1.5;
}
.log-type {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #ffffff;
  margin-right: 8px;
}
.log-type.file { background: #67c23a; }
.log-type.config { background: #e6a23c; }
.log-type.project { background: #409eff; }
.log-type.log { background: #909399; }
.log-type.ai { background: #9c27b0; }
.log-type.error { background: #f56c6c; }
.log-status.error { color: #f56c6c; font-weight: bold; }
.log-status.success { color: #67c23a; font-weight: bold; }
.log-time {
  font-size: 12px;
  color: #999999;
  white-space: nowrap;
  margin-left: 16px;
}
</style>
