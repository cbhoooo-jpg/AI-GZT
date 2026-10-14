<!--
  页面《1》　路由:/1-6（16）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout9>
  <div class="box-div-4ct2h">
    <div class="box-div-lwu0t">
      <div class="box-div-9k9e4">
        <div class="box-div-w2nq0">
          <div class="box-div-npqt9">
            <span class="box-span-9tsyh">总记忆数:{{ totalCount }} 条</span>
          </div>
          <button class="box-button-y29om" type="button" @click="loadLibraries">刷新列表</button>
        </div>
        <div class="box-div-wnz9r">
          <div v-for="lib in libraries" :key="lib.library_id" class="mem-lib-item">
            <div class="mem-lib-info">
              <span class="mem-lib-name">{{ lib.library_name }}</span>
              <span class="mem-lib-count">记忆条数:{{ lib.memory_count }} 条</span>
            </div>
            <button class="mem-lib-clear" type="button" :disabled="lib.memory_count === 0" @click="clearLibrary(lib.library_id, lib.library_name)">清空</button>
          </div>
          <div v-if="libraries.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无记忆库</div>
        </div>
      </div>
    </div>
  </div>
  </Layout9>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout9 from '@/layouts/Layout9.vue'
import { get, post } from '@/api/request'

/** 记忆库结构（与后端 /api/memory/library/list 返回项对齐） */
interface MemoryLibrary {
  library_id: string
  library_name: string
  memory_count: number
  is_main: boolean
}

const libraries = ref<MemoryLibrary[]>([])

/** 所有记忆库总条数 */
const totalCount = computed(() =>
  libraries.value.reduce((sum, lib) => sum + (lib.memory_count || 0), 0),
)

/** 加载记忆库列表 */
async function loadLibraries() {
  try {
    const data = await get<MemoryLibrary[]>('/api/memory/library/list')
    libraries.value = data || []
  } catch (e) {
    console.error('加载记忆库列表失败', e)
  }
}

/** 清空指定记忆库（含确认，后端会同步清理向量索引与对话历史缓存） */
async function clearLibrary(libraryId: string, libraryName: string) {
  if (!window.confirm(`确定要清空【${libraryName}】吗?该库的全部记忆与向量索引将被删除,不可恢复!`)) return
  try {
    await post('/api/memory/library/clear', { library_id: libraryId })
    window.alert('记忆库清空成功')
    await loadLibraries()
  } catch (e) {
    console.error('清空记忆库失败', e)
    window.alert('清空失败,请重试')
  }
}

onMounted(loadLibraries)
</script>

<style scoped>
.box-div-4ct2h {
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

.box-div-lwu0t {
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

.box-div-9k9e4 {
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

.box-div-w2nq0 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-npqt9 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 226px;
  min-height: 40px;
  justify-content: flex-start;
  align-items: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-9tsyh {
  font-size: 14px;
  color: #86909c;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-y29om {
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

.box-div-wnz9r {
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

/* ===== 记忆库列表样式（对齐旧页 sample.html 记忆库管理 Tab） ===== */
.mem-lib-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  margin-bottom: 8px;
}
.mem-lib-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.mem-lib-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mem-lib-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
}
.mem-lib-count {
  font-size: 12px;
  color: #86909c;
}
.mem-lib-clear {
  height: 30px;
  font-size: 13px;
  color: #ffffff;
  background-color: #f56c6c;
  border-style: none;
  padding: 0 14px;
  border-radius: 6px;
  cursor: pointer;
}
.mem-lib-clear:disabled {
  background-color: #c9cdd4;
  cursor: not-allowed;
}
</style>
