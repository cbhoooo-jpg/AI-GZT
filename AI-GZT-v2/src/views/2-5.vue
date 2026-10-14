<!--
  页面《2》　路由:/2-5（25）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout8>
  <div class="box-div-xtkpb">
    <div class="box-div-71zsc">
      <div class="box-div-0bs07">
        <div class="tp-head">
          <h3 class="tp-title">选择预制模板</h3>
          <p class="tp-tip">选择适合的模板，自动填充通用逻辑，无需从零开始编写代码</p>
        </div>
        <div v-if="loading" style="text-align: center; color: #999; padding: 40px 0;">加载模板列表中...</div>
        <div v-else class="tp-grid">
          <div
            v-for="tpl in templates"
            :key="tpl.template_id"
            class="tp-card"
            :class="{ 'is-selected': selectedId === tpl.template_id }"
            @click="selectTemplate(tpl.template_id)"
          >
            <div class="tp-card-head">
              <div class="tp-card-title">
                <span class="pl-icon">🧩</span>
                <div>
                  <h4 class="pl-name">{{ tpl.name }}</h4>
                  <p class="pl-sub">{{ tpl.scene }}</p>
                </div>
              </div>
              <span v-if="selectedId === tpl.template_id" class="tp-check">✓</span>
            </div>
            <div class="tp-block">
              <div class="tp-block-label">默认配置</div>
              <div class="tp-tags">
                <span v-for="c in (tpl.default_config || [])" :key="c.label" class="tp-tag">{{ c.label }}</span>
              </div>
            </div>
            <div class="tp-block">
              <div class="tp-block-label">默认入参</div>
              <div class="tp-tags">
                <span v-for="p in (tpl.default_params || [])" :key="p.name" class="tp-tag">{{ p.name }}</span>
              </div>
            </div>
            <button class="pl-btn pl-btn-primary tp-use-btn" type="button" @click.stop="useTemplate(tpl.template_id)">一键生成插件</button>
          </div>
          <div v-if="templates.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无可用模板</div>
        </div>
      </div>
    </div>

    <!-- 一键生成弹窗 -->
    <div v-if="modalVisible" class="pl-modal-mask" @click.self="closeModal">
      <div class="pl-modal">
        <div class="pl-modal-header">
          <span class="pl-modal-title">一键生成插件</span>
          <span class="pl-modal-close" @click="closeModal">×</span>
        </div>
        <div class="pl-modal-body">
          <div class="pl-form-item">
            <label class="pl-form-label">插件名称<span class="pl-required">*</span></label>
            <input class="pl-form-input" type="text" v-model="form.name" placeholder="例如:AI音乐生成插件" />
          </div>
          <div class="pl-form-item">
            <label class="pl-form-label">触发关键词<span class="pl-required">*</span></label>
            <input class="pl-form-input" type="text" v-model="form.trigger" placeholder="例如:生成音乐" />
            <p class="pl-form-tip">用户输入该关键词即可触发插件</p>
          </div>
          <div class="pl-form-item">
            <label class="pl-form-label">功能描述（可选）</label>
            <textarea class="pl-form-input pl-form-textarea" v-model="form.desc" placeholder="简要描述插件功能，留空自动生成"></textarea>
          </div>
          <div class="pl-form-item">
            <label class="pl-form-label">保存路径<span class="pl-required">*</span></label>
            <input class="pl-form-input" type="text" v-model="form.saveDir" placeholder="插件保存的目录路径" />
            <p class="pl-form-tip">目录不存在会自动创建，默认保存在仓库文件夹的插件开发目录下</p>
          </div>
        </div>
        <div class="pl-modal-footer">
          <button class="pl-btn pl-btn-plain" type="button" @click="closeModal">取消</button>
          <button class="pl-btn pl-btn-primary" type="button" @click="doGenerate">一键生成</button>
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

/** 模板结构（与后端 /api/plugin/templates 返回项对齐） */
interface Template {
  template_id: string
  name: string
  scene: string
  default_config?: Array<{ label: string }>
  default_params?: Array<{ name: string }>
}

const templates = ref<Template[]>([])
const selectedId = ref('')
const loading = ref(false)
const modalVisible = ref(false)
const activeTemplateId = ref('')

const form = ref({
  name: '',
  trigger: '',
  desc: '',
  saveDir: 'D:/AI仓库文件夹/AI智能助手/plugins/',
})

/** 加载模板列表 */
async function loadTemplates() {
  loading.value = true
  try {
    const data = await get<Template[]>('/api/plugin/templates')
    templates.value = data || []
  } catch (e) {
    console.error('加载模板列表失败', e)
  } finally {
    loading.value = false
  }
}

/** 选择模板（高亮） */
function selectTemplate(id: string) {
  selectedId.value = id
}

/** 打开一键生成弹窗 */
function useTemplate(id: string) {
  activeTemplateId.value = id
  selectedId.value = id
  form.value = {
    name: '',
    trigger: '',
    desc: '',
    saveDir: 'D:/AI仓库文件夹/AI智能助手/plugins/',
  }
  modalVisible.value = true
}

function closeModal() {
  modalVisible.value = false
  activeTemplateId.value = ''
}

/** 由插件名生成插件ID（与旧页一致:去中文、空格转下划线） */
function buildPluginId(name: string): string {
  return name
    .toLowerCase()
    .replace(/[\u4e00-\u9fa5]/g, '')
    .replace(/\s+/g, '_')
    .replace(/[^a-z0-9_]/g, '')
}

/** 执行一键生成 */
async function doGenerate() {
  const name = form.value.name.trim()
  const trigger = form.value.trigger.trim()
  if (!name || !trigger) {
    window.alert('请填写插件名称和触发关键词')
    return
  }
  const pluginId = buildPluginId(name)
  if (!pluginId) {
    window.alert('插件名称需要包含英文或数字')
    return
  }
  const desc = form.value.desc.trim() || `${name}，使用触发关键词即可调用生成功能`
  try {
    await post('/api/plugin/generate', {
      plugin_info: {
        plugin_id: pluginId,
        name,
        description: desc,
        version: '1.0.0',
        author: '插件生成器',
        trigger_keyword: trigger,
      },
      save_dir: form.value.saveDir.trim(),
      preset_template_id: activeTemplateId.value,
    })
    window.alert('插件生成成功！已自动添加到已安装插件列表')
    closeModal()
  } catch (e) {
    console.error('生成插件失败', e)
    window.alert('生成失败，请检查服务是否正常')
  }
}

onMounted(loadTemplates)
</script>

<style scoped>
.box-div-xtkpb {
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

.box-div-71zsc {
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

.box-div-0bs07 {
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

/* ===== 插件模版样式（对齐旧页 web_plugin_market.html 开发新插件 Tab） ===== */
.tp-head {
  margin-bottom: 16px;
}
.tp-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2329;
  margin: 0 0 6px;
}
.tp-tip {
  font-size: 13px;
  color: #86909c;
  margin: 0;
}
.tp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.tp-card {
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.06);
  transition: all 0.2s;
}
.tp-card:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
}
.tp-card.is-selected {
  border-color: var(--primary);
}
.tp-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.tp-card-title {
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
.tp-check {
  color: #00b42a;
  font-size: 18px;
  font-weight: bold;
}
.tp-block {
  margin-bottom: 12px;
}
.tp-block-label {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 6px;
}
.tp-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tp-tag {
  padding: 2px 8px;
  background: #f2f3f5;
  color: #4e5969;
  border-radius: 4px;
  font-size: 12px;
}
.tp-use-btn {
  width: 100%;
  height: 32px;
  margin-top: 4px;
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
  width: 520px;
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
</style>
