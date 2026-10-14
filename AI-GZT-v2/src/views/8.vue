<!--
  页面《8》　路由:/8（8）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-6hjel">
    <div class="box-div-12cke">
      <div class="box-div-0gp97">
        <span class="box-span-6epxs"></span>
        <span class="box-span-8eijf">插件管理</span>
        <button class="box-button-bioqf" type="button" @click="goPage8()" :class="{ 'lc-nav-active': route.path === '/8' }">已装插件</button>
        <button class="box-button-3e8l5" type="button" @click="goPage15()" :class="{ 'lc-nav-active': route.path === '/1-5' }">插件市场</button>
        <button class="box-button-ao38r" type="button" @click="goPage25()" :class="{ 'lc-nav-active': route.path === '/2-5' }">插件模版</button>
      </div>
      <div class="box-div-gvzko">
        <div class="box-div-hylnf">
          <div class="box-div-ubhxi">
            <div class="box-div-kdr26">
              <h3 class="box-h3-s1cid">已装插件</h3>
              <div class="pl-head-btns">
                <button class="box-button-voq47" type="button" @click="triggerZipImport">上传ZIP安装</button>
                <button class="pl-btn pl-btn-plain" type="button" @click="triggerFolderImport">上传文件夹安装</button>
                <input ref="zipInputRef" type="file" accept=".zip" class="pl-hidden-input" @change="handleZipImport" />
                <input ref="folderInputRef" type="file" webkitdirectory directory multiple class="pl-hidden-input" @change="handleFolderImport" />
              </div>
            </div>
            <div class="box-div-gro4u"></div>
            <div class="box-div-vd5lx">
              <div v-for="plugin in installedPlugins" :key="plugin.plugin_id" class="pl-card">
                <div class="pl-card-head">
                  <div class="pl-card-title">
                    <span class="pl-icon">🧩</span>
                    <div>
                      <h4 class="pl-name">{{ plugin.name }}</h4>
                      <p class="pl-sub">v{{ plugin.version }} · 作者:{{ plugin.author }}</p>
                    </div>
                  </div>
                  <span class="pl-badge" :class="plugin.enabled ? 'is-on' : 'is-off'">{{ plugin.enabled ? '启用' : '已禁用' }}</span>
                </div>
                <p class="pl-desc">{{ plugin.description }}</p>
                <div class="pl-perms">
                  <span v-for="p in (plugin.permissions || [])" :key="p" class="pl-perm">{{ p }}</span>
                </div>
                <div class="pl-actions">
                  <button v-if="plugin.enabled" class="pl-btn" type="button" @click="operatePlugin(plugin.plugin_id, 'disable')">禁用</button>
                  <button v-else class="pl-btn" type="button" @click="operatePlugin(plugin.plugin_id, 'enable')">启用</button>
                  <button class="pl-btn pl-btn-danger" type="button" @click="operatePlugin(plugin.plugin_id, 'uninstall')">卸载</button>
                  <button class="pl-btn" type="button" @click="openPluginConfig(plugin.plugin_id)">配置</button>
                  <button v-for="action in (plugin.actions || [])" :key="action.key" class="pl-btn" type="button" @click="executePluginAction(plugin.plugin_id, action.key)">
                    {{ action.label }}
                  </button>
                </div>
              </div>
              <div v-if="installedPlugins.length === 0" class="pl-empty">暂无已安装插件</div>
            </div>
          </div>
        </div>

        <!-- 插件配置弹窗 -->
        <div v-if="configVisible" class="pl-modal-mask" @click.self="closePluginConfig">
          <div class="pl-modal">
            <div class="pl-modal-header">
              <span class="pl-modal-title">插件配置</span>
              <span class="pl-modal-close" @click="closePluginConfig">×</span>
            </div>
            <div class="pl-modal-body">
              <div v-if="configLoading" style="text-align: center; padding: 30px 0; color: #999;">加载配置中...</div>
              <template v-else>
                <div v-if="configDefinition.length === 0" style="text-align: center; padding: 30px 0; color: #999;">该插件无需配置参数</div>
                <div v-for="item in configDefinition" :key="item.key" class="pl-form-item">
                  <label class="pl-form-label">{{ item.label }}<span v-if="item.required" class="pl-required">*</span></label>
                  <input v-if="item.type === 'input'" class="pl-form-input" type="text" v-model="configForm[item.key]" :placeholder="item.placeholder || ''" />
                  <input v-else-if="item.type === 'password'" class="pl-form-input" type="password" v-model="configForm[item.key]" :placeholder="item.placeholder || ''" />
                  <input v-else-if="item.type === 'number'" class="pl-form-input" type="number" v-model.number="configForm[item.key]" />
                  <textarea v-else-if="item.type === 'textarea'" class="pl-form-input pl-form-textarea" v-model="configForm[item.key]" :placeholder="item.placeholder || ''"></textarea>
                  <label v-else-if="item.type === 'switch' || item.type === 'boolean'" class="pl-switch">
                    <input type="checkbox" v-model="configForm[item.key]" />
                    <span class="pl-switch-slider"></span>
                  </label>
                  <select v-else-if="item.type === 'select'" class="pl-form-input" v-model="configForm[item.key]">
                    <option v-for="opt in (item.options || [])" :key="typeof opt === 'string' ? opt : opt.value" :value="typeof opt === 'string' ? opt : opt.value">
                      {{ typeof opt === 'string' ? opt : opt.label }}
                    </option>
                  </select>
                  <input v-else class="pl-form-input" type="text" v-model="configForm[item.key]" :placeholder="item.placeholder || ''" />
                  <p v-if="item.description" class="pl-form-tip">{{ item.description }}</p>
                </div>
              </template>
            </div>
            <div class="pl-modal-footer">
              <button class="pl-btn pl-btn-plain" type="button" @click="closePluginConfig">取消</button>
              <button v-if="configSupportTest" class="pl-btn pl-btn-plain" type="button" @click="testPluginConnection">测试连接</button>
              <button class="pl-btn pl-btn-primary" type="button" @click="savePluginConfig(false)">保存配置</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import { get, post } from '@/api/request'

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPage8() {
  router.push('/8')
}

function goPage15() {
  router.push('/1-5')
}

function goPage25() {
  router.push('/2-5')
}

/** 插件自定义操作按钮结构 */
interface PluginAction {
  key: string
  label: string
  icon?: string
  type?: string
}

/** 已安装插件结构（与后端 /api/plugin/list 返回的 installed 项对齐） */
interface InstalledPlugin {
  plugin_id: string
  name: string
  version: string
  author: string
  description: string
  enabled: boolean
  permissions?: string[]
  actions?: PluginAction[]
}

/** 配置项定义（与后端 /api/plugin/config 返回的 config_definition 项对齐） */
interface ConfigItem {
  key: string
  label: string
  type: string
  default?: unknown
  placeholder?: string
  required?: boolean
  description?: string
  options?: Array<string | { value: string; label: string }>
}

const installedPlugins = ref<InstalledPlugin[]>([])
const zipInputRef = ref<HTMLInputElement | null>(null)
const folderInputRef = ref<HTMLInputElement | null>(null)

const configVisible = ref(false)
const configLoading = ref(false)
const configPluginId = ref('')
const configDefinition = ref<ConfigItem[]>([])
const configForm = ref<Record<string, any>>({})
const configSupportTest = ref(false)

/** 加载已安装插件列表 */
async function loadPlugins() {
  try {
    const data = await get<{ installed: InstalledPlugin[] }>('/api/plugin/list')
    installedPlugins.value = data.installed || []
  } catch (e) {
    console.error('加载插件列表失败', e)
  }
}

/** 触发 ZIP 文件选择 */
function triggerZipImport() {
  zipInputRef.value?.click()
}

/** 触发文件夹选择 */
function triggerFolderImport() {
  folderInputRef.value?.click()
}

/** 上传 ZIP 插件包安装 */
async function handleZipImport(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.zip')) {
    window.alert('请选择zip格式的插件压缩包')
    input.value = ''
    return
  }
  const formData = new FormData()
  formData.append('plugin_file', file)
  try {
    const res = await fetch('/api/plugin/install/local', { method: 'POST', body: formData })
    const data = await res.json()
    if (data.code === 200) {
      window.alert('插件安装成功')
      loadPlugins()
    } else {
      window.alert(data.msg || '安装失败')
    }
  } catch (err) {
    console.error('ZIP 安装失败', err)
    window.alert('上传失败，请检查服务是否正常')
  }
  input.value = ''
}

/** 上传文件夹安装 */
async function handleFolderImport(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return
  const firstFile = files[0]
  const pluginName = firstFile.webkitRelativePath.split('/')[0]
  const formData = new FormData()
  formData.append('plugin_name', pluginName)
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const relativePath = file.webkitRelativePath.replace(pluginName + '/', '')
    formData.append(`file_${i}`, file)
    formData.append(`path_${i}`, relativePath)
  }
  formData.append('file_count', String(files.length))
  try {
    const res = await fetch('/api/plugin/install/folder', { method: 'POST', body: formData })
    const data = await res.json()
    if (data.code === 200) {
      window.alert('插件安装成功')
      loadPlugins()
    } else {
      window.alert(data.msg || '安装失败')
    }
  } catch (err) {
    console.error('文件夹安装失败', err)
    window.alert('上传失败，请检查服务是否正常')
  }
  input.value = ''
}

/** 启用 / 禁用 / 卸载 */
async function operatePlugin(pluginId: string, action: string) {
  if (action === 'uninstall' && !window.confirm('确定要卸载该插件吗？卸载后数据将无法恢复！')) return
  try {
    await post(`/api/plugin/${action}`, { plugin_id: pluginId })
    window.alert('操作成功')
    loadPlugins()
  } catch (e) {
    console.error('插件操作失败', e)
    window.alert('操作失败，请重试')
  }
}

/** 执行插件自定义操作 */
async function executePluginAction(pluginId: string, actionKey: string) {
  try {
    await post('/api/plugin/action', { plugin_id: pluginId, action_key: actionKey })
    window.alert('操作成功')
    loadPlugins()
  } catch (e) {
    console.error('执行操作失败', e)
    window.alert('操作执行失败，请检查服务是否正常')
  }
}

/** 打开插件配置弹窗（读取磁盘最新配置，强制禁用浏览器缓存） */
async function openPluginConfig(pluginId: string) {
  configPluginId.value = pluginId
  configVisible.value = true
  configLoading.value = true
  configDefinition.value = []
  configForm.value = {}
  configSupportTest.value = false
  try {
    const res = await fetch(`/api/plugin/config?plugin_id=${pluginId}`, { cache: 'no-store' })
    const data = await res.json()
    if (data.code === 200) {
      configDefinition.value = data.data.config_definition || []
      configSupportTest.value = data.data.support_test === true
      const current = data.data.current_config || {}
      const form: Record<string, unknown> = {}
      configDefinition.value.forEach((item) => {
        if (item.type === 'button') return
        form[item.key] = current[item.key] !== undefined ? current[item.key] : item.default
      })
      configForm.value = form
    } else {
      window.alert(data.msg || '加载配置失败')
      closePluginConfig()
    }
  } catch (e) {
    console.error('加载配置失败', e)
    window.alert('加载配置失败，请检查服务是否正常')
    closePluginConfig()
  } finally {
    configLoading.value = false
  }
}

/** 关闭配置弹窗 */
function closePluginConfig() {
  configVisible.value = false
  configPluginId.value = ''
  configDefinition.value = []
  configForm.value = {}
}

/** 收集配置表单数据（按字段类型归一） */
function collectConfig(): Record<string, unknown> {
  const config: Record<string, unknown> = {}
  configDefinition.value.forEach((item) => {
    if (item.type === 'button') return
    const val = configForm.value[item.key]
    if (item.type === 'number') config[item.key] = Number(val)
    else if (item.type === 'switch' || item.type === 'boolean') config[item.key] = Boolean(val)
    else config[item.key] = val
  })
  return config
}

/** 保存插件配置（silent=true 时不关闭弹窗，供测试连接调用） */
async function savePluginConfig(silent: boolean) {
  if (!configPluginId.value) return
  try {
    await post('/api/plugin/config/save', { plugin_id: configPluginId.value, config: collectConfig() })
    if (!silent) {
      window.alert('配置保存成功')
      closePluginConfig()
    }
  } catch (e) {
    console.error('保存配置失败', e)
    window.alert('保存失败，请检查服务是否正常')
  }
}

/** 测试插件连接（先保存当前配置，确保使用最新值） */
async function testPluginConnection() {
  if (!configPluginId.value) return
  try {
    await savePluginConfig(true)
    await post('/api/plugin/test', { plugin_id: configPluginId.value })
    window.alert('连接测试成功')
  } catch (e) {
    console.error('测试连接失败', e)
    window.alert('连接测试失败，请检查配置是否正确')
  }
}

onMounted(loadPlugins)
</script>

<style scoped>
.box-div-6hjel {
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

.box-div-12cke {
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

.box-div-0gp97 {
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

.box-span-6epxs {
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

.box-span-8eijf {
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

.box-button-bioqf {
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

.box-button-3e8l5 {
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

.box-button-ao38r {
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

.box-div-gvzko {
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

.box-div-hylnf {
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

.box-div-ubhxi {
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

.box-div-kdr26 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  justify-content: space-between;
  align-items: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-h3-s1cid {
  font-size: 18px;
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

.box-button-voq47 {
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

.box-div-gro4u {
  width: 100%;
  height: 1px;
  background-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-vd5lx {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-content: start;
  gap: 16px;
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

/* 已装插件卡片:一行 3 列（对齐插件市场页 1-5.vue 的网格观感），窄窗口自动降级 2 列 / 1 列 */
@media (max-width: 1023px) {
  .box-div-vd5lx {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 767px) {
  .box-div-vd5lx {
    grid-template-columns: 1fr;
  }
}

/* ===== 插件管理样式（对齐旧页 web_plugin_market.html） ===== */
.pl-head-btns {
  display: flex;
  gap: 8px;
  align-items: center;
}
.pl-hidden-input {
  display: none;
}
.pl-card {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.pl-card:hover {
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}
.pl-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.pl-card-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pl-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e8f1ff;
  border-radius: 8px;
  font-size: 20px;
}
.pl-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
  margin: 0;
}
.pl-sub {
  font-size: 12px;
  color: #86909c;
  margin: 2px 0 0;
}
.pl-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}
.pl-badge.is-on {
  background: #e8ffea;
  color: #00b42a;
}
.pl-badge.is-off {
  background: #f2f3f5;
  color: #86909c;
}
.pl-desc {
  font-size: 13px;
  color: #4e5969;
  line-height: 1.6;
  margin: 0 0 10px;
  flex-grow: 1;
}
.pl-perms {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.pl-perm {
  padding: 2px 8px;
  background: #f2f3f5;
  color: #4e5969;
  border-radius: 4px;
  font-size: 12px;
}
.pl-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pl-btn {
  height: 30px;
  font-size: 13px;
  color: #4e5969;
  background: #ffffff;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  padding: 0 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.pl-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.pl-btn-primary {
  background: var(--primary);
  border-color: var(--primary);
  color: #ffffff;
}
.pl-btn-primary:hover {
  background: #0e42d2;
  color: #ffffff;
}
.pl-btn-danger {
  border-color: #f53f3f;
  color: #f53f3f;
}
.pl-btn-danger:hover {
  background: #f53f3f;
  color: #ffffff;
}
.pl-btn-plain {
  color: #4e5969;
}
.pl-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.pl-modal {
  background: #ffffff;
  border-radius: 10px;
  width: 560px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}
.pl-modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e6eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pl-modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}
.pl-modal-close {
  cursor: pointer;
  font-size: 22px;
  color: #86909c;
  line-height: 1;
}
.pl-modal-body {
  padding: 20px;
  overflow-y: auto;
  flex-grow: 1;
}
.pl-modal-footer {
  padding: 14px 20px;
  border-top: 1px solid #e5e6eb;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.pl-form-item {
  margin-bottom: 16px;
}
.pl-form-label {
  display: block;
  font-size: 13px;
  color: #4e5969;
  margin-bottom: 6px;
}
.pl-required {
  color: #f53f3f;
  margin-left: 2px;
}
.pl-form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  font-size: 13px;
  box-sizing: border-box;
  outline: none;
}
.pl-form-input:focus {
  border-color: var(--primary);
}
.pl-form-textarea {
  min-height: 70px;
  resize: vertical;
}
.pl-form-tip {
  font-size: 12px;
  color: #86909c;
  margin: 4px 0 0;
}
.pl-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}
.pl-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.pl-switch-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #e5e6eb;
  transition: 0.3s;
  border-radius: 24px;
}
.pl-switch-slider:before {
  content: "";
  position: absolute;
  height: 20px;
  width: 20px;
  left: 2px;
  bottom: 2px;
  background: #ffffff;
  transition: 0.3s;
  border-radius: 50%;
}
.pl-switch input:checked + .pl-switch-slider {
  background: var(--primary);
}
.pl-switch input:checked + .pl-switch-slider:before {
  transform: translateX(20px);
}

/* 已装插件空态:网格布局下跨满整行居中（对齐插件市场页空态表现） */
.pl-empty {
  grid-column: 1 / -1;
  text-align: center;
  color: #999;
  padding: 40px 0;
}
</style>
