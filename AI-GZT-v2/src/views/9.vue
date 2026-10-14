<!--
  页面《9》　路由:/9（9）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-u6w0e">
    <div class="box-div-dda69">
      <div class="box-div-hhgcv">
        <span class="box-span-613cz"></span>
        <span class="box-span-us3zf">记忆库</span>
        <button class="box-button-6d5l8" type="button" @click="goPage9()" :class="{ 'lc-nav-active': route.path === '/9' }">全库记忆</button>
        <button class="box-button-edvrj" type="button" @click="goPage16()" :class="{ 'lc-nav-active': route.path === '/1-6' }">记忆库管理</button>
        <button class="box-button-rzvxe" type="button" @click="goPage26()" :class="{ 'lc-nav-active': route.path === '/2-6' }">记忆文件管理</button>
        <button class="box-button-qipuj" type="button" @click="goPage35()" :class="{ 'lc-nav-active': route.path === '/3-5' }">召回实时观测</button>
      </div>
      <div class="box-div-x74l9">
        <div class="box-div-be9mj">
          <div class="box-div-hsirm">
            <div class="box-div-rk9uq">
              <div class="box-div-cn4i0">
                <input class="box-input-3bhr9" type="text" placeholder="请输入关键词" v-model="keyword" @keyup.enter="handleSearch" />
                <button class="box-button-h2c9v" type="button" @click="handleSearch">⌕</button>
              </div>
              <button class="box-button-vvrv0" type="button" @click="loadMemories">刷新</button>
            </div>
            <div class="box-div-5dqu9">
              <div v-for="mem in memories" :key="mem.id" class="mem-item">
                <div class="mem-item-head">
                  <span class="mem-index">#{{ mem.id }}</span>
                  <span class="mem-count">调用 {{ mem.call_count }} 次</span>
                  <span class="mem-sync" :class="mem.synced_to_lora ? 'synced' : 'unsynced'">{{ mem.synced_to_lora ? '已同步' : '未同步' }}</span>
                  <span class="mem-time">{{ mem.create_time }}</span>
                  <button class="mem-del" type="button" @click="deleteMemory(mem.id)">删除</button>
                </div>
                <div class="mem-query"><span class="mem-label">问:</span>{{ mem.query }}</div>
                <div class="mem-response"><span class="mem-label">答:</span>{{ mem.response }}</div>
              </div>
              <div v-if="memories.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无记忆记录</div>
            </div>
            <div class="box-div-xm017">
              <span class="mem-total">共 {{ total }} 条</span>
              <div class="box-div-68xqb">
                <button class="box-button-6l3hs" type="button" :disabled="page <= 1" @click="handlePrev">上一页</button>
                <button class="box-button-kqau9" type="button">{{ page }}</button>
                <button class="box-button-ifp1x" type="button" :disabled="page >= totalPages" @click="handleNext">下一页</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPage9() {
  router.push('/9')
}

function goPage16() {
  router.push('/1-6')
}

function goPage26() {
  router.push('/2-6')
}

function goPage35() {
  router.push('/3-5')
}

/** 记忆条目结构（与后端 /api/memory/list 返回的 memories 项对齐） */
interface MemoryItem {
  id: number
  query: string
  response: string
  call_count: number
  synced_to_lora: boolean
  create_time: string
  timestamp: number
}

const memories = ref<MemoryItem[]>([])
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

/** 总页数（用于下一页按钮禁用判断） */
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

/** 加载全库记忆列表（后端返回裸对象，非 {code,msg,data}，故用原生 fetch 与旧页一致） */
async function loadMemories() {
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize.value),
      keyword: keyword.value,
    })
    const res = await fetch(`/api/memory/list?${params.toString()}`)
    const data = await res.json()
    memories.value = data.memories || []
    total.value = data.total || 0
  } catch (e) {
    console.error('加载记忆失败', e)
  }
}

/** 搜索:回到第一页并刷新 */
function handleSearch() {
  page.value = 1
  loadMemories()
}
function handlePrev() {
  if (page.value > 1) {
    page.value -= 1
    loadMemories()
  }
}
function handleNext() {
  if (page.value < totalPages.value) {
    page.value += 1
    loadMemories()
  }
}

/** 删除单条记忆（删除后自动刷新当前页） */
async function deleteMemory(id: number) {
  if (!window.confirm('确定要删除这条记忆吗？删除后不可恢复')) return
  try {
    await fetch('/api/memory/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    })
    await loadMemories()
  } catch (e) {
    console.error('删除记忆失败', e)
  }
}

onMounted(loadMemories)
</script>

<style scoped>
.box-div-u6w0e {
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

.box-div-dda69 {
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

.box-div-hhgcv {
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

.box-span-613cz {
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

.box-span-us3zf {
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

.box-button-6d5l8 {
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

.box-button-edvrj {
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

.box-button-rzvxe {
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

.box-button-qipuj {
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

.box-div-x74l9 {
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

.box-div-be9mj {
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

.box-div-hsirm {
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

.box-div-rk9uq {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-cn4i0 {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 420px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-input-3bhr9 {
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

.box-button-h2c9v {
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

.box-button-vvrv0 {
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

.box-div-5dqu9 {
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

.box-div-xm017 {
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

.box-div-68xqb {
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

.box-button-6l3hs {
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

.box-button-kqau9 {
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

.box-button-ifp1x {
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

/* ===== 记忆条目样式（对齐旧页 sample.html 全库记忆展示） ===== */
.mem-item {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.mem-item:last-child {
  border-bottom: none;
}
.mem-item:hover {
  background: #f7f8fa;
}
.mem-item-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #909399;
}
.mem-index {
  font-weight: 600;
  color: var(--primary);
}
.mem-sync {
  padding: 2px 8px;
  border-radius: 4px;
}
.mem-sync.synced {
  background: #f6ffed;
  color: #52c41a;
}
.mem-sync.unsynced {
  background: #f2f3f5;
  color: #909399;
}
.mem-time {
  margin-left: auto;
}
.mem-del {
  height: 24px;
  font-size: 12px;
  color: #ffffff;
  background-color: #f56c6c;
  border-style: none;
  padding: 0 10px;
  border-radius: 4px;
  cursor: pointer;
}
.mem-query,
.mem-response {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  word-break: break-all;
}
.mem-response {
  color: #4e5969;
}
.mem-label {
  color: var(--primary);
  font-weight: 600;
  margin-right: 6px;
}
.mem-total {
  font-size: 12px;
  color: #909399;
}
</style>
