// ============================================================
// 统一请求封装（阶段 2 新增）
// ------------------------------------------------------------
// 职责:给 9 个模型配置页提供统一的 fetch 封装（超时控制 + 响应归一 + 错误提示）
// 约定:
//   1. 基址为 /api 相对路径（生产环境同源直接命中后端；开发环境靠 vite.config.ts
//      的 server.proxy 转发，避免跨域并保持两环境代码零差异）
//   2. 后端响应统一为 { code: 200, msg?: string, data?: any }，
//      与既有 /api/config/get 等接口口径完全一致（详见 api_server.py）
//   3. code !== 200 视为业务失败，抛出携带可读 message 的 Error
//   4. 网络错误 / 超时 / 非 JSON 响应统一抛出可读错误，调用方仅需 try/catch
// ============================================================

/** 请求默认超时（毫秒）:9 个配置页均为轻量读写，15 秒足够 */
const DEFAULT_TIMEOUT = 15000

/** 业务响应结构（与后端 { code, msg, data } 对齐） */
export interface ApiResponse<T = unknown> {
  /** 业务状态码:200 表示成功，其余为业务失败 */
  code: number
  /** 失败时的可读提示（成功时可缺省） */
  msg?: string
  /** 业务数据（GET 主要用于回填，POST 主要用于回传最新值） */
  data?: T
}

/** 请求参数 */
export interface RequestOptions {
  /** 请求方法，缺省 GET */
  method?: 'GET' | 'POST'
  /** 查询串参数（GET 用，undefined/null 自动跳过） */
  params?: Record<string, string | number | boolean | undefined | null>
  /** 请求体（POST 用，内部自动 JSON 序列化） */
  body?: unknown
  /** 超时毫秒，缺省 15000 */
  timeout?: number
}

/** 把对象拼成查询串（自动跳过 undefined / null，避免拼出 ?slot=undefined） */
function buildQuery(params?: RequestOptions['params']): string {
  if (!params) return ''
  const parts: string[] = []
  Object.keys(params).forEach((key) => {
    const value = params[key]
    if (value === undefined || value === null) return
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
  })
  return parts.length > 0 ? `?${parts.join('&')}` : ''
}

/** 核心请求函数:超时控制 + 响应归一化
 *  - 内部使用 fetch + AbortController，超时后自动中止请求
 *  - 统一解析后端 { code, msg, data } 结构，code !== 200 抛业务错误
 *  - 网络错误 / 超时 / 非 JSON 响应也统一抛出可读错误，调用方仅需 try/catch */
async function request<T = unknown>(url: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', params, body, timeout = DEFAULT_TIMEOUT } = options
  const fullUrl = url + buildQuery(params)

  // 超时控制:AbortController 为浏览器原生能力，无需额外依赖
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  let response: Response
  try {
    response = await fetch(fullUrl, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (err) {
    // AbortController.abort() 触发的错误 name 为 AbortError，与网络错误分开提示
    const reason =
      (err as { name?: string })?.name === 'AbortError'
        ? `请求超时（${timeout}ms）:${fullUrl}`
        : `网络请求失败:${fullUrl}`
    throw new Error(reason)
  } finally {
    clearTimeout(timer)
  }

  // 非 JSON 响应（如 500 HTML 错误页）:先取文本，避免 json() 抛裸错
  let payload: ApiResponse<T>
  try {
    payload = (await response.json()) as ApiResponse<T>
  } catch (err) {
    throw new Error(`响应解析失败（HTTP ${response.status}）:${fullUrl}`)
  }

  // 业务错误:后端 { code, msg } 口径
  if (payload.code !== 200) {
    throw new Error(payload.msg || `请求失败（code=${payload.code}）:${fullUrl}`)
  }

  return payload.data as T
}

/** GET 便捷方法:参数走查询串 */
export function get<T = unknown>(
  url: string,
  params?: RequestOptions['params'],
  timeout?: number,
): Promise<T> {
  return request<T>(url, { method: 'GET', params, timeout })
}

/** POST 便捷方法:参数走 JSON 请求体 */
export function post<T = unknown>(url: string, body?: unknown, timeout?: number): Promise<T> {
  return request<T>(url, { method: 'POST', body, timeout })
}