<!--
  页面《7》　路由:/7（7）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-605ld">
    <div class="box-div-10o80">
      <div class="box-div-9q1cx">
        <div class="box-div-6czfh">
          <h2 class="box-h2-c1q7h">定时任务管理</h2>
          <div class="box-div-o3pms">
            <button class="box-button-b537u" type="button" @click="loadTasks">刷新任务</button>
            <button class="box-button-vmks5" type="button" @click="openCreateModal">新建任务</button>
          </div>
        </div>
        <div class="tk-main">
          <div class="tk-sidebar">
            <div class="tk-tabs">
              <div class="tk-tab" :class="{ active: currentTab === 'active' }" @click="switchTab('active')">进行中</div>
              <div class="tk-tab" :class="{ active: currentTab === 'completed' }" @click="switchTab('completed')">已完成</div>
              <div class="tk-tab" :class="{ active: currentTab === 'cancelled' }" @click="switchTab('cancelled')">已取消</div>
            </div>
            <div class="tk-list">
              <div
                v-for="task in filteredTasks"
                :key="task.id"
                class="tk-item"
                :class="{ active: task.id === currentTaskId, completed: task.status !== 'active' }"
                @click="selectTask(task.id)"
              >
                <div class="tk-item-header">
                  <span class="tk-item-name">{{ task.name }}</span>
                  <span class="tk-badge" :class="task.type === 'long_term' ? 'badge-long' : 'badge-once'">{{ task.type === 'long_term' ? '长期' : '一次性' }}</span>
                </div>
                <div class="tk-item-schedule">{{ formatSchedule(task) }}</div>
                <div class="tk-item-prompt">{{ task.prompt }}</div>
              </div>
              <div v-if="filteredTasks.length === 0" class="tk-empty">暂无任务</div>
            </div>
          </div>
          <div class="tk-content">
            <div v-if="!currentTask" class="tk-empty">请从左侧选择任务查看详情，或点击右上角新建任务</div>
            <div v-else class="tk-detail">
              <div class="tk-detail-header">
                <span class="tk-detail-title">{{ currentTask.name }}</span>
                <span class="tk-badge" :class="statusBadgeClass">{{ statusText }}</span>
              </div>
              <div class="tk-field">
                <label class="tk-field-label">执行计划</label>
                <div class="tk-field-value">{{ formatSchedule(currentTask) }}</div>
              </div>
              <div class="tk-field">
                <label class="tk-field-label">下次执行时间</label>
                <div class="tk-field-value">{{ currentTask.next_run_time || '无' }}</div>
              </div>
              <div class="tk-field">
                <label class="tk-field-label">任务提示词</label>
                <div class="tk-field-value tk-field-pre">{{ currentTask.prompt }}</div>
              </div>
              <div class="tk-field">
                <label class="tk-field-label">执行历史</label>
                <div class="tk-history">
                  <div v-for="(h, i) in (currentTask.history || [])" :key="i" class="tk-history-item">
                    <span>{{ h.executed_at }}</span>
                    <span class="tk-history-status" :class="h.status === 'success' ? 'status-success' : 'status-fail'">{{ h.status === 'success' ? '成功' : '失败' }}</span>
                  </div>
                  <div v-if="!currentTask.history || currentTask.history.length === 0" class="tk-empty-line">暂无执行记录</div>
                </div>
              </div>
              <div class="tk-actions">
                <template v-if="currentTask.status === 'active'">
                  <button class="tk-btn tk-btn-secondary" type="button" @click="editTask(currentTask.id)">编辑</button>
                  <button class="tk-btn tk-btn-danger" type="button" @click="cancelTask(currentTask.id)">取消任务</button>
                </template>
                <template v-else>
                  <button class="tk-btn tk-btn-danger" type="button" @click="deleteTask(currentTask.id)">删除</button>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- 新建 / 编辑弹窗 -->
        <div v-if="modalVisible" class="tk-modal-mask" @click.self="closeModal">
          <div class="tk-modal">
            <div class="tk-modal-header">
              <span class="tk-modal-title">{{ isEdit ? '编辑任务' : '新建定时任务' }}</span>
              <span class="tk-modal-close" @click="closeModal">×</span>
            </div>
            <div class="tk-modal-body">
              <div class="tk-form-group">
                <label class="tk-field-label">任务名称</label>
                <input class="tk-input" type="text" v-model="form.name" placeholder="例如:每日金融信息收集" />
              </div>
              <div class="tk-form-group">
                <label class="tk-field-label">任务类型</label>
                <select class="tk-input" v-model="form.type">
                  <option value="long_term">长期任务（周期执行）</option>
                  <option value="one_time">一次性任务（指定时间执行一次）</option>
                </select>
              </div>
              <div v-if="form.type === 'long_term'" class="tk-schedule-config">
                <div class="tk-form-row">
                  <div class="tk-form-group">
                    <label class="tk-field-label">执行频率</label>
                    <select class="tk-input" v-model="form.scheduleType">
                      <option value="daily">每天</option>
                      <option value="weekly">每周</option>
                      <option value="monthly">每月</option>
                      <option value="yearly">每年</option>
                    </select>
                  </div>
                  <div v-if="form.scheduleType === 'weekly'" class="tk-form-group">
                    <label class="tk-field-label">星期</label>
                    <select class="tk-input" v-model="form.weeklyDay">
                      <option v-for="(d, i) in weekDays" :key="i" :value="String(i)">{{ d }}</option>
                    </select>
                  </div>
                  <div v-if="form.scheduleType === 'monthly'" class="tk-form-group">
                    <label class="tk-field-label">日期</label>
                    <select class="tk-input" v-model="form.monthlyDay">
                      <option v-for="d in 28" :key="d" :value="String(d)">{{ d }}号</option>
                    </select>
                  </div>
                  <div v-if="form.scheduleType === 'yearly'" class="tk-form-group">
                    <label class="tk-field-label">月份</label>
                    <select class="tk-input" v-model="form.yearlyMonth">
                      <option v-for="m in 12" :key="m" :value="String(m)">{{ m }}月</option>
                    </select>
                  </div>
                  <div v-if="form.scheduleType === 'yearly'" class="tk-form-group">
                    <label class="tk-field-label">日期</label>
                    <select class="tk-input" v-model="form.yearlyDay">
                      <option v-for="d in 28" :key="d" :value="String(d)">{{ d }}号</option>
                    </select>
                  </div>
                </div>
                <div class="tk-form-row">
                  <div class="tk-form-group">
                    <label class="tk-field-label">小时 (0-23)</label>
                    <input class="tk-input" type="number" min="0" max="23" v-model.number="form.hour" />
                  </div>
                  <div class="tk-form-group">
                    <label class="tk-field-label">分钟 (0-59)</label>
                    <input class="tk-input" type="number" min="0" max="59" v-model.number="form.minute" />
                  </div>
                </div>
              </div>
              <div v-if="form.type === 'one_time'" class="tk-schedule-config">
                <div class="tk-form-group">
                  <label class="tk-field-label">执行时间</label>
                  <input class="tk-input" type="datetime-local" v-model="form.runDate" />
                </div>
              </div>
              <div class="tk-form-group">
                <label class="tk-field-label">任务提示词 (Prompt)</label>
                <textarea class="tk-input tk-textarea" v-model="form.prompt" placeholder="例如:请收集今日金融方面的最新信息"></textarea>
              </div>
            </div>
            <div class="tk-modal-footer">
              <button class="tk-btn tk-btn-secondary" type="button" @click="closeModal">取消</button>
              <button class="tk-btn tk-btn-primary" type="button" @click="saveTask">保存任务</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'

/** 调度配置（与 scheduler_manager 返回口径对齐） */
interface TaskSchedule {
  trigger_type?: string
  hour?: number | string
  minute?: number | string
  day_of_week?: string
  day?: number | string
  month?: number | string
  run_date?: string
}

/** 执行历史项 */
interface TaskHistory {
  executed_at: string
  status: string
}

/** 定时任务结构 */
interface Task {
  id: string
  name: string
  type: 'long_term' | 'one_time'
  status: 'active' | 'completed' | 'cancelled'
  prompt: string
  schedule: TaskSchedule
  next_run_time?: string
  history?: TaskHistory[]
}

type TabKey = 'active' | 'completed' | 'cancelled'
type ScheduleType = 'daily' | 'weekly' | 'monthly' | 'yearly'

const tasks = ref<Task[]>([])
const currentTab = ref<TabKey>('active')
const currentTaskId = ref<string | null>(null)
const modalVisible = ref(false)
const isEdit = ref(false)
const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

/** 新建 / 编辑表单（扁平结构，便于双向绑定） */
const form = ref({
  name: '',
  type: 'long_term' as 'long_term' | 'one_time',
  prompt: '',
  scheduleType: 'daily' as ScheduleType,
  weeklyDay: '0',
  monthlyDay: '1',
  yearlyMonth: '1',
  yearlyDay: '1',
  hour: 9,
  minute: 0,
  runDate: '',
})

const filteredTasks = computed(() => tasks.value.filter((t) => t.status === currentTab.value))
const currentTask = computed(() => tasks.value.find((t) => t.id === currentTaskId.value) || null)
const statusText = computed(() => {
  const t = currentTask.value
  if (!t) return ''
  if (t.status === 'completed') return '已完成'
  if (t.status === 'cancelled') return '已取消'
  return t.type === 'long_term' ? '长期' : '一次性'
})
const statusBadgeClass = computed(() => {
  const t = currentTask.value
  if (!t) return 'badge-once'
  if (t.status === 'completed') return 'badge-done'
  if (t.status === 'cancelled') return 'badge-cancel'
  return t.type === 'long_term' ? 'badge-long' : 'badge-once'
})

/** 加载任务列表（后端返回裸数组，非 {code,msg,data}，故用原生 fetch 与旧页一致） */
async function loadTasks() {
  try {
    const res = await fetch('/api/scheduler/tasks')
    tasks.value = await res.json()
  } catch (e) {
    console.error('加载任务失败', e)
  }
}

function switchTab(tab: TabKey) {
  currentTab.value = tab
}

function selectTask(id: string) {
  currentTaskId.value = id
}

/** 格式化执行计划（对齐旧页 formatSchedule） */
function formatSchedule(task: Task): string {
  if (task.type === 'one_time') return String(task.schedule?.run_date ?? '')
  const s = task.schedule || {}
  if (s.trigger_type === 'cron') {
    let freq = ''
    if (s.day_of_week === '*') freq = '每天'
    else if (s.day_of_week !== undefined && s.day_of_week !== '') freq = weekDays[Number(s.day_of_week)] || ''
    else if (s.month) freq = `每年${s.month}月${s.day}号`
    else if (s.day) freq = `每月${s.day}号`
    const hh = String(s.hour ?? 0).padStart(2, '0')
    const mm = String(s.minute ?? 0).padStart(2, '0')
    return `${freq} ${hh}:${mm}`.trim()
  }
  return '未知'
}

/** 打开新建弹窗（重置表单） */
function openCreateModal() {
  isEdit.value = false
  currentTaskId.value = null
  form.value = {
    name: '',
    type: 'long_term',
    prompt: '',
    scheduleType: 'daily',
    weeklyDay: '0',
    monthlyDay: '1',
    yearlyMonth: '1',
    yearlyDay: '1',
    hour: 9,
    minute: 0,
    runDate: '',
  }
  modalVisible.value = true
}

/** 打开编辑弹窗（回填任务数据） */
function editTask(id: string) {
  const task = tasks.value.find((t) => t.id === id)
  if (!task) return
  isEdit.value = true
  currentTaskId.value = id
  const s = task.schedule || {}
  const st: ScheduleType =
    s.day_of_week === '*'
      ? 'daily'
      : s.day_of_week !== undefined && s.day_of_week !== ''
        ? 'weekly'
        : s.month
          ? 'yearly'
          : 'monthly'
  form.value = {
    name: task.name,
    type: task.type,
    prompt: task.prompt,
    scheduleType: st,
    weeklyDay: String(s.day_of_week ?? '0'),
    monthlyDay: String(s.day ?? '1'),
    yearlyMonth: String(s.month ?? '1'),
    yearlyDay: String(s.day ?? '1'),
    hour: Number(s.hour ?? 9),
    minute: Number(s.minute ?? 0),
    runDate: task.type === 'one_time' ? String(s.run_date ?? '').substring(0, 16) : '',
  }
  modalVisible.value = true
}

function closeModal() {
  modalVisible.value = false
}

/** 保存任务（新建走 POST，编辑走 PUT，均返回裸 JSON，用 res.ok 判断） */
async function saveTask() {
  if (!form.value.name.trim() || !form.value.prompt.trim()) {
    window.alert('请填写任务名称和提示词')
    return
  }
  let schedule: TaskSchedule = {}
  if (form.value.type === 'long_term') {
    schedule = { trigger_type: 'cron', hour: form.value.hour, minute: form.value.minute }
    if (form.value.scheduleType === 'daily') schedule.day_of_week = '*'
    else if (form.value.scheduleType === 'weekly') schedule.day_of_week = form.value.weeklyDay
    else if (form.value.scheduleType === 'monthly') schedule.day = form.value.monthlyDay
    else if (form.value.scheduleType === 'yearly') {
      schedule.month = form.value.yearlyMonth
      schedule.day = form.value.yearlyDay
    }
  } else {
    if (!form.value.runDate) {
      window.alert('请选择执行时间')
      return
    }
    schedule = { trigger_type: 'date', run_date: form.value.runDate }
  }
  const payload = {
    name: form.value.name,
    type: form.value.type,
    schedule,
    prompt: form.value.prompt,
    status: 'active',
  }
  try {
    let res: Response
    if (isEdit.value && currentTaskId.value) {
      res = await fetch(`/api/scheduler/tasks/${currentTaskId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } else {
      res = await fetch('/api/scheduler/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    }
    if (res.ok) {
      modalVisible.value = false
      await loadTasks()
    } else {
      window.alert('保存失败')
    }
  } catch (e) {
    console.error('保存任务失败', e)
  }
}

/** 取消任务 */
async function cancelTask(id: string) {
  if (!window.confirm('确定要取消此任务吗？')) return
  try {
    await fetch(`/api/scheduler/tasks/${id}/cancel`, { method: 'POST' })
    await loadTasks()
  } catch (e) {
    console.error('取消任务失败', e)
  }
}

/** 删除任务 */
async function deleteTask(id: string) {
  if (!window.confirm('确定要删除此任务吗？此操作不可恢复')) return
  try {
    await fetch(`/api/scheduler/tasks/${id}`, { method: 'DELETE' })
    currentTaskId.value = null
    await loadTasks()
  } catch (e) {
    console.error('删除任务失败', e)
  }
}

onMounted(loadTasks)
</script>

<style scoped>
.box-div-605ld {
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

.box-div-10o80 {
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

.box-div-9q1cx {
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

.box-div-6czfh {
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

.box-h2-c1q7h {
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

.box-div-o3pms {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 556px;
  min-height: 40px;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-b537u {
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

.box-button-vmks5 {
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

/* ===== 定时任务页样式（对齐旧页 web_scheduler.html） ===== */
.tk-main {
  display: flex;
  flex-direction: row;
  gap: 12px;
  flex-grow: 1;
  min-height: 0;
}
.tk-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}
.tk-tabs {
  display: flex;
  border-bottom: 1px solid #e9ecef;
}
.tk-tab {
  flex: 1;
  padding: 12px;
  text-align: center;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.tk-tab:hover {
  background-color: #f7f8fa;
}
.tk-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}
.tk-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.tk-item {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
}
.tk-item:hover {
  border-color: var(--primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.tk-item.active {
  border-color: var(--primary);
  background-color: #f2f7ff;
}
.tk-item.completed {
  opacity: 0.6;
}
.tk-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.tk-item-name {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}
.tk-item-schedule {
  font-size: 12px;
  color: #888;
}
.tk-item-prompt {
  font-size: 12px;
  color: #666;
  margin-top: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tk-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.badge-long {
  background-color: #e8f1ff;
  color: var(--primary);
}
.badge-once {
  background-color: #fff7e6;
  color: #fa8c16;
}
.badge-done {
  background-color: #f6ffed;
  color: #52c41a;
}
.badge-cancel {
  background-color: #fff1f0;
  color: #ff4d4f;
}
.tk-content {
  flex: 1;
  overflow-y: auto;
}
.tk-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  padding: 40px 0;
}
.tk-empty-line {
  color: #999;
  text-align: center;
  padding: 10px;
}
.tk-detail {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
}
.tk-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e9ecef;
}
.tk-detail-title {
  font-size: 18px;
  font-weight: 600;
}
.tk-field {
  margin-bottom: 15px;
}
.tk-field-label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #555;
}
.tk-field-value {
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
}
.tk-field-pre {
  white-space: pre-wrap;
}
.tk-history-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #666;
}
.tk-history-status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}
.status-success {
  background-color: #f6ffed;
  color: #52c41a;
}
.status-fail {
  background-color: #fff1f0;
  color: #ff4d4f;
}
.tk-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}
.tk-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.tk-btn-primary {
  background-color: var(--primary);
  color: #ffffff;
}
.tk-btn-secondary {
  background-color: #e9ecef;
  color: #333333;
}
.tk-btn-danger {
  background-color: #ff4d4f;
  color: #ffffff;
}
.tk-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.tk-modal {
  background-color: #ffffff;
  border-radius: 8px;
  width: 500px;
  max-height: 80vh;
  overflow-y: auto;
}
.tk-modal-header {
  padding: 15px 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tk-modal-title {
  font-size: 16px;
  font-weight: 600;
}
.tk-modal-close {
  cursor: pointer;
  font-size: 20px;
  color: #999;
}
.tk-modal-body {
  padding: 20px;
}
.tk-modal-footer {
  padding: 15px 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.tk-form-group {
  margin-bottom: 15px;
  flex: 1;
}
.tk-form-row {
  display: flex;
  gap: 15px;
}
.tk-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}
.tk-input:focus {
  outline: none;
  border-color: var(--primary);
}
.tk-textarea {
  resize: vertical;
  min-height: 80px;
}
.tk-schedule-config {
  background-color: #f9fafb;
  padding: 15px;
  border-radius: 6px;
  margin-top: 10px;
}
</style>
