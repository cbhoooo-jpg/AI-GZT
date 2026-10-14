<!--
  页面《4》　路由:/4（4）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-u3i2k">
    <div class="box-div-5uowr">
      <div class="box-div-xngty">
        <span class="box-span-cr64v"></span>
        <span class="box-span-31c2k">系统配置</span>
        <button class="box-button-v14cc" type="button" @click="goPage4()" :class="{ 'lc-nav-active': route.path === '/4' }">安全-存储</button>
        <button class="box-button-zdo16" type="button" @click="goPage14()" :class="{ 'lc-nav-active': route.path === '/1-4' }">记忆召回</button>
        <button class="box-button-o3fep" type="button" @click="goPage24()" :class="{ 'lc-nav-active': route.path === '/2-4' }">界面主题</button>
        <button class="box-button-jjl4j" type="button" @click="goPage34()" :class="{ 'lc-nav-active': route.path === '/3-4' }">工具输出与任务防中断</button>
      </div>
      <div class="box-div-xvg97">
        <div class="box-div-7rz71">
          <div class="box-div-8xq9v">
            <div class="box-div-xvt8b">
              <h2 class="box-h2-nufux">安全设置 - 禁止操作列表</h2>
              <button class="box-button-pomif" type="submit" @click="saveConfig">保存配置</button>
            </div>
            <div class="box-div-iz9ts" v-for="(p, i) in config.forbidden_paths" :key="i">
              <p class="box-p-g5d5v">自定义禁止操作列表</p>
              <input class="box-input-3unz9" type="text" :value="p" readonly />
              <button class="box-button-4x3ed" type="button" @click="removeForbidden(p)">🗑</button>
            </div>
            <div class="box-div-dg32k">
              <input class="box-input-3unz9" type="text" placeholder="点击右侧按钮选择要禁止的目录" v-model="newForbiddenPath" readonly />
              <button class="box-button-xqev3" type="submit" @click="addForbidden">添加文件目录</button>
            </div>
            <div class="box-div-f457r">
              <h2 class="box-h2-0f6g4">存储设置</h2>
            </div>
            <div class="box-div-ga14v">
              <p class="box-p-m0ryp">仓库存储路径</p>
              <input class="box-input-m8f15" type="text" placeholder="请选择仓库存储位置" v-model="repositoryPath" readonly />
              <button class="box-button-prq30" type="submit" @click="selectRepositoryPath">选择文件夹</button>
            </div>
            <div class="box-div-eig6d">
              <p class="box-p-2y4wj">下载保存路径</p>
              <input class="box-input-b25k1" type="text" placeholder="请选择下载文件保存位置" v-model="config.download_path" readonly />
              <button class="box-button-j45pi" type="submit" @click="selectDownloadPath">选择文件夹</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

// ---- 安全-存储配置接线（复用统一请求封装 /api/request） ----
import { ref, onMounted } from 'vue'
import { get, post } from '@/api/request'

/** 系统配置（下载路径等）+ 禁止路径列表 */
const config = ref<Record<string, any>>({ download_path: '', forbidden_paths: [] })
/** 仓库存储路径（走独立接口 /api/config/repository/set） */
const repositoryPath = ref('')
/** 待新增的禁止路径输入值 */
const newForbiddenPath = ref('')

/** 加载系统配置与仓库路径 */
async function loadConfig() {
  try {
    const data = await get<Record<string, any>>('/api/config/get')
    if (data) {
      config.value = { ...config.value, ...data }
      if (!Array.isArray(config.value.forbidden_paths)) config.value.forbidden_paths = []
      repositoryPath.value = data.repository_path || ''
    }
  } catch (e) {
    console.error('加载系统配置失败:', e)
  }
}

/** 保存配置:下载路径走 /api/config/set；仓库路径变化时走独立接口 */
async function saveConfig() {
  try {
    await post('/api/config/set', { config: { download_path: config.value.download_path } })
    const cur = await get<Record<string, any>>('/api/config/get')
    const oldRepo = (cur && cur.repository_path) || ''
    if (repositoryPath.value && repositoryPath.value !== oldRepo) {
      await post('/api/config/repository/set', { new_path: repositoryPath.value, migrate_files: false })
    }
    console.log('安全-存储配置保存成功')
  } catch (e) {
    console.error('保存安全-存储配置失败:', e)
  }
}

/** 弹出系统原生文件夹选择框，返回选中路径（用户取消时返回空串） */
async function selectFolderByDialog(): Promise<string> {
  const path = await post<string>('/api/utils/select_path', { select_dir: true })
  return path || ''
}

/** 添加文件目录:点击按钮直接弹出系统文件夹选择框，选中后立即加入禁止列表（复用旧版 /api/utils/select_path） */
async function addForbidden() {
  try {
    const p = await selectFolderByDialog()
    if (!p) return
    newForbiddenPath.value = p
    const data = await post<Record<string, any>>('/api/config/forbidden/add', { path: p })
    if (data && Array.isArray(data.forbidden_paths)) config.value.forbidden_paths = data.forbidden_paths
  } catch (e) {
    console.error('添加禁止路径失败:', e)
  }
}

/** 选择仓库存储路径:点击按钮直接弹出系统文件夹选择框，选中后立即落盘（与「保存配置」同一接口） */
async function selectRepositoryPath() {
  try {
    const p = await selectFolderByDialog()
    if (!p) return
    repositoryPath.value = p
    await post('/api/config/repository/set', { new_path: p, migrate_files: false })
    console.log('仓库存储路径已保存:', p)
  } catch (e) {
    console.error('选择仓库路径失败:', e)
  }
}

/** 选择下载保存路径:点击按钮直接弹出系统文件夹选择框，选中后立即落盘（与「保存配置」同一接口） */
async function selectDownloadPath() {
  try {
    const p = await selectFolderByDialog()
    if (!p) return
    config.value.download_path = p
    await post('/api/config/set', { config: { download_path: p } })
    console.log('下载保存路径已保存:', p)
  } catch (e) {
    console.error('选择下载路径失败:', e)
  }
}

/** 删除禁止路径 */
async function removeForbidden(p: string) {
  try {
    const data = await post<Record<string, any>>('/api/config/forbidden/delete', { path: p })
    if (data && Array.isArray(data.forbidden_paths)) config.value.forbidden_paths = data.forbidden_paths
  } catch (e) {
    console.error('删除禁止路径失败:', e)
  }
}

onMounted(loadConfig)

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPage4() {
  router.push('/4')
}

function goPage14() {
  router.push('/1-4')
}

function goPage24() {
  router.push('/2-4')
}

function goPage34() {
  router.push('/3-4')
}
</script>

<style scoped>
.box-div-u3i2k {
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

.box-div-5uowr {
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

.box-div-xngty {
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

.box-span-cr64v {
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

.box-span-31c2k {
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

.box-button-v14cc {
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

.box-button-zdo16 {
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

.box-button-o3fep {
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

.box-button-jjl4j {
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

.box-div-xvg97 {
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

.box-div-7rz71 {
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

.box-div-8xq9v {
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

.box-div-xvt8b {
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

.box-h2-nufux {
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

.box-button-pomif {
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

.box-div-iz9ts {
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

.box-p-g5d5v {
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

.box-input-3unz9 {
  width: 350px;
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

.box-button-4x3ed {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 28px;
  height: 28px;
  min-width: 28px;
  max-width: 28px;
  font-size: 24px;
  color: #1f2329;
  background-color: transparent;
  border-style: none;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-dg32k {
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

.box-p-5uizv {
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

.box-button-xqev3 {
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

.box-div-f457r {
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

.box-h2-0f6g4 {
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

.box-div-ga14v {
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

.box-p-m0ryp {
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

.box-input-m8f15 {
  width: 350px;
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

.box-button-prq30 {
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

.box-div-eig6d {
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

.box-p-2y4wj {
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

.box-input-b25k1 {
  width: 350px;
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

.box-button-j45pi {
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
</style>
