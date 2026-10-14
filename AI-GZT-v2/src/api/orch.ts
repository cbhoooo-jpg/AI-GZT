// ============================================================
// 任务编排接口封装（阶段5 新增）
// ------------------------------------------------------------
// 职责:给 /1 主对话页「任务模式」提供 /api/orch/* 5 接口统一入口
// 约定:
//   1. 复用 request.ts 的 get/post（基址 /api、15s 超时、code 归一、错误抛出）
//      基址与后端同源（vite 代理 → 127.0.0.1:8000），禁止硬编码 IP
//   2. 后端 {code,msg,data} 已由 request.ts 剥离，此处只处理内层 data
//   3. 内层 ok=false 时抛可读 Error，保持与 request.ts 口径一致
//   4. 与 model.ts 风格保持同构（命名 / 注释 / 类型导出）
// ============================================================

import { get, post } from './request'

/** 任务历史轨迹单条（后端 meta.history 元素） */
export interface TaskHistoryItem {
  ts: number
  state: string
  note?: string
}

/** 任务元快照（对应 sessions/tasks/T-XXX/meta.json） */
export interface TaskMeta {
  task_id: string
  session_id: string
  requirement: string
  /** 状态码 0~5 */
  state: number
  /** 状态名（6 态之一）:待派发/开发中/待审查/审查中/待裁决/已闭环 */
  state_name: string
  rework_count: number
  max_rework: number
  dev_slot?: number | null
  review_slot?: number | null
  degraded_review?: boolean
  terminal?: boolean
  created_at?: number
  updated_at?: number
  deadline_at?: number
  history?: TaskHistoryItem[]
}

/** 角色池槽位（/api/orch/roles 返回的 data 元素） */
export interface RoleSlot {
  slot: number
  display_name: string
  model_name: string
  persona_name: string
  available: boolean
}

/** 提交/中止返回结构 */
export interface SubmitResult {
  ok: boolean
  task_id?: string
  state?: string
  role_pool?: RoleSlot[]
  msg?: string
}

/** 查询返回结构（meta 内层再嵌一层 data） */
export interface QueryResult {
  ok: boolean
  data?: TaskMeta
  dev?: { messages: unknown[] }
  review?: { messages: unknown[] }
  msg?: string
}

/** 任务列表条目 */
export interface TaskListItem {
  task_id: string
  state_name: string
  rework_count: number
  degraded_review: boolean
  created_at?: number
  updated_at?: number
}

/** 列表内层结构 */
export interface ListResult {
  ok: boolean
  data: TaskListItem[]
  msg?: string
}

/** 角色池返回结构 */
export interface RolePoolResult {
  ok: boolean
  data: RoleSlot[]
  brief: string
  msg?: string
}

/** 提交编排任务:立即返回 task_id，不阻塞（后台线程跑闭环）
 *  @param requirement 需求描述（须明确，如「新建 note.txt 并写入 hello」）
 *  @param sessionId 会话号，默认 default */
export async function submitTask(
  requirement: string,
  sessionId = 'default',
): Promise<SubmitResult> {
  const res = await post<SubmitResult>('/api/orch/submit', {
    requirement,
    session_id: sessionId,
  })
  if (!res.ok) throw new Error(res.msg || '任务提交失败')
  return res
}

/** 查询单任务:meta 快照 + 开发/审查次级会话全文 */
export async function queryTask(taskId: string): Promise<QueryResult> {
  const res = await get<QueryResult>('/api/orch/query', { task_id: taskId })
  if (!res.ok) throw new Error(res.msg || '任务查询失败')
  return res
}

/** 列出会话下全部编排任务（按 task_id 升序） */
export async function listTasks(sessionId = 'default'): Promise<TaskListItem[]> {
  const res = await get<ListResult>('/api/orch/list', { session_id: sessionId })
  if (!res.ok) throw new Error(res.msg || '任务列表获取失败')
  return res.data || []
}

/** 中止编排任务 */
export async function abortTask(taskId: string): Promise<SubmitResult> {
  const res = await post<SubmitResult>('/api/orch/abort', { task_id: taskId })
  if (!res.ok) throw new Error(res.msg || '任务中止失败')
  return res
}

/** 当前可用角色池快照（槽位 / 人设 / 连通状态） */
export async function listRolePool(): Promise<RolePoolResult> {
  const res = await get<RolePoolResult>('/api/orch/roles')
  if (!res.ok) throw new Error(res.msg || '角色池获取失败')
  return res
}