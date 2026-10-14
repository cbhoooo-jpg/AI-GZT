<!--
  页面《3》　路由:/3（3）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-7uzrx">
    <div class="box-div-9240c">
      <div class="box-div-gmrzc">
        <span class="box-span-v0d6y"></span>
        <span class="box-span-bqfh2">模型配置</span>
        <button class="box-button-tm5t8" type="button" @click="goPage3()" :class="{ 'lc-nav-active': route.path === '/3' }">模型1</button>
        <button class="box-button-k05po" type="button" @click="goPage13()" :class="{ 'lc-nav-active': route.path === '/1-3' }">模型2</button>
        <button class="box-button-mext8" type="button" @click="goPage23()" :class="{ 'lc-nav-active': route.path === '/2-3' }">模型3</button>
        <button class="box-button-q36xh" type="button" @click="goPage33()" :class="{ 'lc-nav-active': route.path === '/3-3' }">模型4</button>
        <button class="box-button-g4exl" type="button" @click="goPage43()" :class="{ 'lc-nav-active': route.path === '/4-3' }">模型5</button>
        <button class="box-button-qozja" type="button" @click="goPage53()" :class="{ 'lc-nav-active': route.path === '/5-3' }">模型6</button>
        <button class="box-button-qdkyf" type="button" @click="goPage63()" :class="{ 'lc-nav-active': route.path === '/6-3' }">模型7</button>
        <button class="box-button-5fwwe" type="button" @click="goPage73()" :class="{ 'lc-nav-active': route.path === '/7-3' }">模型8</button>
        <button class="box-button-e052x" type="button" @click="goPage82()" :class="{ 'lc-nav-active': route.path === '/8-2' }">模型9</button>
      </div>
      <div class="box-div-qe0xj">
        <div class="box-div-09npd">
          <div class="box-div-clw05">
            <h2 class="box-h2-yak9r">主模型配置</h2>
            <button class="box-button-ow0ki" type="button" :disabled="saving" @click="handleSave">保存配置</button>
          </div>
          <div class="box-div-tbb0v">
            <p class="box-p-vt43d">API地址</p>
            <input class="box-input-1vgwy" type="text" placeholder="请输入内容" v-model="form.api_url" />
          </div>
          <div class="box-div-nuyq7">
            <p class="box-p-jljbf">模型ID</p>
            <input class="box-input-pql5f" type="text" placeholder="请输入内容" v-model="form.model_name" />
          </div>
          <div class="box-div-hzwmk">
            <p class="box-p-lzoaq">API-keys</p>
            <input class="box-input-a3t44" type="password" placeholder="请输入密码" v-model="form.api_key" />
          </div>
          <div class="box-div-uzfjc">
            <p class="box-p-mz7vb">请求超时</p>
            <input class="box-input-1rhdq" type="text" placeholder="请输入内容" v-model.number="form.timeout" />
            <p class="box-p-0spvw">温度参数</p>
            <input class="box-input-gn7hm" type="text" placeholder="请输入内容" v-model.number="form.temperature" />
          </div>
          <div class="box-div-mgprl">
            <p class="box-p-wtcle">回复上限</p>
            <input class="box-input-c1tu3" type="text" placeholder="每轮回复次数上限" v-model.number="form.max_reply_rounds" />
            <p class="box-p-fq3pu">上下文轮数</p>
            <input class="box-input-4owg1" type="text" placeholder="请输入内容" v-model.number="form.max_chat_rounds" />
          </div>
          <div class="box-div-i3z9t">
            <p class="box-p-wt8af">输出模式</p>
            <div class="box-div-uch2l" @click="form.stream_output = !form.stream_output" :style="{ backgroundColor: form.stream_output ? 'var(--primary)' : '#c9cdd4', justifyContent: form.stream_output ? 'flex-end' : 'flex-start' }">
              <div class="box-div-c16jy"></div>
            </div>
            <p class="box-p-311rg">流式输出开关</p>
          </div>
          <div class="box-div-w3a44">
            <p class="box-p-sgoqd">人设名称</p>
            <input class="box-input-ilqdm" type="text" placeholder="请输入内容" v-model="form.persona_name" />
          </div>
          <div class="box-div-sbfcd">
            <p class="box-p-3gy3p">人设提示词</p>
            <textarea class="box-textarea-1cbul" placeholder="请输入多行内容" rows="4" v-model="form.persona_prompt"></textarea>
          </div>
          <div class="box-div-362sd">
            <p class="box-p-r09wz">固定提示1</p>
            <textarea class="box-textarea-k818j" placeholder="请输入多行内容" rows="4" v-model="form.fixed_prompt_1"></textarea>
          </div>
          <div class="box-div-sd703">
            <p class="box-p-6koz3">固定提示2</p>
            <textarea class="box-textarea-h4ikj" placeholder="请输入多行内容" rows="4" v-model="form.fixed_prompt_2"></textarea>
          </div>
          <div class="box-div-mp9ur">
            <p class="box-p-dgbm5">固定提示3</p>
            <textarea class="box-textarea-t2ar1" placeholder="请输入多行内容" rows="4" v-model="form.fixed_prompt_3"></textarea>
          </div>
          <!-- 已启用插件勾选区:按槽位控制次级/主控可见插件；不勾选或清空 = 全量注入（后端口径） -->
          <div style="margin-top: 12px;">
            <p style="font-size: 14px; color: #333; margin-bottom: 8px;">已启用插件</p>
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
              <button type="button" @click="handleSelectAllPlugins" style="padding: 4px 12px; font-size: 13px; cursor: pointer;">全选</button>
              <button type="button" @click="handleClearPlugins" style="padding: 4px 12px; font-size: 13px; cursor: pointer;">清空</button>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 12px;">
              <label v-for="plugin in pluginList" :key="plugin.plugin_id" style="display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer;">
                <input type="checkbox" :value="plugin.plugin_id" v-model="form.enabled_plugins" />
                <span>{{ plugin.name || plugin.plugin_id }}</span>
              </label>
              <p v-if="!pluginList.length" style="font-size: 13px; color: #999;">暂无已注册插件</p>
            </div>
            <p style="font-size: 12px; color: #999; margin-top: 6px;">不勾选或全部清空 = 全量注入所有插件（默认行为）</p>
          </div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import { getModel, saveModel, type ModelConfig } from '@/api/model'
import { get } from '@/api/request'

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPage3() {
  router.push('/3')
}

function goPage13() {
  router.push('/1-3')
}

function goPage23() {
  router.push('/2-3')
}

function goPage33() {
  router.push('/3-3')
}

function goPage43() {
  router.push('/4-3')
}

function goPage53() {
  router.push('/5-3')
}

function goPage63() {
  router.push('/6-3')
}

function goPage73() {
  router.push('/7-3')
}

function goPage82() {
  router.push('/8-2')
}

/** ============================================================
 *  阶段 2:模型配置表单逻辑（13 字段与 models_config.json 槽位一一对应）
 *  - 本页对应 slot=1（模型1，主模型配置-玲珑）
 *  - 挂载后自动回填（api_key 为明文）；保存时空密钥不回写（后端保证）
 *  - 输出模式开关:点击切换流式/非流式，样式随 form.stream_output 联动
 * ============================================================ */

/** 本页对应的槽位号（模型1 → slot=1） */
const SLOT = 1

/** 表单数据（字段与 ModelConfig 逐一对齐，默认值取自 models_config.json 结构） */
const form = reactive<ModelConfig & { enabled_plugins: string[] }>({
  slot: SLOT,
  api_url: '',
  model_name: '',
  api_key: '',
  timeout: 200,
  temperature: 0.5,
  max_tokens: 0,
  max_reply_rounds: 20,
  max_chat_rounds: 10,
  stream_output: true,
  persona_name: '',
  persona_prompt: '',
  fixed_prompt_1: '',
  fixed_prompt_2: '',
  fixed_prompt_3: '',
  // 已启用插件ID列表（空数组 = 全量注入，与后端口径一致）
  enabled_plugins: [],
})

/** 已注册插件列表（/api/plugin/list 返回，供勾选；失败静默降级为空数组） */
const pluginList = ref<Array<{ plugin_id: string; name?: string }>>([])

/** 全选所有已注册插件 */
function handleSelectAllPlugins() {
  form.enabled_plugins = pluginList.value.map((p) => p.plugin_id)
}

/** 清空勾选（清空后提交空数组 = 后端按全量注入处理） */
function handleClearPlugins() {
  form.enabled_plugins = []
}

/** 保存按钮的忙碌态（防止重复点击） */
const saving = ref(false)

/** 挂载后回填:从后端拉取本槽位完整配置（api_key 为明文） */
onMounted(async () => {
  try {
    const cfg = await getModel(SLOT)
    Object.assign(form, cfg, { slot: SLOT })
    // 兜底:后端未返回或返回 null 时置空数组（空数组 = 全量注入，与后端口径一致）
    form.enabled_plugins = Array.isArray(cfg?.enabled_plugins) ? cfg.enabled_plugins : []
  } catch (err) {
    console.error('加载模型配置失败:', err)
  }
  // 拉取已装插件列表（口径与 8.vue 完全一致:request.ts 的 get 已解包 data，直接取 data.installed）
  try {
    const res: any = await get('/api/plugin/list')
    pluginList.value = Array.isArray(res?.installed) ? res.installed : []
  } catch (err) {
    console.error('加载插件列表失败:', err)
  }
})

/** 保存配置:提交 form 到后端；成功后用回传值刷新（保持脱敏口径一致） */
async function handleSave() {
  if (saving.value) return
  saving.value = true
  try {
    const latest = await saveModel({ ...form, slot: SLOT })
    Object.assign(form, latest, { slot: SLOT })
    alert(`模型${SLOT}配置保存成功`)
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    alert(`保存失败:${message}`)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.box-div-7uzrx {
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

.box-div-9240c {
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

.box-div-gmrzc {
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

.box-span-v0d6y {
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

.box-span-bqfh2 {
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

.box-button-tm5t8 {
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

.box-button-k05po {
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

.box-button-mext8 {
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

.box-button-q36xh {
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

.box-button-g4exl {
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

.box-button-qozja {
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

.box-button-qdkyf {
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

.box-button-5fwwe {
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

.box-button-e052x {
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

.box-div-qe0xj {
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
  height: 729px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-09npd {
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

.box-div-clw05 {
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

.box-h2-yak9r {
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

.box-button-ow0ki {
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

.box-div-tbb0v {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-vt43d {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-1vgwy {
  width: 450px;
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

.box-div-nuyq7 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-jljbf {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-pql5f {
  width: 450px;
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

.box-div-hzwmk {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-lzoaq {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-a3t44 {
  width: 450px;
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

.box-div-uzfjc {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-mz7vb {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-1rhdq {
  width: 146px;
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

.box-p-0spvw {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-gn7hm {
  width: 146px;
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

.box-div-mgprl {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-wtcle {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-c1tu3 {
  width: 146px;
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

.box-p-fq3pu {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-4owg1 {
  width: 146px;
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

.box-div-i3z9t {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-wt8af {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-uch2l {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
  width: 44px;
  height: 24px;
  min-width: 44px;
  padding-left: 4px;
  padding-right: 4px;
  background-color: var(--primary);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
  border-bottom-left-radius: 12px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-c16jy {
  width: 16px;
  height: 16px;
  min-width: 16px;
  max-width: 16px;
  background-color: #ffffff;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-p-311rg {
  font-size: 12px;
  color: #9298a0;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 86px;
  display: flex;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-w3a44 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-sgoqd {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-ilqdm {
  width: 146px;
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

.box-div-sbfcd {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-3gy3p {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-textarea-1cbul {
  width: 450px;
  font-size: 14px;
  color: #1f2329;
  background-color: #ffffff;
  line-height: 1.6;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  height: 41px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-362sd {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-r09wz {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-textarea-k818j {
  width: 450px;
  font-size: 14px;
  color: #1f2329;
  background-color: #ffffff;
  line-height: 1.6;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  height: 41px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-sd703 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-6koz3 {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-textarea-h4ikj {
  width: 450px;
  font-size: 14px;
  color: #1f2329;
  background-color: #ffffff;
  line-height: 1.6;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  height: 41px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-mp9ur {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-dgbm5 {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-textarea-t2ar1 {
  width: 450px;
  font-size: 14px;
  color: #1f2329;
  background-color: #ffffff;
  line-height: 1.6;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  padding-top: 8px;
  padding-right: 8px;
  padding-bottom: 8px;
  padding-left: 8px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  height: 41px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}
</style>
