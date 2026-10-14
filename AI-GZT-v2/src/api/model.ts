// ============================================================
// 9 槽位模型配置接口封装（阶段 2 新增）
// ------------------------------------------------------------
// 职责:给 9 个模型配置页提供统一调用入口，屏蔽 HTTP 细节，只暴露 4 个语义化函数
// 约定:
//   1. 所有接口路径统一走 /api/models/*（基址与 request.ts 一致）
//   2. ModelConfig 字段与 api_server.py 的 _MODEL_SLOT_FIELDS 严格一一对应，
//      前端表单绑定 / 挂载回填 / 保存提交均以 ModelConfig 为准
//   3. listModels 返回的 api_key 为脱敏值（前 4 位 + ****）；
//      getModel 返回明文，供编辑页回填；
//      saveModel 时若 api_key 为空或脱敏形态，后端保留原值不覆盖
// ============================================================

import { get, post } from './request'

/** 单槽位模型配置（字段与后端 _MODEL_SLOT_FIELDS 逐一对齐） */
export interface ModelConfig {
  /** 槽位号（1~9），提交时必填 */
  slot: number
  /** 槽位别名（如"模型1"），列表页展示用 */
  display_name?: string
  /** API 地址（如 https://ark.cn-beijing.volces.com/api/v3） */
  api_url?: string
  /** 模型 ID（火山方舟 / OpenAI 兼容语义） */
  model_name?: string
  /** 密钥:list 返回脱敏值，get 返回明文，save 提交明文（空值不回写） */
  api_key?: string
  /** 请求超时（秒） */
  timeout?: number
  /** 温度参数（0~2） */
  temperature?: number
  /** 单次输出上限（tokens）:0 = 自动（调用时不发送该参数，自动使用模型自身最大输出） */
  max_tokens?: number
  /** 每轮回复次数上限（承接旧界面「回复上限」的循环次数语义） */
  max_reply_rounds?: number
  /** 上下文轮数 */
  max_chat_rounds?: number
  /** 输出模式:true 流式 / false 非流式 */
  stream_output?: boolean
  /** 人设名称（供任务模式选角色） */
  persona_name?: string
  /** 人设提示词 */
  persona_prompt?: string
  /** 固定提示 1 */
  fixed_prompt_1?: string
  /** 固定提示 2 */
  fixed_prompt_2?: string
  /** 固定提示 3 */
  fixed_prompt_3?: string
  /** 已启用插件ID列表（空数组/缺失 = 全量注入，向后兼容；与后端 _MODEL_SLOT_FIELDS 逐字对齐） */
  enabled_plugins?: string[] | null
}

/** 角色简表（/api/models/roles 返回值） */
export interface ModelRole {
  slot: number
  persona_name: string
}

/** 列出 9 槽位模型配置（api_key 为脱敏值，供列表/概览页展示） */
export function listModels(): Promise<ModelConfig[]> {
  return get<ModelConfig[]>('/api/models/list')
}

/** 读取指定槽位完整配置（api_key 为明文，供编辑页回填）
 *  @param slot 槽位号 1~9 */
export function getModel(slot: number): Promise<ModelConfig> {
  return get<ModelConfig>('/api/models/get', { slot })
}

/** 保存指定槽位配置
 *  - 提交 api_key 为空字符串 / null / 脱敏形态（以 **** 结尾）时，后端保留原值不覆盖
 *  - 其余字段按 ModelConfig 逐字段合并
 *  @param config 槽位配置（slot 必填，其它字段按需提交） */
export function saveModel(config: ModelConfig): Promise<ModelConfig> {
  return post<ModelConfig>('/api/models/save', config)
}

/** 列出已填写 persona_name 的槽位（供任务模式选角色，只返回有内容的） */
export function listRoles(): Promise<ModelRole[]> {
  return get<ModelRole[]>('/api/models/roles')
}