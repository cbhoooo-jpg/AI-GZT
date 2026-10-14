<!--
  页面《2》　路由:/2-6（26）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout9>
  <div class="box-div-rz7cb">
    <div class="box-div-gih76">
      <div class="box-div-vrsnu">
        <div class="box-div-2g3jo">
          <button class="box-button-y6pko" type="button" @click="loadFiles">刷新列表</button>
        </div>
        <div class="box-div-ebc48">
          <div v-for="file in fileList" :key="file.file_name" class="mem-file-item">
            <div class="mem-file-info">
              <span class="mem-file-name">{{ file.file_desc }}</span>
              <span class="mem-file-meta">{{ file.file_name }} · {{ file.file_size }} · {{ file.modify_time }}</span>
            </div>
            <button
              class="mem-file-clear"
              type="button"
              :disabled="file.is_system"
              @click="clearFile(file.file_name, file.file_desc)"
            >{{ file.is_system ? '系统文件' : '清空' }}</button>
          </div>
          <div v-if="fileList.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无记忆文件</div>
        </div>
      </div>
    </div>
  </div>
  </Layout9>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout9 from '@/layouts/Layout9.vue'
import { get, post } from '@/api/request'

/** 记忆文件结构（与后端 /api/memory/file/list 返回项对齐） */
interface MemoryFile {
  file_name: string
  file_desc: string
  file_size: string
  modify_time: string
  is_system: boolean
  file_type: string
}

const fileList = ref<MemoryFile[]>([])

/** 加载记忆文件列表 */
async function loadFiles() {
  try {
    const data = await get<MemoryFile[]>('/api/memory/file/list')
    fileList.value = data || []
  } catch (e) {
    console.error('加载记忆文件列表失败', e)
  }
}

/** 清空指定记忆文件（仅对话历史缓存可清，系统文件按钮已禁用） */
async function clearFile(fileName: string, fileDesc: string) {
  if (!window.confirm(`确定要清空【${fileDesc}】吗?该操作仅清空对话历史缓存,不会影响记忆库数据`)) return
  try {
    await post('/api/memory/file/clear', { file_name: fileName })
    window.alert('文件清空成功')
    await loadFiles()
  } catch (e) {
    console.error('清空记忆文件失败', e)
    window.alert('清空失败,请重试')
  }
}

onMounted(loadFiles)
</script>

<style scoped>
.box-div-rz7cb {
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

.box-div-gih76 {
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

.box-div-vrsnu {
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

.box-div-2g3jo {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-button-y6pko {
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

.box-div-ebc48 {
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

/* ===== 记忆文件列表样式（对齐旧页 sample.html 记忆文件管理 Tab） ===== */
.mem-file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  margin-bottom: 8px;
}
.mem-file-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.mem-file-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mem-file-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
}
.mem-file-meta {
  font-size: 12px;
  color: #86909c;
}
.mem-file-clear {
  height: 30px;
  font-size: 13px;
  color: #ffffff;
  background-color: #f56c6c;
  border-style: none;
  padding: 0 14px;
  border-radius: 6px;
  cursor: pointer;
}
.mem-file-clear:disabled {
  background-color: #c9cdd4;
  cursor: not-allowed;
}
</style>
