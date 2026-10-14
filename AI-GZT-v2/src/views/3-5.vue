<!--
  页面《3》　路由:/3-5（35）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout9>
  <div class="box-div-crmav">
    <div class="box-div-udk8g">
      <div class="box-div-hcpll">
        <div class="box-div-x0e7w">
          <span class="obs-status" :style="{ color: statusColor }">{{ statusText }}</span>
          <span class="obs-stats">{{ statsText }}</span>
          <label class="obs-filter">
            <input type="checkbox" v-model="onlyHit" />
            只看已触发
          </label>
          <button class="box-button-wktba" type="button" @click="refresh">刷新</button>
          <button class="box-button-12g6w" type="button" @click="clearTimeline">清空</button>
        </div>
        <div class="box-div-5wybs">
          <div v-for="snap in visibleSnaps" :key="snap.id" class="obs-item">
            <div class="obs-item-head">
              <span class="obs-time">[{{ snap.time_str }}]</span>
              <span class="obs-query">{{ snap.query }}</span>
            </div>
            <div class="obs-item-meta">
              <span>项目:{{ snap.project }}</span>
              <span v-if="snap.triggered" class="obs-tag-hit">已触发召回 {{ (snap.memories || []).length }} 条</span>
              <span v-else class="obs-tag-miss">未触发</span>
              <span v-if="snap.reason">| {{ snap.reason }}</span>
            </div>
            <div v-for="mem in (snap.memories || [])" :key="mem.id" class="obs-mem">
              <div class="obs-mem-meta">
                相似度 {{ mem.similarity != null ? mem.similarity + '%' : '-' }} | 排序分 {{ mem.recall_score != null ? mem.recall_score : '-' }} | {{ (mem.tags || []).filter((t) => !t.startsWith('session:') && !t.startsWith('project:')).join(',') }}
              </div>
              <div class="obs-mem-content">{{ mem.content }}</div>
              <div class="obs-mem-actions">
                <button class="obs-btn obs-btn-relevant" :class="{ active: getLabel(snap, mem.id) === 1 }" type="button" @click="evalRecall(snap.id, mem.id, 1)">相关</button>
                <button class="obs-btn obs-btn-irrelevant" :class="{ active: getLabel(snap, mem.id) === 0 }" type="button" @click="evalRecall(snap.id, mem.id, 0)">不相关</button>
              </div>
            </div>
          </div>
          <div v-if="visibleSnaps.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无符合条件的观测记录</div>
        </div>
      </div>
    </div>
  </div>
  </Layout9>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout9 from '@/layouts/Layout9.vue'

/** 召回到的单条记忆 */
interface RecallMemory {
  id: string | number
  similarity?: number
  recall_score?: number
  tags?: string[]
  content: string
}

/** 单次提问的召回快照（与后端 /api/memory/recall/recent 返回项对齐） */
interface RecallSnapshot {
  id: string
  time_str: string
  query: string
  project: string
  triggered: boolean
  reason?: string
  memories: RecallMemory[]
  evaluations?: Record<string, { label: number; time: string }>
}

/** 观测统计（与后端 /api/memory/recall/stats 返回对齐） */
interface RecallStats {
  total_observations: number
  triggered_count: number
  trigger_rate: number
  evaluated_count: number
  relevant_count: number
  irrelevant_count: number
  hit_rate: number | null
}

const snaps = ref<RecallSnapshot[]>([])
const stats = ref<RecallStats | null>(null)
const onlyHit = ref(false)
const statusText = ref('等待连接...')
const statusColor = ref('#86909c')
let es: EventSource | null = null

/** 统计条文案 */
const statsText = computed(() => {
  const s = stats.value
  if (!s) return ''
  const hit = s.hit_rate == null ? '-' : s.hit_rate + '%'
  return `观测 ${s.total_observations} 次 | 召回触发率 ${s.trigger_rate}% | 已标注 ${s.evaluated_count} 条 | 命中率 ${hit}`
})

/** 按「只看已触发」筛选后的快照 */
const visibleSnaps = computed(() =>
  onlyHit.value ? snaps.value.filter((s) => s.triggered) : snaps.value,
)

/** 读取某条记忆的当前标注档位（1=相关 0=不相关 null=未标注） */
function getLabel(snap: RecallSnapshot, memoryId: string | number): number | null {
  const ev = (snap.evaluations || {})[String(memoryId)]
  return ev ? ev.label : null
}

/** 拉取最近观测快照（后端返回裸对象，无 code，用原生 fetch） */
async function loadRecent() {
  try {
    const res = await fetch('/api/memory/recall/recent')
    const data = await res.json()
    snaps.value = data.snapshots || []
  } catch (e) {
    console.error('加载观测快照失败', e)
  }
}

/** 拉取统计指标（裸对象） */
async function loadStats() {
  try {
    const res = await fetch('/api/memory/recall/stats')
    stats.value = await res.json()
  } catch (e) {
    console.error('加载观测统计失败', e)
  }
}

/** 手动刷新:整页观测以 REST 重新拉取 */
function refresh() {
  loadRecent()
  loadStats()
}

/** 初始化 SSE 实时订阅（type: connected / recall_snapshot / heartbeat） */
function initSSE() {
  es = new EventSource('/api/memory/recall/stream')
  es.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.type === 'connected') {
      statusText.value = '● 实时已连接'
      statusColor.value = '#00b42a'
    } else if (m.type === 'recall_snapshot') {
      snaps.value.unshift(m.snapshot)
      if (snaps.value.length > 50) snaps.value.pop()
      loadStats()
    }
  }
  es.onerror = () => {
    statusText.value = '● 连接断开，重连中...'
    statusColor.value = '#f53f3f'
  }
}

/** 两档标注（重复点同档视为取消），提交后重拉快照刷新标注态 */
async function evalRecall(snapshotId: string, memoryId: string | number, label: number) {
  try {
    await fetch('/api/memory/recall/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ snapshot_id: snapshotId, memory_id: String(memoryId), label }),
    })
    await loadRecent()
  } catch (e) {
    console.error('标注失败', e)
  }
}

/** 清空观测时间线（已保存的标注不删除） */
async function clearTimeline() {
  if (!window.confirm('确定要清空观测时间线吗?已保存的标注不会被删除')) return
  try {
    await fetch('/api/memory/recall/clear', { method: 'DELETE' })
    snaps.value = []
    loadStats()
  } catch (e) {
    console.error('清空观测时间线失败', e)
  }
}

onMounted(() => {
  loadRecent()
  loadStats()
  initSSE()
})
onBeforeUnmount(() => {
  if (es) {
    es.close()
    es = null
  }
})
</script>

<style scoped>
.box-div-crmav {
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

.box-div-udk8g {
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

.box-div-hcpll {
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

.box-div-x0e7w {
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

.box-button-wktba {
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

.box-button-12g6w {
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

.box-div-5wybs {
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

/* ===== 召回实时观测样式（对齐旧页 sample.html 召回观测 Tab） ===== */
.box-div-x0e7w {
  gap: 16px;
}
.obs-status {
  font-size: 13px;
}
.obs-stats {
  font-size: 12px;
  color: #86909c;
}
.obs-filter {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #4e5969;
  cursor: pointer;
}
.obs-item {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.obs-item-head {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: #1f2329;
  font-weight: 500;
}
.obs-time {
  color: #86909c;
}
.obs-item-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #86909c;
  margin: 6px 0;
  flex-wrap: wrap;
}
.obs-tag-hit {
  color: #00b42a;
}
.obs-tag-miss {
  color: #f53f3f;
}
.obs-mem {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 10px;
  margin-top: 8px;
  background: #fcfcfc;
}
.obs-mem-meta {
  font-size: 12px;
  color: #888888;
  margin-bottom: 6px;
}
.obs-mem-content {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  color: #333333;
  max-height: 120px;
  overflow: auto;
}
.obs-mem-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.obs-btn {
  height: 26px;
  font-size: 12px;
  color: #4e5969;
  background: #ffffff;
  border: 1px solid #e5e6eb;
  border-radius: 4px;
  padding: 0 12px;
  cursor: pointer;
}
.obs-btn-relevant.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}
.obs-btn-irrelevant.active {
  background: #f53f3f;
  border-color: #f53f3f;
  color: #ffffff;
}
</style>
