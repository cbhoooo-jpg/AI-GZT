<!--
  页面《7》　路由:/7-3（73）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout3>
  <div class="box-div-nqpe4">
    <div class="box-div-abjf3">
      <div class="box-div-z48dr">
        <div class="box-div-1rdx4">
          <h2 class="box-h2-fhw30">模型8配置</h2>
          <button class="box-button-fttxy" type="button" :disabled="saving" @click="handleSave">保存配置</button>
        </div>
        <div class="box-div-my33n">
          <p class="box-p-25pgb">API地址</p>
          <input class="box-input-enqlf" type="text" placeholder="请输入内容" v-model="form.api_url" />
        </div>
        <div class="box-div-ewtju">
          <p class="box-p-m8us8">模型ID</p>
          <input class="box-input-4gm46" type="text" placeholder="请输入内容" v-model="form.model_name" />
        </div>
        <div class="box-div-ajsxo">
          <p class="box-p-0w98a">API-keys</p>
          <input class="box-input-afed3" type="password" placeholder="请输入密码" v-model="form.api_key" />
        </div>
        <div class="box-div-j9n2m">
          <p class="box-p-nrkzn">请求超时</p>
          <input class="box-input-g6tpu" type="text" placeholder="请输入内容" v-model.number="form.timeout" />
          <p class="box-p-k68z8">温度参数</p>
          <input class="box-input-9j2ed" type="text" placeholder="请输入内容" v-model.number="form.temperature" />
        </div>
        <div class="box-div-630oc">
          <p class="box-p-zm1yv">回复上限</p>
          <input class="box-input-6yt8m" type="text" placeholder="每轮回复次数上限" v-model.number="form.max_reply_rounds" />
          <p class="box-p-tvtgu">上下文轮数</p>
          <input class="box-input-vd7ry" type="text" placeholder="请输入内容" v-model.number="form.max_chat_rounds" />
        </div>
        <div class="box-div-t79k0">
          <p class="box-p-p8kud">输出模式</p>
          <div class="box-div-mv0c0" @click="form.stream_output = !form.stream_output" :style="{ backgroundColor: form.stream_output ? 'var(--primary)' : '#c9cdd4', justifyContent: form.stream_output ? 'flex-end' : 'flex-start' }">
            <div class="box-div-pb7c1"></div>
          </div>
          <p class="box-p-7dsoy">流式输出开关</p>
        </div>
        <div class="box-div-msteu">
          <p class="box-p-kktxj">人设名称</p>
          <input class="box-input-bzjlc" type="text" placeholder="请输入内容" v-model="form.persona_name" />
        </div>
        <div class="box-div-sr65k">
          <p class="box-p-o83td">人设提示词</p>
          <textarea class="box-textarea-g4190" placeholder="请输入多行内容" rows="4" v-model="form.persona_prompt"></textarea>
        </div>
        <div class="box-div-7kfnn">
          <p class="box-p-8da74">固定提示1</p>
          <textarea class="box-textarea-2h76m" placeholder="请输入多行内容" rows="4" v-model="form.fixed_prompt_1"></textarea>
        </div>
        <div class="box-div-27zw5">
          <p class="box-p-ftj9j">固定提示2</p>
          <textarea class="box-textarea-ruzib" placeholder="请输入多行内容" rows="4" v-model="form.fixed_prompt_2"></textarea>
        </div>
        <div class="box-div-didjm">
          <p class="box-p-y6zo1">固定提示3</p>
          <textarea class="box-textarea-kurh2" placeholder="请输入多行内容" rows="4" v-model="form.fixed_prompt_3"></textarea>
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
  </Layout3>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout3 from '@/layouts/Layout3.vue'
import { getModel, saveModel, type ModelConfig } from '@/api/model'
import { get } from '@/api/request'

/** ============================================================
 *  阶段 2:模型配置表单逻辑（13 字段与 models_config.json 槽位一一对应）
 *  - 本页对应 slot=8（模型8，模型8配置-）
 *  - 挂载后自动回填（api_key 为明文）；保存时空密钥不回写（后端保证）
 *  - 输出模式开关:点击切换流式/非流式，样式随 form.stream_output 联动
 * ============================================================ */

/** 本页对应的槽位号（模型8 → slot=8） */
const SLOT = 8

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
.box-div-nqpe4 {
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

.box-div-abjf3 {
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

.box-div-z48dr {
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

.box-div-1rdx4 {
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

.box-h2-fhw30 {
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

.box-button-fttxy {
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

.box-div-my33n {
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

.box-p-25pgb {
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

.box-input-enqlf {
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

.box-div-ewtju {
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

.box-p-m8us8 {
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

.box-input-4gm46 {
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

.box-div-ajsxo {
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

.box-p-0w98a {
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

.box-input-afed3 {
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

.box-div-j9n2m {
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

.box-p-nrkzn {
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

.box-input-g6tpu {
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

.box-p-k68z8 {
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

.box-input-9j2ed {
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

.box-div-630oc {
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

.box-p-zm1yv {
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

.box-input-6yt8m {
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

.box-p-tvtgu {
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

.box-input-vd7ry {
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

.box-div-t79k0 {
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

.box-p-p8kud {
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

.box-div-mv0c0 {
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

.box-div-pb7c1 {
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

.box-p-7dsoy {
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

.box-div-msteu {
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

.box-p-kktxj {
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

.box-input-bzjlc {
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

.box-div-sr65k {
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

.box-p-o83td {
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

.box-textarea-g4190 {
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

.box-div-7kfnn {
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

.box-p-8da74 {
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

.box-textarea-2h76m {
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

.box-div-27zw5 {
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

.box-p-ftj9j {
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

.box-textarea-ruzib {
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

.box-div-didjm {
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

.box-p-y6zo1 {
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

.box-textarea-kurh2 {
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
