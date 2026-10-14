<!--
  页面《1》　路由:/1-4（14）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout4>
  <div class="box-div-kv2jk">
    <div class="box-div-0e80i">
      <div class="box-div-x7aas">
        <div class="box-div-ik208">
          <h2 class="box-h2-826c9">记忆召回参数配置</h2>
          <button class="box-button-0p8ps" type="submit" @click="saveConfig">保存配置</button>
        </div>
        <div class="box-div-p6xx4">
          <p class="box-p-eowk9">记忆检索数</p>
          <input class="box-input-qqe6n" type="text" placeholder="请输入内容" v-model.number="config.recall_top_k" />
          <p class="box-p-6lh7v">相似度阈值</p>
          <input class="box-input-qxcsh" type="text" placeholder="请输入内容" v-model.number="config.similarity_threshold" />
        </div>
        <div class="box-div-8wim2">
          <p class="box-p-6xewv">检索触发阈值</p>
          <input class="box-input-01xzy" type="text" placeholder="请输入内容" v-model.number="config.recall_trigger_rounds" />
          <p class="box-p-wd191">超龄记忆上限(天)</p>
          <input class="box-input-3275e" type="text" placeholder="请输入内容" v-model.number="config.max_age_days" />
        </div>
        <div class="box-div-9l01r">
          <p class="box-p-y6es5">相对阈值余量</p>
          <input class="box-input-svweg" type="text" placeholder="请输入内容" v-model.number="config.relative_margin" />
          <p class="box-p-f9309">时间衰减档位(天)</p>
          <input class="box-input-7t6yv" type="text" placeholder="请输入内容" :value="numListToStr(config.time_decay_days)" @input="config.time_decay_days = strToNumList(($event.target as HTMLInputElement).value)" />
        </div>
        <div class="box-div-qlrr1">
          <p class="box-p-0hfq6">时间衰减惩罚</p>
          <input class="box-input-iz53z" type="text" placeholder="请输入内容" :value="numListToStr(config.time_decay_penalty)" @input="config.time_decay_penalty = strToNumList(($event.target as HTMLInputElement).value)" />
          <p class="box-p-142ph">多样性权重</p>
          <input class="box-input-u3ezi" type="text" placeholder="请输入内容" v-model.number="config.mmr_lambda" />
        </div>
        <div class="box-div-3mfbf">
          <h2 class="box-h2-8b3bv">向量环境检索检测</h2>
        </div>
        <div class="box-div-qkijc">
          <!-- 向量检索环境检测（对齐旧前端 web_settings.html L273-315；数据源 GET /api/memory/env_check） -->
          <div style="display: flex; align-items: center;">
            <span :style="{ padding: '4px 12px', borderRadius: '4px', fontSize: '13px', color: '#ffffff', backgroundColor: vectorEnv.current_mode === 'full' ? '#67C23A' : '#E6A23C' }">
              {{ vectorEnv.current_mode === 'full' ? '✅ 完整模式' : '⚠️ 降级模式' }}
            </span>
            <span style="margin-left: 12px; color: #606266; font-size: 14px;">Python版本: {{ vectorEnv.python_version }}</span>
          </div>
          <div style="display: flex; gap: 12px;">
            <span :style="{ padding: '2px 10px', borderRadius: '4px', fontSize: '12px', color: '#ffffff', backgroundColor: vectorEnv.torch_installed ? '#67C23A' : '#F56C6C' }">
              torch {{ vectorEnv.torch_installed ? '已安装' : '未安装' }}
            </span>
            <span :style="{ padding: '2px 10px', borderRadius: '4px', fontSize: '12px', color: '#ffffff', backgroundColor: vectorEnv.sentence_transformers_installed ? '#67C23A' : '#F56C6C' }">
              sentence_transformers {{ vectorEnv.sentence_transformers_installed ? '已安装' : '未安装' }}
            </span>
            <span :style="{ padding: '2px 10px', borderRadius: '4px', fontSize: '12px', color: '#ffffff', backgroundColor: vectorEnv.transformers_installed ? '#67C23A' : '#F56C6C' }">
              transformers {{ vectorEnv.transformers_installed ? '已安装' : '未安装' }}
            </span>
          </div>
          <div v-if="vectorEnv.current_mode === 'full'" style="color: #67C23A; font-size: 14px;">
            ✅ 向量检索功能已启用，记忆检索开启，RAG功能开启
          </div>
          <div v-else-if="!vectorEnv.torch_installed || !vectorEnv.sentence_transformers_installed || !vectorEnv.transformers_installed" style="color: #e6a23c; font-size: 14px;">
            ⚠️ 向量检索功能已禁用，当前仅保留元数据记忆。请安装以下依赖以启用完整模式:
            <div style="margin-top: 8px; padding: 8px; background-color: #fdf6ec; border-radius: 4px;">
              <div>1. 安装Python 3.11 (需与程序内置版本一致)</div>
              <div>2. 找到安装文件中的(Python和依赖安装.bat)文件双击运行会自动安装Python 3.11和相关依赖</div>
              <div>3. 安装完成后重启程序</div>
            </div>
          </div>
          <div v-else-if="!vectorEnv.model_installed" style="color: #e6a23c; font-size: 14px;">
            ⚠️ 向量检索功能已禁用，当前仅保留元数据记忆。依赖已安装，但未检测到本地中文语义向量模型文件。
            <div style="margin-top: 8px; padding: 8px; background-color: #fdf6ec; border-radius: 4px;">
              <div>1. 下载中文语义向量模型 gte-small-zh（含 pytorch_model.bin 等文件）</div>
              <div>2. 将模型文件放入程序目录下的 gte-small-zh 文件夹中</div>
              <div>3. 点击"重新检测"后关闭工作台重新启动后即可启用完整模式</div>
            </div>
          </div>
          <div v-else style="color: #e6a23c; font-size: 14px;">
            ⚠️ 向量检索功能已禁用，当前仅保留元数据记忆。依赖与模型文件均已就绪，但模型加载失败，请查看日志后重启程序。
          </div>
          <button class="box-button-0p8ps" type="button" @click="checkVectorEnv" :disabled="vectorEnvLoading" style="align-self: flex-start; margin-top: 4px;">{{ vectorEnvLoading ? '检测中…' : '重新检测' }}</button>
        </div>
      </div>
    </div>
  </div>
  </Layout4>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, post } from '@/api/request'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout4 from '@/layouts/Layout4.vue'

// 记忆召回配置（与后端 memory_config.json 字段一一对应）
const config = ref<Record<string, any>>({
  recall_top_k: 4,
  similarity_threshold: 0.85,
  recall_trigger_rounds: 2,
  max_age_days: 0,
  relative_margin: 0.05,
  time_decay_days: [180, 30, 7],
  time_decay_penalty: [0.2, 0.1, 0.05],
  mmr_lambda: 0.7,
})

// 向量检索环境状态（对齐旧前端 web_settings.html 的 vectorEnv，字段与 /api/memory/env_check 返回一一对应）
const vectorEnv = ref<Record<string, any>>({
  python_version: '',
  python_matched: true,
  torch_installed: false,
  sentence_transformers_installed: false,
  transformers_installed: false,
  model_installed: false,
  current_mode: 'degraded',
})
const vectorEnvLoading = ref(false)

// 数组型参数编辑辅助:数字数组 <-> 逗号分隔字符串（前端可编辑，后端存数组）
function numListToStr(arr: any): string {
  return Array.isArray(arr) ? arr.join(',') : String(arr ?? '')
}
function strToNumList(str: any): number[] {
  return String(str == null ? '' : str)
    .split(',')
    .map((x) => Number(x.trim()))
    .filter((x) => !isNaN(x))
}

// 加载记忆配置（复用统一请求封装，接口口径与 web_settings.html 一致）
async function loadConfig() {
  try {
    const data = await get<Record<string, any>>('/api/memory/config')
    if (data) {
      config.value = { ...config.value, ...data }
    }
  } catch (e) {
    console.error('加载记忆配置失败:', e)
  }
}

// 保存记忆配置（后端 update_config 即时生效）
async function saveConfig() {
  try {
    await post('/api/memory/config/update', { config: config.value })
    console.log('记忆配置保存成功')
  } catch (e) {
    console.error('保存记忆配置失败:', e)
  }
}

// 检测向量检索环境（对齐旧前端 web_settings.html 的 checkVectorEnv；该接口返回含 data 字段，统一封装 get() 正常解包）
async function checkVectorEnv() {
  vectorEnvLoading.value = true
  try {
    const data = await get<Record<string, any>>('/api/memory/env_check')
    if (data) {
      vectorEnv.value = { ...vectorEnv.value, ...data }
    }
  } catch (e) {
    console.error('检测向量检索环境失败:', e)
  } finally {
    vectorEnvLoading.value = false
  }
}

onMounted(() => {
  loadConfig()
  checkVectorEnv()
})
</script>

<style scoped>
.box-div-kv2jk {
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

.box-div-0e80i {
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

.box-div-x7aas {
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

.box-div-ik208 {
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

.box-h2-826c9 {
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

.box-button-0p8ps {
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

.box-div-p6xx4 {
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

.box-p-eowk9 {
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

.box-input-qqe6n {
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

.box-p-6lh7v {
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

.box-input-qxcsh {
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

.box-div-8wim2 {
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

.box-p-6xewv {
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

.box-input-01xzy {
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

.box-p-wd191 {
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

.box-input-3275e {
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

.box-div-9l01r {
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

.box-p-y6es5 {
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

.box-input-svweg {
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

.box-p-f9309 {
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

.box-input-7t6yv {
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

.box-div-qlrr1 {
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

.box-p-0hfq6 {
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

.box-input-iz53z {
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

.box-p-142ph {
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

.box-input-u3ezi {
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

.box-div-3mfbf {
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

.box-h2-8b3bv {
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

.box-div-qkijc {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
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
  min-height: 143px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}
</style>
