<!--
  页面《1》　路由:/1-5（15）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout8>
  <div class="box-div-spooa">
    <div class="box-div-swurf">
      <div class="box-div-ael31">
        <div class="box-div-q2lil">
          <h3 class="box-h3-i7jpn">插件市场-选择插件安装</h3>
          <button class="pl-btn pl-btn-plain" type="button" :disabled="loading" @click="loadMarket(true)">刷新市场列表</button>
        </div>
        <div class="mk-meta">
          <span>{{ marketName }}</span>
          <span v-if="updatedAt" class="mk-meta-time">清单更新时间:{{ updatedAt }}</span>
        </div>
        <div v-if="loading" style="text-align: center; color: #999; padding: 40px 0;">正在获取云端插件清单...</div>
        <div v-else-if="errorMsg" style="text-align: center; padding: 40px 0;">
          <p style="color: #f53f3f; margin-bottom: 12px;">{{ errorMsg }}</p>
          <button class="pl-btn pl-btn-primary" type="button" @click="loadMarket(true)">重新加载</button>
        </div>
        <div v-else class="mk-grid">
          <div v-for="plugin in plugins" :key="plugin.plugin_id" class="mk-card">
            <div class="mk-card-head">
              <div class="mk-card-title">
                <span class="pl-icon">🧩</span>
                <div>
                  <h4 class="pl-name">{{ plugin.name }}</h4>
                  <p class="pl-sub">v{{ plugin.version }} · 作者:{{ plugin.author || '未知' }}</p>
                </div>
              </div>
              <span class="pl-badge" :class="badgeClass(plugin)">{{ badgeText(plugin) }}</span>
            </div>
            <p class="pl-desc">{{ plugin.description || '' }}</p>
            <div class="pl-perms">
              <span v-if="plugin.category" class="pl-perm">{{ plugin.category }}</span>
              <span v-for="p in (plugin.permissions || [])" :key="p" class="pl-perm">{{ p }}</span>
            </div>
            <button
              v-if="plugin.status === 'installed'"
              class="pl-btn pl-btn-block"
              type="button"
              disabled
            >已安装（最新）</button>
            <button
              v-else-if="plugin.status === 'update_available'"
              class="pl-btn pl-btn-block pl-btn-warning"
              type="button"
              :disabled="installingId === plugin.plugin_id"
              @click="installMarketPlugin(plugin)"
            >{{ installingId === plugin.plugin_id ? '正在更新...' : `更新到 v${plugin.version}（当前 v${plugin.installed_version || '?'}）` }}</button>
            <button
              v-else
              class="pl-btn pl-btn-block pl-btn-primary"
              type="button"
              :disabled="installingId === plugin.plugin_id"
              @click="installMarketPlugin(plugin)"
            >{{ installingId === plugin.plugin_id ? '正在安装...' : '安装' }}</button>
          </div>
          <div v-if="plugins.length === 0" style="text-align: center; color: #999; padding: 40px 0;">市场暂无可安装插件</div>
        </div>
      </div>
    </div>
  </div>
  </Layout8>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout8 from '@/layouts/Layout8.vue'
import { get, post } from '@/api/request'

/** 市场插件结构（后端已按 plugin_id 合并未安装/可更新/已最新三态） */
interface MarketPlugin {
  plugin_id: string
  name: string
  version: string
  author?: string
  description?: string
  category?: string
  permissions?: string[]
  status?: 'installed' | 'update_available' | string
  installed_version?: string
}

const plugins = ref<MarketPlugin[]>([])
const marketName = ref('云端插件市场')
const updatedAt = ref('')
const loading = ref(false)
const errorMsg = ref('')
const installingId = ref('')

/** 拉取云端插件清单（force=true 跳过前端与后端缓存） */
async function loadMarket(force: boolean) {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await get<{ plugins: MarketPlugin[]; market_name?: string; updated_at?: string }>(
      '/api/plugin/market/list',
      { force: force ? 'true' : 'false' },
    )
    plugins.value = data.plugins || []
    marketName.value = data.market_name || '云端插件市场'
    updatedAt.value = data.updated_at || ''
  } catch (e) {
    console.error('加载市场插件失败', e)
    errorMsg.value = '网络错误，请检查服务是否正常'
  } finally {
    loading.value = false
  }
}

/** 从云端市场安装/更新插件，成功后强制刷新市场三态 */
async function installMarketPlugin(plugin: MarketPlugin) {
  if (installingId.value) return
  if (
    plugin.status === 'update_available' &&
    !window.confirm('更新将卸载旧版并安装新版，插件配置会自动保留，是否继续？')
  ) {
    return
  }
  installingId.value = plugin.plugin_id
  try {
    await post('/api/plugin/market/install', { plugin_id: plugin.plugin_id })
    window.alert(plugin.status === 'update_available' ? '更新成功' : '安装成功')
    await loadMarket(true)
  } catch (e) {
    console.error('安装插件失败', e)
    window.alert('安装失败，请检查网络或服务是否正常')
  } finally {
    installingId.value = ''
  }
}

/** 三态徽标文案 */
function badgeText(p: MarketPlugin) {
  if (p.status === 'installed') return '已安装'
  if (p.status === 'update_available') return '可更新'
  return '可安装'
}

/** 三态徽标样式 */
function badgeClass(p: MarketPlugin) {
  if (p.status === 'installed') return 'is-off'
  if (p.status === 'update_available') return 'is-warn'
  return 'is-new'
}

onMounted(() => loadMarket(false))
</script>

<style scoped>
.box-div-spooa {
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

.box-div-swurf {
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

.box-div-ael31 {
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

.box-div-q2lil {
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

.box-h3-i7jpn {
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

/* ===== 插件市场样式（对齐旧页 web_plugin_market.html 可安装插件 Tab） ===== */
.mk-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #86909c;
  margin-bottom: 12px;
}
.mk-meta-time {
  color: #c9cdd4;
}
.mk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.mk-card {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}
.mk-card:hover {
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}
.mk-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.mk-card-title {
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
  white-space: nowrap;
}
.pl-badge.is-off {
  background: #f2f3f5;
  color: #86909c;
}
.pl-badge.is-warn {
  background: #fff7e8;
  color: #ff7d00;
}
.pl-badge.is-new {
  background: #e8f1ff;
  color: var(--primary);
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
.pl-btn {
  height: 32px;
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
.pl-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.pl-btn-plain {
  color: #4e5969;
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
.pl-btn-warning {
  border-color: #ff7d00;
  color: #ff7d00;
  background: #ffffff;
}
.pl-btn-warning:hover {
  background: #ff7d00;
  color: #ffffff;
}
.pl-btn-block {
  width: 100%;
  height: 34px;
}
</style>
